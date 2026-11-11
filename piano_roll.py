"""
铺面编辑组件

以钢琴卷帘（piano roll）形式展示与编辑一首曲目的结构化音符列表：
- 纵轴覆盖钢琴全部88键（MIDI 21 A0 ~ 108 C8），左侧带一条纯视觉的钢琴键盘参照
- 横轴为绝对时间（秒），背景叠加逐秒参考线与（可选的）小节线
- 支持新增 / 删除 / 拖动（音高+起始时间）/ 拖动右边缘调整时长，可选量化吸附
- 支持 Ctrl+A / 矩形框选 / Ctrl·Shift+单击 的多选，多选后可整体拖动、整体删除
- 支持 Ctrl+C / Ctrl+X / Ctrl+V 在播放辅助线处复制、剪切与粘贴选中音符
- 支持 Shift+↑ / Shift+↓ 把选中音符整体上移 / 下移一个八度（越界音符保持原音高）
- 支持展示随实际播放进度移动的播放线，并可在播放期间禁用编辑
- 支持展示/拖动一个黄色半透明的「乐器音域框」，用于框定乐器实际可用的键位区间
"""

import math
from typing import Dict, List, Optional, Set, Tuple

from PyQt5.QtCore import QPoint, QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QAction,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QMenu,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from build_music import get_chromatic_key_ladder, tempo_us_from_bpm

MIN_PITCH = 21  # A0
MAX_PITCH = 108  # C8
PITCH_COUNT = MAX_PITCH - MIN_PITCH + 1  # 88

ROW_HEIGHT = 10
PIXELS_PER_SECOND = 70
DEFAULT_NOTE_DURATION = 0.4
MIN_NOTE_DURATION = 0.05
RESIZE_MARGIN = 6.0
MIN_SCENE_SECONDS = 10.0
TRAILING_PADDING_SECONDS = 5.0
CLICK_DRAG_THRESHOLD = 4.0
KEYBOARD_WIDTH = 30
MIN_MEASURE_SECONDS = 0.05  # 拍号/BPM 异常导致小节过短时的安全下限，避免画出海量小节线

# 横向缩放
MIN_PIXELS_PER_SECOND = 10.0
MAX_PIXELS_PER_SECOND = 600.0
ZOOM_STEP_FACTOR = 1.25

# 播放起点过滤的浮点比较容差
PLAYHEAD_EPSILON = 1e-6

# 顶部拍数标尺高度（像素）
RULER_HEIGHT = 28

RANGE_FILL_COLOR = QColor(255, 196, 0, 110)
RANGE_BORDER_COLOR = QColor(255, 214, 10, 235)
SELECT_RECT_FILL_COLOR = QColor(244, 208, 63, 40)
SELECT_RECT_BORDER_COLOR = QColor(244, 208, 63, 220)
SECOND_LINE_COLOR = QColor("#25313D")
MEASURE_LINE_COLOR = QColor("#55708A")

# 一个八度内的黑键相对半音位置（以C为0）
_BLACK_KEY_OFFSETS = {1, 3, 6, 8, 10}


def _is_black_key(pitch: int) -> bool:
    return (pitch % 12) in _BLACK_KEY_OFFSETS


def pasted_starts(clipboard: List[Dict], anchor: float) -> List[float]:
    """剪贴板音符按最早 start 对齐 anchor（秒）后的起始时间列表；不修改输入。"""
    if not clipboard:
        return []
    base = min(float(n.get("start", 0.0)) for n in clipboard)
    return [max(0.0, float(anchor) + float(n.get("start", 0.0)) - base) for n in clipboard]


def octave_shift_pitches(
    notes: List[Dict], selected_ids: Set[int], delta: int
) -> Dict[int, int]:
    """按 delta 半音整体移动选中音符；新音高超出 A0～C8 的音符保持原音高。"""
    targets: Dict[int, int] = {}
    for note in notes:
        note_id = note.get("id")
        if note_id not in selected_ids:
            continue
        pitch = int(note["pitch"])
        target = pitch + delta
        targets[note_id] = target if MIN_PITCH <= target <= MAX_PITCH else pitch
    return targets


def playback_notes_from_position(notes: List[Dict], playhead: float) -> List[Dict]:
    """只保留起始时间不早于 playhead 的音符，并把 start 平移到相对时间。"""
    result: List[Dict] = []
    for note in notes:
        start = float(note.get("start", 0.0))
        if start >= playhead - PLAYHEAD_EPSILON:
            cloned = dict(note)
            cloned["start"] = max(0.0, start - playhead)
            result.append(cloned)
    return result


def first_playable_start(
    notes: List[Dict], pitch_range: Optional[Tuple[int, int]] = None
) -> float:
    """返回参与播放的第一个音符的相对起始时间；无音符时返回 0。"""
    low = pitch_range[0] - 1 if pitch_range else None
    high = pitch_range[1] + 1 if pitch_range else None
    starts = [
        float(n.get("start", 0.0))
        for n in notes
        if low is None or low <= int(n["pitch"]) <= high
    ]
    return min(starts, default=0.0)


def clamp_pixels_per_second(value: float) -> float:
    return max(MIN_PIXELS_PER_SECOND, min(MAX_PIXELS_PER_SECOND, float(value)))


def anchored_scroll_value(anchor_time: float, screen_x: float, pixels_per_second: float) -> float:
    """缩放后应设置的横向滚动值（像素），使 anchor_time 仍落在屏幕 screen_x 处。"""
    return max(0.0, float(anchor_time) * float(pixels_per_second) - float(screen_x))


def bpm_scale_factor(old_bpm: float, new_bpm: float) -> float:
    """旧/新 BPM 的时间缩放因子；任一 BPM 非正时抛 ValueError。"""
    if old_bpm <= 0 or new_bpm <= 0:
        raise ValueError("BPM 必须大于 0")
    return float(old_bpm) / float(new_bpm)


def grid_seconds_for_bpm(bpm: float, numerator: int, denominator: int) -> Tuple[float, float]:
    """返回 (每小节秒数, 每拍秒数)；拍长 = 60/BPM * 4/分母。"""
    if bpm <= 0:
        raise ValueError("BPM 必须大于 0")
    beat_seconds = (60.0 / float(bpm)) * (4.0 / float(denominator))
    return beat_seconds * int(numerator), beat_seconds


