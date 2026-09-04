"""
铺面编辑组件

以钢琴卷帘（piano roll）形式展示与编辑一首曲目的结构化音符列表：
- 纵轴覆盖钢琴全部88键（MIDI 21 A0 ~ 108 C8），左侧带一条纯视觉的钢琴键盘参照
- 横轴为绝对时间（秒），背景叠加逐秒参考线与（可选的）小节线
- 支持新增 / 删除 / 拖动（音高+起始时间）/ 拖动右边缘调整时长，可选量化吸附
- 支持 Ctrl+A / 矩形框选 / Ctrl·Shift+单击 的多选，多选后可整体拖动、整体删除
- 支持展示随实际播放进度移动的播放线，并可在播放期间禁用编辑
- 支持展示/拖动一个黄色半透明的「乐器音域框」，用于框定乐器实际可用的键位区间
"""

import math
from typing import Dict, List, Optional, Set, Tuple

from PyQt5.QtCore import QPoint, QRectF, Qt, pyqtSignal
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
    QWidget,
)

from build_music import get_natural_key_ladder

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


class _PianoRollCanvas(QGraphicsView):
    """钢琴卷帘铺面编辑视图的实际画布（音符/音域框/背景网格/鼠标交互）"""

    notesChanged = pyqtSignal()
    instrumentRangeChanged = pyqtSignal(int, int)  # 仅在拖动黄色音域框改变范围时发出

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

        # 量化 / 小节网格
        self._quantize_seconds: Optional[float] = None
        self._measure_seconds: Optional[float] = None

        # 乐器音域框状态
        self._ladder: List[Tuple[int, str]] = get_natural_key_ladder()
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

        self._build_background(MIN_SCENE_SECONDS)

    # ------------------------------------------------------------------
    # 坐标换算
    # ------------------------------------------------------------------
    def _time_to_x(self, t: float) -> float:
        return t * PIXELS_PER_SECOND

    def _x_to_time(self, x: float) -> float:
        return max(0.0, x / PIXELS_PER_SECOND)

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

    def set_playhead(self, seconds: Optional[float]) -> None:
        """设置/清除播放线位置；传 None 表示隐藏播放线"""
        if self._playhead_item is not None:
            self._scene.removeItem(self._playhead_item)
            self._playhead_item = None

        if seconds is None:
            return

        x = self._time_to_x(max(0.0, seconds))
        height = PITCH_COUNT * ROW_HEIGHT
        line = QGraphicsLineItem(x, 0, x, height)
        line.setPen(QPen(QColor("#F1C40F"), 2))
        line.setZValue(10)
        line.setAcceptedMouseButtons(Qt.NoButton)
        self._scene.addItem(line)
        self._playhead_item = line
        self.ensureVisible(QRectF(x - 5, 0, 10, height), 60, 0)

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

    def _nearest_ladder_index_for_pitch(self, pitch: int) -> int:
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
        w = max(4.0, note["duration"] * PIXELS_PER_SECOND)
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
            # 按键位序列的位置步长（而非原始 MIDI 半音距离）换算拖动增量：
            # B-C、E-F 之间相邻自然键只差 1 个半音，若按半音距离取最近键，
            # 这两个位置的可命中像素区间只有其余键位的一半，正常速度拖动就会被跳过。
            idx_delta = round(dy / ROW_HEIGHT)
            new_low_idx = self._drag_range_start_low_idx - idx_delta
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

                raw_anchor_start = max(0.0, self._drag_note_start["start"] + dx / PIXELS_PER_SECOND)
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
                    self._drag_note_start["start"] + self._drag_note_start["duration"] + dx / PIXELS_PER_SECOND
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

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._keyboard)
        layout.addWidget(self._canvas)

        # 透传信号：直接引用内部画布的已绑定信号对象，外部 connect/emit 行为不变
        self.notesChanged = self._canvas.notesChanged
        self.instrumentRangeChanged = self._canvas.instrumentRangeChanged

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
