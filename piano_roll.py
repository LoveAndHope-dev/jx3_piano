"""
铺面编辑组件

以钢琴卷帘（piano roll）形式展示与编辑一首曲目的结构化音符列表：
- 纵轴覆盖钢琴全部88键（MIDI 21 A0 ~ 108 C8）
- 横轴为绝对时间（秒），不做小节量化
- 支持新增 / 删除 / 拖动（音高+起始时间）/ 拖动右边缘调整时长
- 支持展示随实际播放进度移动的播放线，并可在播放期间禁用编辑
- 支持展示/拖动一个黄色半透明的「乐器音域框」，用于框定乐器实际可用的键位区间
"""

from typing import Dict, List, Optional, Set, Tuple

from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import (
    QAction,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QMenu,
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

RANGE_FILL_COLOR = QColor(255, 196, 0, 110)
RANGE_BORDER_COLOR = QColor(255, 214, 10, 235)

# 一个八度内的黑键相对半音位置（以C为0）
_BLACK_KEY_OFFSETS = {1, 3, 6, 8, 10}


def _is_black_key(pitch: int) -> bool:
    return (pitch % 12) in _BLACK_KEY_OFFSETS


class PianoRollWidget(QGraphicsView):
    """钢琴卷帘铺面编辑视图"""

    notesChanged = pyqtSignal()
    instrumentRangeChanged = pyqtSignal(int, int)  # 仅在拖动黄色音域框改变范围时发出

    def __init__(self, mapped_pitches: Set[int], parent=None):
        super().__init__(parent)
        self._mapped_pitches = mapped_pitches
        self._notes: List[Dict] = []
        self._note_items: Dict[int, QGraphicsRectItem] = {}
        self._next_id = 0
        self._selected_note_id: Optional[int] = None
        self._read_only = False
        self._drag_mode: Optional[str] = None
        self._drag_start_scene = None
        self._drag_note_start: Optional[Dict] = None
        self._playhead_item: Optional[QGraphicsLineItem] = None
        self._background_items: List = []
        self._default_track = 0  # 新增音符使用的音轨号，由外部通过 set_default_track 设置

        # 乐器音域框状态
        self._ladder: List[Tuple[int, str]] = get_natural_key_ladder()
        default_low = self._ladder[0][0]
        default_high = self._ladder[-1][0]
        self._range_low_pitch = default_low
        self._range_high_pitch = default_high
        self._range_visible = False
        self._range_item: Optional[QGraphicsRectItem] = None
        self._drag_range_start_low = 0
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
    # 公开接口
    # ------------------------------------------------------------------
    def set_notes(self, notes: List[Dict]) -> None:
        """加载一首曲目的音符列表，重建整个铺面"""
        self._scene.clear()  # 清空场景会连带销毁旧的图元，以下引用需一并重置
        self._note_items = {}
        self._selected_note_id = None
        self._drag_mode = None
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
        """设置乐器音域框的（未扩展半音的）最低/最高映射音高，由外部下拉框调用"""
        self._range_low_pitch = low_pitch
        self._range_high_pitch = high_pitch
        self._update_range_item_geometry()

    def set_instrument_range_visible(self, visible: bool) -> None:
        """切换乐器音域框的可见性（纯视觉开关，不影响播放使用的范围）"""
        self._range_visible = visible
        self._update_range_item_geometry()

    def get_instrument_range(self) -> Tuple[int, int]:
        """返回当前（未扩展半音的）最低/最高映射音高"""
        return self._range_low_pitch, self._range_high_pitch

    # ------------------------------------------------------------------
    # 背景（琴键行 + 秒线）
    # ------------------------------------------------------------------
    def _build_background(self, total_seconds: float) -> None:
        # 先移除上一次绘制的背景图元，避免场景宽度增长（_ensure_scene_width）
        # 重新调用本方法时把旧的琴键行/秒线堆叠成重复的图元
        for item in self._background_items:
            self._scene.removeItem(item)
        self._background_items = []

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
            line.setPen(QPen(QColor("#25313D"), 1))
            line.setZValue(-8)
            line.setAcceptedMouseButtons(Qt.NoButton)
            self._scene.addItem(line)
            self._background_items.append(line)

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
        selected = note["id"] == self._selected_note_id
        item.setBrush(self._note_brush(note, selected))
        item.setPen(QPen(QColor("#1B2631" if not selected else "#F4D03F"), 1 if not selected else 2))

    def _note_by_id(self, note_id: int) -> Optional[Dict]:
        for n in self._notes:
            if n["id"] == note_id:
                return n
        return None

    def _select_note(self, note_id: Optional[int]) -> None:
        previous = self._selected_note_id
        self._selected_note_id = note_id
        if previous is not None and previous in self._note_items:
            note = self._note_by_id(previous)
            if note:
                self._update_item_geometry(note)
        if note_id is not None and note_id in self._note_items:
            note = self._note_by_id(note_id)
            if note:
                self._update_item_geometry(note)

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
        if self._selected_note_id == note_id:
            self._selected_note_id = None
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
                self._select_note(note_id)
                self._show_context_menu(note_id, event.globalPos())
            return

        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return

        note_id = self._hit_test(scene_pos)
        if note_id is not None:
            note = self._note_by_id(note_id)
            item = self._note_items[note_id]
            rect = item.rect()
            near_right_edge = (rect.right() - scene_pos.x()) <= RESIZE_MARGIN

            self._select_note(note_id)
            self._drag_mode = "resize" if near_right_edge else "move"
            self._drag_start_scene = scene_pos
            self._drag_note_start = dict(note)
        elif self._range_visible and self._is_within_range_band(scene_pos.y()):
            self._select_note(None)
            self._drag_mode = "range"
            self._drag_start_scene = scene_pos
            self._drag_range_start_low = self._range_low_pitch
            low_idx = self._nearest_ladder_index_for_pitch(self._range_low_pitch)
            high_idx = self._nearest_ladder_index_for_pitch(self._range_high_pitch)
            self._drag_range_span_idx = high_idx - low_idx
        else:
            pitch = self._y_to_pitch(scene_pos.y())
            start = round(self._x_to_time(scene_pos.x()), 3)
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

        event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_mode == "range" and not self._read_only:
            scene_pos = self.mapToScene(event.pos())
            dy = scene_pos.y() - self._drag_start_scene.y()
            row_delta = round(dy / ROW_HEIGHT)
            target_low_pitch = self._drag_range_start_low - row_delta

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

        if self._drag_mode and not self._read_only and self._drag_note_start is not None:
            scene_pos = self.mapToScene(event.pos())
            note = self._note_by_id(self._drag_note_start["id"])
            if note is None:
                return

            if self._drag_mode == "move":
                dx = scene_pos.x() - self._drag_start_scene.x()
                dy = scene_pos.y() - self._drag_start_scene.y()
                new_start = max(0.0, self._drag_note_start["start"] + dx / PIXELS_PER_SECOND)
                row_delta = round(dy / ROW_HEIGHT)
                new_pitch = self._drag_note_start["pitch"] - row_delta
                new_pitch = max(MIN_PITCH, min(MAX_PITCH, new_pitch))

                note["start"] = round(new_start, 3)
                note["pitch"] = new_pitch
                note["mapped"] = new_pitch in self._mapped_pitches
                self._update_item_geometry(note)
            elif self._drag_mode == "resize":
                dx = scene_pos.x() - self._drag_start_scene.x()
                new_duration = max(
                    MIN_NOTE_DURATION, self._drag_note_start["duration"] + dx / PIXELS_PER_SECOND
                )
                note["duration"] = round(new_duration, 3)
                self._update_item_geometry(note)
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_mode == "range":
            self._drag_mode = None
            return

        if self._drag_mode:
            note = self._note_by_id(self._drag_note_start["id"]) if self._drag_note_start else None
            self._drag_mode = None
            self._drag_note_start = None
            if note is not None:
                self._ensure_scene_width(note["start"] + note["duration"])
            self.notesChanged.emit()
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if (
            event.key() in (Qt.Key_Delete, Qt.Key_Backspace)
            and self._selected_note_id is not None
            and not self._read_only
        ):
            self._delete_note(self._selected_note_id)
            event.accept()
            return
        super().keyPressEvent(event)

    def _show_context_menu(self, note_id: int, global_pos) -> None:
        menu = QMenu(self)
        delete_action = QAction("删除音符", self)
        delete_action.triggered.connect(lambda: self._delete_note(note_id))
        menu.addAction(delete_action)
        menu.exec_(global_pos)