def scaled_note_times(notes: List[Dict], factor: float) -> List[Dict]:
    """返回音符浅拷贝（音符为扁平字典），start 与 duration 乘以 factor；不修改输入。"""
    result: List[Dict] = []
    for note in notes:
        cloned = dict(note)
        cloned["start"] = float(note.get("start", 0.0)) * factor
        cloned["duration"] = float(note.get("duration", 0.0)) * factor
        result.append(cloned)
    return result


class _PianoKeyboardWidget(QWidget):
    """铺面左侧的竖直钢琴键盘：纯视觉参照，固定贴在视图左边缘，随铺面纵向滚动
    一起滚动，不随铺面横向（时间轴）滚动移动；不接受任何鼠标事件。"""

    def __init__(self, canvas: "_PianoRollCanvas", mapped_pitches: Set[int], parent=None):
        super().__init__(parent)
        self._canvas = canvas
        self._mapped_pitches = mapped_pitches
        self.setFixedWidth(KEYBOARD_WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        canvas.verticalScrollBar().valueChanged.connect(self._on_canvas_scrolled)

    def _on_canvas_scrolled(self, _value=None) -> None:
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        width = self.width()
        height = self.height()
        painter.fillRect(0, 0, width, height, QColor("#F5F2EA"))

        top_scene_y = self._canvas.mapToScene(QPoint(0, 0)).y()
        first_index = max(0, int(top_scene_y // ROW_HEIGHT))

        i = first_index
        while True:
            pitch = MAX_PITCH - i
            if pitch < MIN_PITCH:
                break
            row_top_scene_y = i * ROW_HEIGHT
            y = row_top_scene_y - top_scene_y
            if y > height:
                break

            if _is_black_key(pitch):
                color = QColor("#1B1B1B")
                if pitch not in self._mapped_pitches:
                    color = color.lighter(150)
                bx = int(width * 0.42)
                bw = width - bx
                by = int(y) + 1
                bh = max(1, ROW_HEIGHT - 2)
                painter.fillRect(bx, by, bw, bh, color)

            i += 1

        painter.setPen(QPen(QColor("#0F1720"), 1))
        painter.drawLine(width - 1, 0, width - 1, height)
        painter.end()


class _TimeRulerWidget(QWidget):
    """钢琴窗顶部的固定拍数标尺：显示小节/拍刻度，点击或拖动定位播放辅助线。"""

    playheadRequested = pyqtSignal(float)

    def __init__(self, canvas: "_PianoRollCanvas", parent=None):
        super().__init__(parent)
        self._canvas = canvas
        self._seconds_per_beat: Optional[float] = None
        self._beats_per_measure = 4
        self.setFixedHeight(RULER_HEIGHT)
        self.setMouseTracking(True)
        canvas.zoomChanged.connect(self._on_canvas_changed)
        canvas.horizontalScrollBar().valueChanged.connect(self._on_canvas_changed)
        canvas.horizontalScrollBar().rangeChanged.connect(self._on_canvas_changed)

    def _on_canvas_changed(self, *_args) -> None:
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self.update()
        super().resizeEvent(event)

    def _viewport_origin(self) -> float:
        """画布视口左边缘在本标尺坐标系中的 x。

        标尺与画布在 `PianoRollWidget` 中左边缘对齐（同一 KEYBOARD_WIDTH 缩进），
        因此这里只需补上画布自身的边框宽度；调用 QWidget.mapTo 在绘制期间
        会导致 PyQt 崩溃，不能用它做实时换算。
        """
        return float(self._canvas.frameWidth())

    def _viewport_width(self) -> float:
        return float(self._canvas.viewport().width())

    def _tick_x(self, seconds: float) -> float:
        return self._viewport_origin() + self._canvas.viewport_x_for_time(seconds)

    def _time_at_x(self, x: float) -> float:
        local = max(0.0, min(float(x) - self._viewport_origin(), self._viewport_width()))
        return self._canvas.time_at_viewport_x(local)

    def set_beat_grid(
        self, seconds_per_beat: Optional[float], beats_per_measure: int
    ) -> None:
        """设置每拍秒数与每小节拍数；缺少节拍信息时标尺退化为按秒标注。"""
        self._seconds_per_beat = (
            seconds_per_beat if (seconds_per_beat and seconds_per_beat > 0) else None
        )
        self._beats_per_measure = max(1, int(beats_per_measure))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1B2631"))
        pps = self._canvas.pixels_per_second()
        if pps <= 0 or self.width() <= 0 or self._viewport_width() <= 0:
            painter.end()
            return

        start_time = self._canvas.time_at_viewport_x(0.0)
        end_time = self._canvas.time_at_viewport_x(self._viewport_width())
        seconds_per_measure = (
            self._seconds_per_beat * self._beats_per_measure
            if self._seconds_per_beat
            else None
        )

        if seconds_per_measure:
            measure = int(start_time // seconds_per_measure)
            # 安全上限：避免异常 BPM/拍号画出海量刻度
            count = 0
            while measure * seconds_per_measure <= end_time and count < 5000:
                self._draw_tick(
                    painter, measure * seconds_per_measure, str(measure + 1), tall=True
                )
                if self._seconds_per_beat:
                    base = measure * seconds_per_measure
                    for beat in range(1, self._beats_per_measure):
                        self._draw_tick(
                            painter, base + beat * self._seconds_per_beat, "", tall=False
                        )
                measure += 1
                count += 1
        else:
            second = int(start_time)
            while second <= end_time and second - int(start_time) < 5000:
                self._draw_tick(painter, float(second), f"{second}s", tall=True)
                second += 1

        painter.end()

    def _draw_tick(self, painter: QPainter, seconds: float, text: str, tall: bool) -> None:
        origin = self._viewport_origin()
        right = origin + self._viewport_width()
        x = self._tick_x(seconds)
        if x < origin - 40 or x > right + 40:
            return
        top = 0 if tall else RULER_HEIGHT - 8
        painter.setPen(QPen(QColor("#85929E" if tall else "#4D5656"), 1))
        painter.drawLine(int(x), top, int(x), RULER_HEIGHT - 1)
        if text:
            painter.setPen(QPen(QColor("#D5D8DC"), 1))
            painter.drawText(int(x) + 3, 12, text)

    def _should_ignore_mouse(self) -> bool:
        # 播放中（只读）禁用标尺定位，避免与播放进度争夺辅助线
        return self._canvas.is_read_only()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or self._should_ignore_mouse():
            return
        self.playheadRequested.emit(self._time_at_x(float(event.pos().x())))

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self._should_ignore_mouse():
            return
        self.playheadRequested.emit(self._time_at_x(float(event.pos().x())))


class _PianoRollCanvas(QGraphicsView):
    """钢琴卷帘铺面编辑视图的实际画布（音符/音域框/背景网格/鼠标交互）"""

    notesChanged = pyqtSignal()
    instrumentRangeChanged = pyqtSignal(int, int)  # 仅在拖动黄色音域框改变范围时发出
    zoomChanged = pyqtSignal()  # 横向缩放比例变化（顶部标尺据此重绘）

    def __init__(self, mapped_pitches: Set[int], parent=None):
        super().__init__(parent)
        self._mapped_pitches = mapped_pitches
        self._notes: List[Dict] = []
        self._note_items: Dict[int, QGraphicsRectItem] = {}
        self._next_id = 0
        self._selected_ids: Set[int] = set()
        self._read_only = False
        self._drag_mode: Optional[str] = None
        self._drag_start_scene = None
        self._drag_note_start: Optional[Dict] = None
        self._drag_group_ids: Set[int] = set()
        self._drag_group_start: Dict[int, Dict] = {}
        self._drag_pending_collapse = False
        self._drag_moved = False
        self._select_rect_item: Optional[QGraphicsRectItem] = None
        self._pending_create_note: Optional[Dict] = None
        self._playhead_item: Optional[QGraphicsLineItem] = None
        self._background_items: List = []
        self._default_track = 0  # 新增音符使用的音轨号，由外部通过 set_default_track 设置
        self._current_total_seconds = MIN_SCENE_SECONDS

        # 内部剪贴板（Ctrl+C / Ctrl+X 的快照）与播放辅助线锚点
        self._clipboard: List[Dict] = []
        self._playhead_anchor_seconds = 0.0
        self._playhead_display_seconds = 0.0

        # 横向缩放：像素/秒（实例级，默认沿用模块常量）
        self._pixels_per_second = float(PIXELS_PER_SECOND)

        # 量化 / 小节网格
        self._quantize_seconds: Optional[float] = None
        self._measure_seconds: Optional[float] = None

        # 乐器音域框状态
        self._ladder: List[Tuple[int, str]] = get_chromatic_key_ladder()
        default_low = self._ladder[0][0]
        default_high = self._ladder[-1][0]
        self._range_low_pitch = default_low
        self._range_high_pitch = default_high
        self._range_visible = False
        self._range_item: Optional[QGraphicsRectItem] = None
        self._drag_range_start_low_idx = 0
        self._drag_range_span_idx = 0

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(QColor("#1B2631")))
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        # 左/上对齐：场景比视口窄时不会自动居中，视口坐标与场景坐标始终满足
        # 「视口 x = 场景 x - 横向滚动值」，标尺、点击定位与缩放锚点才能对齐
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self._build_background(MIN_SCENE_SECONDS)

    # ------------------------------------------------------------------
    # 坐标换算
    # ------------------------------------------------------------------
    def _time_to_x(self, t: float) -> float:
        return t * self._pixels_per_second

    def _x_to_time(self, x: float) -> float:
        return max(0.0, x / self._pixels_per_second)

    def _pitch_to_y(self, pitch: int) -> float:
        pitch = max(MIN_PITCH, min(MAX_PITCH, pitch))
        return (MAX_PITCH - pitch) * ROW_HEIGHT

    def _y_to_pitch(self, y: float) -> int:
        pitch = MAX_PITCH - int(y // ROW_HEIGHT)
        return max(MIN_PITCH, min(MAX_PITCH, pitch))

    # ------------------------------------------------------------------
    # 量化吸附
    # ------------------------------------------------------------------
    def set_quantize_grid(self, seconds: Optional[float]) -> None:
        """设置拖动量化网格间距（秒）；传 None 或 <=0 表示关闭量化（自由拖动）"""
        self._quantize_seconds = seconds if (seconds and seconds > 0) else None

    def _snap_time(self, t: float) -> float:
        """把时间吸附到从 0 起、以量化网格为间距的最近网格点；量化关闭时原样返回（钳制到 >=0）"""
        if not self._quantize_seconds:
            return max(0.0, t)
        grid = self._quantize_seconds
        return max(0.0, round(t / grid) * grid)

    def _snap_end_time(self, raw_end: float, min_end: float) -> float:
        """把结束时间吸附到最近网格点；若吸附结果早于 min_end（会导致时长小于最小时长
        限制），改用刚好满足 min_end 的最近合法网格点。量化关闭时只做 min_end 钳制。"""
        if not self._quantize_seconds:
            return max(min_end, raw_end)
        grid = self._quantize_seconds
        snapped = round(raw_end / grid) * grid
        if snapped < min_end:
            snapped = math.ceil(min_end / grid) * grid
            if snapped < min_end - 1e-9:
                snapped += grid
        return snapped

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------
    def set_notes(self, notes: List[Dict]) -> None:
        """加载一首曲目的音符列表，重建整个铺面"""
        self._scene.clear()  # 清空场景会连带销毁旧的图元，以下引用需一并重置
        self._note_items = {}
        self._selected_ids = set()
        self._drag_mode = None
        self._select_rect_item = None
        self._pending_create_note = None
        self._playhead_item = None
        self._range_item = None
        self._background_items = []

        self._notes = [dict(n) for n in notes]
        self._next_id = (max((n.get("id", 0) for n in self._notes), default=-1) + 1)

        total_seconds = max(
            (n.get("start", 0.0) + n.get("duration", 0.0) for n in self._notes),
            default=MIN_SCENE_SECONDS,
        )
        self._build_background(max(total_seconds + TRAILING_PADDING_SECONDS, MIN_SCENE_SECONDS))

        for note in self._notes:
            self._add_note_item(note)

        self._update_range_item_geometry()

        # 切换曲目后播放辅助线回到 0 秒并保持可见
        self._playhead_anchor_seconds = 0.0
        self._playhead_display_seconds = 0.0
        self._draw_playhead()

    def get_notes(self) -> List[Dict]:
        """返回当前铺面上的音符列表（副本）"""
        return [dict(n) for n in self._notes]

    def set_default_track(self, track_idx: int) -> None:
        """设置新增音符使用的音轨号；应传入当前曲目实际会被处理/保存的音轨之一
        （例如 processed_tracks[0]），否则新增的音符在另存为 MIDI 时会因为落在
        未被处理的音轨而被静默丢弃。"""
        self._default_track = track_idx

    def set_read_only(self, read_only: bool) -> None:
        """播放期间调用 True 禁用编辑交互，播放结束后调用 False 恢复"""
        self._read_only = read_only
        if read_only:
            self._drag_mode = None

    def is_read_only(self) -> bool:
        return self._read_only

    def set_playhead_anchor(self, seconds: float) -> None:
        """设置用户定位的播放辅助线位置（粘贴与播放起点都以此为基准）。"""
        self._playhead_anchor_seconds = max(0.0, float(seconds))
        self.set_playhead(self._playhead_anchor_seconds)

    def get_playhead_position(self) -> float:
        """返回播放辅助线的锚点时间（秒）。"""
        return self._playhead_anchor_seconds

    def set_playhead(self, seconds: Optional[float]) -> None:
        """更新播放线显示位置；传 None 表示播放结束，回落到用户定位的锚点并保持可见。"""
        if seconds is None:
            self._playhead_display_seconds = self._playhead_anchor_seconds
        else:
            self._playhead_display_seconds = max(0.0, float(seconds))
        self._draw_playhead()

    def _draw_playhead(self, focus: bool = True) -> None:
        if self._playhead_item is not None:
            self._scene.removeItem(self._playhead_item)
            self._playhead_item = None

        x = self._time_to_x(self._playhead_display_seconds)
        height = PITCH_COUNT * ROW_HEIGHT
        line = QGraphicsLineItem(x, 0, x, height)
        line.setPen(QPen(QColor("#F1C40F"), 2))
        line.setZValue(10)
        line.setAcceptedMouseButtons(Qt.NoButton)
        self._scene.addItem(line)
        self._playhead_item = line
        if focus:
            self.ensureVisible(QRectF(x - 5, 0, 10, height), 60, 0)

    def pixels_per_second(self) -> float:
        return self._pixels_per_second

    def set_pixels_per_second(self, value: float) -> None:
        """直接设置横向像素/秒比例（自动夹紧，不做视图锚定）；滚轮缩放走 wheelEvent。"""
        new_value = clamp_pixels_per_second(value)
        if abs(new_value - self._pixels_per_second) < 1e-9:
            return
        self._pixels_per_second = new_value
        self._rebuild_after_zoom()

    def viewport_x_for_time(self, seconds: float) -> float:
        """时间（秒）→ 当前视口横坐标（像素），使用场景映射而非算术近似。"""
        return float(self.mapFromScene(QPointF(self._time_to_x(seconds), 0.0)).x())

    def time_at_viewport_x(self, x: float) -> float:
        """当前视口横坐标（像素）→ 时间（秒），结果不小于 0。"""
        scene_x = float(self.mapToScene(QPoint(int(round(float(x))), 0)).x())
        return max(0.0, scene_x / self._pixels_per_second)

    def wheelEvent(self, event):
        """Shift+滚轮横向缩放（以鼠标所在时间为锚点）；否则保持原有纵向滚动。"""
        if not (event.modifiers() & Qt.ShiftModifier):
            super().wheelEvent(event)
            return

        delta_y = event.angleDelta().y()
        if delta_y == 0:
            # 纯横向滚轮（触控板常见）：不当作缩放，交回默认处理
            super().wheelEvent(event)
            return

        viewport_x = float(event.pos().x())
        anchor_time = self.time_at_viewport_x(viewport_x)
        factor = ZOOM_STEP_FACTOR if delta_y > 0 else 1.0 / ZOOM_STEP_FACTOR
        new_pps = clamp_pixels_per_second(self._pixels_per_second * factor)
        if abs(new_pps - self._pixels_per_second) < 1e-9:
            event.accept()
            return

        self._pixels_per_second = new_pps
        # 先重建场景（滚动条范围随之更新），再设置滚动值，否则旧上限会把
        # 锚点滚动值夹紧，缩放后视口偏移（时间轴末段尤其明显）
        self._rebuild_after_zoom()
        self.horizontalScrollBar().setValue(
            int(round(anchored_scroll_value(anchor_time, viewport_x, new_pps)))
        )
        event.accept()

    def _rebuild_after_zoom(self) -> None:
        """缩放后重建背景、重排全部音符与音域框、重绘播放线，并通知标尺刷新。"""
        self._build_background(self._current_total_seconds)
        for note in self._notes:
            self._update_item_geometry(note)
        self._update_range_item_geometry()
        self._draw_playhead(focus=False)
        rect = self._scene.sceneRect()
        self._scene.setSceneRect(0, 0, max(rect.width(), 400.0), rect.height())
        self.zoomChanged.emit()
        self.viewport().update()

    def rescale_times(self, factor: float) -> None:
        """按 factor 缩放全部音符时间与播放辅助线（BPM 变更使用）。"""
        if abs(factor - 1.0) < 1e-9:
            return
        self._notes = scaled_note_times(self._notes, factor)
        if self._clipboard:
            self._clipboard = scaled_note_times(self._clipboard, factor)
        self._playhead_anchor_seconds = max(0.0, self._playhead_anchor_seconds * factor)
        self._playhead_display_seconds = max(0.0, self._playhead_display_seconds * factor)
        for note in self._notes:
            self._update_item_geometry(note)
        total = max(
            (n["start"] + n["duration"] for n in self._notes), default=MIN_SCENE_SECONDS
        )
        self._ensure_scene_width(total)
        self._draw_playhead(focus=False)
        self.notesChanged.emit()

    def set_instrument_range(self, low_pitch: int, high_pitch: int) -> None:
        """整体设置框体的低/高边界音高（用于切换曲目时的完整重置）"""
        self._range_low_pitch = low_pitch
        self._range_high_pitch = high_pitch
        self._update_range_item_geometry()

    def set_instrument_span(self, span_idx: int) -> None:
        """按最低/最高映射下拉框的位置差重新计算框体跨度，保持框体当前低边界不变，
        只调整高边界；若新跨度会让高边界超出键位序列顶端，则把低边界下压以完整容纳
        这个跨度（与拖动到边界时的钳制方式一致），不回写下拉框。"""
        span_idx = max(0, span_idx)
        low_idx = self._nearest_ladder_index_for_pitch(self._range_low_pitch)
        max_low_idx = len(self._ladder) - 1 - span_idx
        low_idx = max(0, min(low_idx, max_low_idx))
        high_idx = low_idx + span_idx
        self._range_low_pitch = self._ladder[low_idx][0]
        self._range_high_pitch = self._ladder[high_idx][0]
        self._update_range_item_geometry()

    def set_instrument_range_visible(self, visible: bool) -> None:
        """切换乐器音域框的可见性（纯视觉开关，不影响播放使用的范围）"""
        self._range_visible = visible
        self._update_range_item_geometry()

    def get_instrument_range(self) -> Tuple[int, int]:
        """返回当前（未扩展半音的）最低/最高映射音高"""
        return self._range_low_pitch, self._range_high_pitch

    def set_measure_grid(self, seconds_per_measure: Optional[float]) -> None:
        """设置背景小节线的间距（秒）；传 None 或过小的值表示不画小节线"""
        if seconds_per_measure and seconds_per_measure >= MIN_MEASURE_SECONDS:
            self._measure_seconds = seconds_per_measure
        else:
            self._measure_seconds = None
        self._build_background(self._current_total_seconds)
        self._update_range_item_geometry()

    # ------------------------------------------------------------------
    # 背景（琴键行 + 秒线 + 小节线）
    # ------------------------------------------------------------------
    def _build_background(self, total_seconds: float) -> None:
        # 先移除上一次绘制的背景图元，避免场景宽度增长（_ensure_scene_width）
        # 重新调用本方法时把旧的琴键行/秒线/小节线堆叠成重复的图元
        for item in self._background_items:
            self._scene.removeItem(item)
        self._background_items = []
        self._current_total_seconds = total_seconds

        width = max(self._time_to_x(total_seconds), 400)
        height = PITCH_COUNT * ROW_HEIGHT
        self._scene.setSceneRect(0, 0, width, height)

        for i in range(PITCH_COUNT):
            pitch = MAX_PITCH - i
            y = i * ROW_HEIGHT
            is_black = _is_black_key(pitch)
            color = QColor("#2C3E50") if is_black else QColor("#3B4A5A")
            if pitch not in self._mapped_pitches:
                color = color.darker(130)

            row = QGraphicsRectItem(0, y, width, ROW_HEIGHT)
            row.setBrush(QBrush(color))
            row.setPen(QPen(Qt.NoPen))
            row.setZValue(-10)
            row.setAcceptedMouseButtons(Qt.NoButton)
            self._scene.addItem(row)
            self._background_items.append(row)

            if pitch % 12 == 0:  # 每个 C 音加标签
                label = QGraphicsSimpleTextItem(f"C{pitch // 12 - 1}")
                label.setBrush(QBrush(QColor("#AAB7B8")))
                label.setPos(2, y - 1)
                label.setZValue(-5)
                label.setAcceptedMouseButtons(Qt.NoButton)
                self._scene.addItem(label)
                self._background_items.append(label)

        seconds = int(total_seconds) + 1
        for s in range(seconds + 1):
            x = self._time_to_x(s)
            line = QGraphicsLineItem(x, 0, x, height)
            line.setPen(QPen(SECOND_LINE_COLOR, 1))
            line.setZValue(-8)
            line.setAcceptedMouseButtons(Qt.NoButton)
            self._scene.addItem(line)
            self._background_items.append(line)

        if self._measure_seconds:
            measure_idx = 0
            m = 0.0
            # 安全上限：避免拍号/BPM 异常导致的极小间距画出海量图元
            max_lines = 20000
            count = 0
            while m <= total_seconds + 1e-9 and count < max_lines:
                x = self._time_to_x(m)
                line = QGraphicsLineItem(x, 0, x, height)
                line.setPen(QPen(MEASURE_LINE_COLOR, 2))
                line.setZValue(-7)
                line.setAcceptedMouseButtons(Qt.NoButton)
                self._scene.addItem(line)
                self._background_items.append(line)
                measure_idx += 1
                m = measure_idx * self._measure_seconds
                count += 1

    def _ensure_scene_width(self, seconds: float) -> None:
        needed_width = self._time_to_x(seconds + TRAILING_PADDING_SECONDS)
        rect = self._scene.sceneRect()
        if needed_width > rect.width():
            # 已有音符图元不受场景宽度变化影响，只需重绘背景（内部已处理去重）
            # 与音域框（宽度依赖场景宽度，需要跟着重新计算）
            self._build_background(seconds + TRAILING_PADDING_SECONDS)
            self._update_range_item_geometry()

    # ------------------------------------------------------------------
    # 乐器音域框
    # ------------------------------------------------------------------
    def _update_range_item_geometry(self) -> None:
        if self._range_item is not None:
            self._scene.removeItem(self._range_item)
            self._range_item = None

        if not self._range_visible:
            return

        ext_low = self._range_low_pitch - 1
        ext_high = self._range_high_pitch + 1
        y_top = self._pitch_to_y(ext_high)
        y_bottom = self._pitch_to_y(ext_low) + ROW_HEIGHT
        width = self._scene.sceneRect().width()

        item = QGraphicsRectItem(0, y_top, width, y_bottom - y_top)
        item.setBrush(QBrush(RANGE_FILL_COLOR))
        item.setPen(QPen(RANGE_BORDER_COLOR, 2))
        item.setZValue(3)  # 背景网格之上、音符之下
        item.setAcceptedMouseButtons(Qt.NoButton)
        self._scene.addItem(item)
        self._range_item = item

    def _range_band_y_bounds(self) -> Tuple[float, float]:
        ext_low = self._range_low_pitch - 1
        ext_high = self._range_high_pitch + 1
        y_top = self._pitch_to_y(ext_high)
        y_bottom = self._pitch_to_y(ext_low) + ROW_HEIGHT
        return y_top, y_bottom

    def _is_within_range_band(self, y: float) -> bool:
        y_top, y_bottom = self._range_band_y_bounds()
        return y_top <= y <= y_bottom

    def _nearest_ladder_index_for_pitch(self, pitch: float) -> int:
        best_idx = 0
        best_dist = None
        for i, (p, _label) in enumerate(self._ladder):
            d = abs(p - pitch)
            if best_dist is None or d < best_dist:
                best_dist, best_idx = d, i
        return best_idx

    # ------------------------------------------------------------------
    # 音符图元
    # ------------------------------------------------------------------
    def _note_brush(self, note: Dict, selected: bool) -> QBrush:
        if note.get("mapped", True):
            color = QColor("#58D68D") if not selected else QColor("#F5B041")
        else:
            color = QColor("#7F8C8D") if not selected else QColor("#E59866")
        return QBrush(color)

    def _add_note_item(self, note: Dict) -> None:
        item = QGraphicsRectItem()
        item.setZValue(5)
        item.setData(0, note["id"])
        self._scene.addItem(item)
        self._note_items[note["id"]] = item
        self._update_item_geometry(note)

    def _update_item_geometry(self, note: Dict) -> None:
        item = self._note_items.get(note["id"])
        if item is None:
            return
        x = self._time_to_x(note["start"])
        y = self._pitch_to_y(note["pitch"])
        w = max(4.0, note["duration"] * self._pixels_per_second)
        item.setRect(x, y, w, ROW_HEIGHT - 1)
        selected = note["id"] in self._selected_ids
        item.setBrush(self._note_brush(note, selected))
        item.setPen(QPen(QColor("#1B2631" if not selected else "#F4D03F"), 1 if not selected else 2))

    def _note_by_id(self, note_id: int) -> Optional[Dict]:
        for n in self._notes:
            if n["id"] == note_id:
                return n
        return None

    def _set_selection(self, new_ids: Set[int]) -> None:
        old_ids = self._selected_ids
        if new_ids == old_ids:
            return
        self._selected_ids = set(new_ids)
        for note_id in old_ids ^ new_ids:
            note = self._note_by_id(note_id)
            if note:
                self._update_item_geometry(note)

    def _select_note(self, note_id: Optional[int]) -> None:
        self._set_selection({note_id} if note_id is not None else set())

    def _hit_test(self, scene_pos) -> Optional[int]:
        for note_id, item in self._note_items.items():
            if item.rect().contains(scene_pos):
                return note_id
        return None

    def _delete_note(self, note_id: int) -> None:
        item = self._note_items.pop(note_id, None)
        if item is not None:
            self._scene.removeItem(item)
        self._notes = [n for n in self._notes if n["id"] != note_id]
        if note_id in self._selected_ids:
            self._selected_ids.discard(note_id)
        self.notesChanged.emit()

    def _delete_selected(self) -> None:
        ids = set(self._selected_ids)
        if not ids:
            return
        for note_id in ids:
            item = self._note_items.pop(note_id, None)
            if item is not None:
                self._scene.removeItem(item)
        self._notes = [n for n in self._notes if n["id"] not in ids]
        self._selected_ids -= ids
        self.notesChanged.emit()

    # ------------------------------------------------------------------
    # 剪贴板
    # ------------------------------------------------------------------
    def _copy_selected(self) -> None:
        """把当前选中音符深拷贝进内部剪贴板；无选中时保持原剪贴板。"""
        if not self._selected_ids:
            return
        self._clipboard = [dict(n) for n in self._notes if n["id"] in self._selected_ids]

    def _paste_clipboard(self) -> None:
        """把剪贴板全部音符粘贴到播放辅助线锚点处，并选中新音符。"""
        if not self._clipboard:
            return
        anchor = float(self._playhead_anchor_seconds)
        starts = pasted_starts(self._clipboard, anchor)
        pasted: List[Dict] = []
        for source, start in zip(self._clipboard, starts):
            note = dict(source)
            note["id"] = self._next_id
            self._next_id += 1
            note["start"] = start
            note["mapped"] = int(note["pitch"]) in self._mapped_pitches
            self._notes.append(note)
            self._add_note_item(note)
            pasted.append(note)
        self._set_selection({n["id"] for n in pasted})
        max_end = max(n["start"] + n["duration"] for n in pasted)
        self._ensure_scene_width(max_end)
        self.notesChanged.emit()

    def _shift_selected_octave(self, delta: int) -> None:
        """把选中音符整体移动 delta 个半音；会越界的音符保持原音高。"""
        if not self._selected_ids:
            return
        targets = octave_shift_pitches(self._notes, self._selected_ids, delta)
        changed = False
        for note in self._notes:
            target = targets.get(note["id"])
            if target is None or target == note["pitch"]:
                continue
            note["pitch"] = target
            note["mapped"] = target in self._mapped_pitches
            self._update_item_geometry(note)
            changed = True
        if changed:
            self.notesChanged.emit()

    # ------------------------------------------------------------------
    # 鼠标 / 键盘交互
    # ------------------------------------------------------------------
    def mousePressEvent(self, event):
        if self._read_only:
            return

        scene_pos = self.mapToScene(event.pos())

        if event.button() == Qt.RightButton:
            note_id = self._hit_test(scene_pos)
            if note_id is not None:
                # 右键菜单只针对被点击的这一个音符生效，不改变当前多选集合
                # （不调用 _set_selection，避免清空原本选中的其余音符）
                self._show_context_menu(note_id, event.globalPos())
            return

        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return

        modifiers = event.modifiers()
        toggle = bool(modifiers & (Qt.ControlModifier | Qt.ShiftModifier))

        note_id = self._hit_test(scene_pos)
        if note_id is not None:
            note = self._note_by_id(note_id)
            item = self._note_items[note_id]
            rect = item.rect()
            near_right_edge = (rect.right() - scene_pos.x()) <= RESIZE_MARGIN

            if toggle:
                new_ids = set(self._selected_ids)
                if note_id in new_ids:
                    new_ids.discard(note_id)
                else:
                    new_ids.add(note_id)
                self._set_selection(new_ids)
                self._drag_mode = None
                event.accept()
                return

            self._drag_start_scene = scene_pos
            self._drag_note_start = dict(note)
            self._drag_moved = False

            if near_right_edge:
                # 调整时长恒定只针对被点击的这一个音符，不受多选影响
                self._set_selection({note_id})
                self._drag_mode = "resize"
                self._drag_group_ids = {note_id}
                self._drag_group_start = {note_id: dict(note)}
                self._drag_pending_collapse = False
            else:
                already_in_group = note_id in self._selected_ids and len(self._selected_ids) > 1
                if not already_in_group:
                    self._set_selection({note_id})
                self._drag_mode = "move"
                self._drag_group_ids = set(self._selected_ids)
                self._drag_group_start = {
                    nid: dict(self._note_by_id(nid)) for nid in self._drag_group_ids if self._note_by_id(nid)
                }
                self._drag_pending_collapse = already_in_group
        elif self._range_visible and self._is_within_range_band(scene_pos.y()):
            self._select_note(None)
            self._drag_mode = "range"
            self._drag_start_scene = scene_pos
            low_idx = self._nearest_ladder_index_for_pitch(self._range_low_pitch)
            high_idx = self._nearest_ladder_index_for_pitch(self._range_high_pitch)
            self._drag_range_start_low_idx = low_idx
            self._drag_range_span_idx = high_idx - low_idx
        else:
            pitch = self._y_to_pitch(scene_pos.y())
            start = max(0.0, self._x_to_time(scene_pos.x()))
            self._pending_create_note = {"pitch": pitch, "start": round(start, 3)}
            self._drag_mode = "select-rect-or-create"
            self._drag_start_scene = scene_pos
            self._select_rect_item = None

        event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_mode == "range" and not self._read_only:
            scene_pos = self.mapToScene(event.pos())
            dy = scene_pos.y() - self._drag_start_scene.y()
            # 目标音高必须按渲染网格的像素/半音比例（ROW_HEIGHT 像素 = 1 个半音）换算，
            # 与框体的实际渲染位置（_pitch_to_y）保持 1:1，再吸附到距离最近的键位序列
            # 位置。这里刻意保留连续（未取整的）目标音高，不对 dy/ROW_HEIGHT 提前取整：
            # 提前取整会和随后按最近音高吸附时的平局裁决叠加，使 B、E 两个键的可命中像
            # 素窗口显著窄于其余键位（实测约 10px vs 20px），正常速度拖动时更容易被跳
            # 过；改为连续目标音高后，每个自然键的命中窗口只由其左右真实半音间隔决定
            # （多数键 20px，B-C/E-F 相关的 4 个键各 15px），不再因为浮点/整数取整顺序
            # 产生额外的不对称收窄。
            drag_start_low_pitch = self._ladder[self._drag_range_start_low_idx][0]
            target_low_pitch = drag_start_low_pitch - dy / ROW_HEIGHT
            new_low_idx = self._nearest_ladder_index_for_pitch(target_low_pitch)
            max_low_idx = len(self._ladder) - 1 - self._drag_range_span_idx
            new_low_idx = max(0, min(new_low_idx, max_low_idx))
            new_high_idx = new_low_idx + self._drag_range_span_idx

            new_low_pitch = self._ladder[new_low_idx][0]
            new_high_pitch = self._ladder[new_high_idx][0]

            if (new_low_pitch, new_high_pitch) != (self._range_low_pitch, self._range_high_pitch):
                self._range_low_pitch = new_low_pitch
                self._range_high_pitch = new_high_pitch
                self._update_range_item_geometry()
                self.instrumentRangeChanged.emit(new_low_pitch, new_high_pitch)
            return

        if self._drag_mode == "select-rect-or-create" and not self._read_only:
            scene_pos = self.mapToScene(event.pos())
            if self._select_rect_item is None:
                dx = scene_pos.x() - self._drag_start_scene.x()
                dy = scene_pos.y() - self._drag_start_scene.y()
                if abs(dx) < CLICK_DRAG_THRESHOLD and abs(dy) < CLICK_DRAG_THRESHOLD:
                    return
                self._pending_create_note = None
                rect_item = QGraphicsRectItem()
                rect_item.setBrush(QBrush(SELECT_RECT_FILL_COLOR))
                rect_item.setPen(QPen(SELECT_RECT_BORDER_COLOR, 1, Qt.DashLine))
                rect_item.setZValue(20)
                rect_item.setAcceptedMouseButtons(Qt.NoButton)
                self._scene.addItem(rect_item)
                self._select_rect_item = rect_item
            rect = QRectF(self._drag_start_scene, scene_pos).normalized()
            self._select_rect_item.setRect(rect)
            return

        if self._drag_mode in ("move", "resize") and not self._read_only and self._drag_note_start is not None:
            scene_pos = self.mapToScene(event.pos())
            anchor_note = self._note_by_id(self._drag_note_start["id"])
            if anchor_note is None:
                return

            if self._drag_mode == "move":
                dx = scene_pos.x() - self._drag_start_scene.x()
                dy = scene_pos.y() - self._drag_start_scene.y()
                if dx or dy:
                    self._drag_moved = True

                raw_anchor_start = max(
                    0.0, self._drag_note_start["start"] + dx / self._pixels_per_second
                )
                snapped_anchor_start = self._snap_time(raw_anchor_start)
                time_delta = snapped_anchor_start - self._drag_note_start["start"]

                row_delta = round(dy / ROW_HEIGHT)
                pitch_delta = -row_delta

                group_ids = self._drag_group_ids if self._drag_group_ids else {self._drag_note_start["id"]}
                for nid in group_ids:
                    start_note = self._drag_group_start.get(nid)
                    note = self._note_by_id(nid)
                    if note is None or start_note is None:
                        continue
                    new_start = max(0.0, start_note["start"] + time_delta)
                    new_pitch = max(MIN_PITCH, min(MAX_PITCH, start_note["pitch"] + pitch_delta))
                    note["start"] = round(new_start, 3)
                    note["pitch"] = new_pitch
                    note["mapped"] = new_pitch in self._mapped_pitches
                    self._update_item_geometry(note)
            elif self._drag_mode == "resize":
                dx = scene_pos.x() - self._drag_start_scene.x()
                if dx:
                    self._drag_moved = True
                raw_end = (
                    self._drag_note_start["start"]
                    + self._drag_note_start["duration"]
                    + dx / self._pixels_per_second
                )
                min_end = self._drag_note_start["start"] + MIN_NOTE_DURATION
                new_end = self._snap_end_time(raw_end, min_end)
                anchor_note["duration"] = round(new_end - self._drag_note_start["start"], 3)
                self._update_item_geometry(anchor_note)
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_mode == "range":
            self._drag_mode = None
            return

        if self._drag_mode == "select-rect-or-create":
            if self._select_rect_item is not None:
                rect = self._select_rect_item.rect()
                self._scene.removeItem(self._select_rect_item)
                self._select_rect_item = None
                hit_ids = {nid for nid, item in self._note_items.items() if item.rect().intersects(rect)}
                self._set_selection(hit_ids)
            elif self._pending_create_note is not None and not self._read_only:
                pitch = self._pending_create_note["pitch"]
                start = self._pending_create_note["start"]
                note = {
                    "id": self._next_id,
                    "track": self._default_track,
                    "channel": 0,
                    "pitch": pitch,
                    "start": start,
                    "duration": DEFAULT_NOTE_DURATION,
                    "velocity": 100,
                    "mapped": pitch in self._mapped_pitches,
                }
                self._next_id += 1
                self._notes.append(note)
                self._add_note_item(note)
                self._select_note(note["id"])
                self._ensure_scene_width(start + DEFAULT_NOTE_DURATION)
                self.notesChanged.emit()
            self._pending_create_note = None
            self._drag_mode = None
            return

        if self._drag_mode in ("move", "resize"):
            if self._drag_mode == "move" and not self._drag_moved and self._drag_pending_collapse:
                # 未发生实际拖动的普通单击：即使点在原多选集合内，也收窄为只选中这一个
                if self._drag_note_start is not None:
                    self._select_note(self._drag_note_start["id"])

            group_ids = self._drag_group_ids or (
                {self._drag_note_start["id"]} if self._drag_note_start else set()
            )
            self._drag_mode = None
            self._drag_note_start = None
            self._drag_group_ids = set()
            self._drag_group_start = {}
            self._drag_pending_collapse = False

            max_end = 0.0
            for nid in group_ids:
                note = self._note_by_id(nid)
                if note is not None:
                    max_end = max(max_end, note["start"] + note["duration"])
            if max_end > 0.0:
                self._ensure_scene_width(max_end)
            self.notesChanged.emit()
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if self._read_only:
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key_A and bool(event.modifiers() & Qt.ControlModifier):
            self._set_selection(set(self._note_items.keys()))
            event.accept()
            return

        if event.key() == Qt.Key_C and bool(event.modifiers() & Qt.ControlModifier):
            self._copy_selected()
            event.accept()
            return

        if event.key() == Qt.Key_X and bool(event.modifiers() & Qt.ControlModifier):
            self._copy_selected()
            self._delete_selected()
            event.accept()
            return

        if event.key() == Qt.Key_V and bool(event.modifiers() & Qt.ControlModifier):
            self._paste_clipboard()
            event.accept()
            return

        if event.modifiers() & Qt.ShiftModifier and event.key() in (Qt.Key_Up, Qt.Key_Down):
            self._shift_selected_octave(12 if event.key() == Qt.Key_Up else -12)
            event.accept()
            return

        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self._selected_ids:
            self._delete_selected()
            event.accept()
            return

        super().keyPressEvent(event)

    def _show_context_menu(self, note_id: int, global_pos) -> None:
        menu = QMenu(self)
        delete_action = QAction("删除音符", self)
        delete_action.triggered.connect(lambda: self._delete_note(note_id))
        menu.addAction(delete_action)
        menu.exec_(global_pos)


class PianoRollWidget(QWidget):
    """钢琴卷帘铺面编辑视图：左侧纯视觉钢琴键盘 + 右侧可编辑画布的容器；
    对外方法与信号透传给内部画布，保持与旧版本一致的公开接口。"""

    def __init__(self, mapped_pitches: Set[int], parent=None):
        super().__init__(parent)
        self._canvas = _PianoRollCanvas(mapped_pitches, parent=self)
        self._keyboard = _PianoKeyboardWidget(self._canvas, mapped_pitches, parent=self)
        self._ruler = _TimeRulerWidget(self._canvas, parent=self)

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        content.addWidget(self._keyboard)
        content.addWidget(self._canvas)

        ruler_row = QHBoxLayout()
        ruler_row.setContentsMargins(0, 0, 0, 0)
        ruler_row.setSpacing(0)
        ruler_row.addSpacing(KEYBOARD_WIDTH)
        ruler_row.addWidget(self._ruler)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(ruler_row)
        layout.addLayout(content, 1)

        # 标尺定位请求 → 播放辅助线锚点
        self._ruler.playheadRequested.connect(self._canvas.set_playhead_anchor)

        # 透传信号：直接引用内部画布的已绑定信号对象，外部 connect/emit 行为不变
        self.notesChanged = self._canvas.notesChanged
        self.instrumentRangeChanged = self._canvas.instrumentRangeChanged
        self.zoomChanged = self._canvas.zoomChanged

    def set_notes(self, notes: List[Dict]) -> None:
        self._canvas.set_notes(notes)

    def get_notes(self) -> List[Dict]:
        return self._canvas.get_notes()

    def set_default_track(self, track_idx: int) -> None:
        self._canvas.set_default_track(track_idx)

    def set_read_only(self, read_only: bool) -> None:
        self._canvas.set_read_only(read_only)

    def set_playhead(self, seconds: Optional[float]) -> None:
        self._canvas.set_playhead(seconds)

    def set_playhead_anchor(self, seconds: float) -> None:
        """把播放辅助线定位到指定秒数（粘贴与播放起点以此为基准）"""
        self._canvas.set_playhead_anchor(seconds)

    def get_playhead_position(self) -> float:
        """返回播放辅助线的锚点时间（秒）"""
        return self._canvas.get_playhead_position()

    def set_beat_grid(
        self, seconds_per_beat: Optional[float], beats_per_measure: int
    ) -> None:
        """把每拍秒数与每小节拍数传给顶部标尺"""
        self._ruler.set_beat_grid(seconds_per_beat, beats_per_measure)

    def rescale_times(self, factor: float) -> None:
        """按 factor 缩放全部音符时间与播放辅助线（BPM 变更使用）"""
        self._canvas.rescale_times(factor)

    def set_instrument_range(self, low_pitch: int, high_pitch: int) -> None:
        self._canvas.set_instrument_range(low_pitch, high_pitch)

    def set_instrument_span(self, span_idx: int) -> None:
        self._canvas.set_instrument_span(span_idx)

    def set_instrument_range_visible(self, visible: bool) -> None:
        self._canvas.set_instrument_range_visible(visible)

    def get_instrument_range(self) -> Tuple[int, int]:
        return self._canvas.get_instrument_range()

    def set_quantize_grid(self, seconds: Optional[float]) -> None:
        """设置拖动量化网格间距（秒）；传 None 表示关闭量化（自由拖动）"""
        self._canvas.set_quantize_grid(seconds)

    def set_measure_grid(self, seconds_per_measure: Optional[float]) -> None:
        """设置背景小节线间距（秒）；传 None 表示不画小节线"""
        self._canvas.set_measure_grid(seconds_per_measure)
