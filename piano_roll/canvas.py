"""铺面画布：状态、剪贴板与对外操作。"""

import math
from typing import Dict, List, Optional, Set, Tuple

from PyQt5.QtCore import QPoint, QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)

from arpeggiate_runner import arpeggiate_notes
from build_music import get_chromatic_key_ladder

from .canvas_input import CanvasInputMixin
from .canvas_paint import CanvasPaintMixin
from .geometry import *  # noqa: F401,F403
from .geometry import _is_black_key


class _PianoRollCanvas(CanvasInputMixin, CanvasPaintMixin, QGraphicsView):
    """钢琴卷帘铺面编辑视图的实际画布（音符/音域框/背景网格/鼠标交互）"""

    notesChanged = pyqtSignal()
    instrumentRangeChanged = pyqtSignal(int, int)  # 仅在拖动黄色音域框改变范围时发出
    zoomChanged = pyqtSignal()  # 横向缩放比例变化（顶部标尺据此重绘）
    undoRequested = pyqtSignal()  # 编辑模式下按 Ctrl+Z
    redoRequested = pyqtSignal()  # 编辑模式下按 Ctrl+Shift+Z

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
        self._playhead_locked = False

        # 横向缩放：像素/秒（实例级，默认沿用模块常量）
        self._pixels_per_second = float(PIXELS_PER_SECOND)
        # 纵向行高（实例级，支持 Shift+滚轮缩放）
        self._row_height = float(ROW_HEIGHT)

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
        return (MAX_PITCH - pitch) * self._row_height

    def _y_to_pitch(self, y: float) -> int:
        pitch = MAX_PITCH - int(y // self._row_height)
        return max(MIN_PITCH, min(MAX_PITCH, pitch))

    @property
    def row_height(self) -> float:
        return self._row_height

    def set_row_height(
        self, value: float, anchor_scene_y: Optional[float] = None, anchor_viewport_y: Optional[float] = None
    ) -> None:
        """纵向缩放行高；保持锚点音高在视口中的纵向位置不变。"""
        new_height = max(MIN_ROW_HEIGHT, min(MAX_ROW_HEIGHT, float(value)))
        old_height = self._row_height
        if abs(new_height - old_height) < 1e-9:
            return
        if anchor_scene_y is None:
            anchor_scene_y = self.mapToScene(self.viewport().rect().center()).y()
        if anchor_viewport_y is None:
            anchor_viewport_y = self.viewport().height() / 2.0
        ratio = anchor_scene_y / old_height
        self._row_height = new_height
        self._build_background(self._current_total_seconds)
        for note in self._notes:
            self._update_item_geometry(note)
        self._update_range_item_geometry()
        self._draw_playhead(focus=False)
        self.zoomChanged.emit()
        new_scene_y = ratio * new_height
        self.verticalScrollBar().setValue(
            int(round(new_scene_y - anchor_viewport_y))
        )

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

    def set_playhead_locked(self, locked: bool) -> None:
        """锁定/解锁标尺定位（播放期间锁定；演奏模式不锁定）。"""
        self._playhead_locked = bool(locked)
        if self._playhead_locked:
            self.focus_vertical_range_center()

    def focus_vertical_range_center(self) -> None:
        """把黄色音域框的纵向中心滚到视口中心（播放开始时调用一次）。"""
        if not self._range_visible:
            return
        y_top, y_bottom = self._range_band_y_bounds()
        center = (y_top + y_bottom) / 2.0
        bar = self.verticalScrollBar()
        target = int(round(center - self.viewport().height() / 2.0))
        bar.setValue(max(bar.minimum(), min(bar.maximum(), target)))

    def is_playhead_locked(self) -> bool:
        return self._playhead_locked

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
        if self._read_only and self._playhead_locked:
            self.follow_playhead()

    def follow_playhead(self) -> None:
        """播放期翻页跟随：辅助线超过视口 80% 时滚到视口左侧 20%。"""
        width = float(self.viewport().width())
        if width <= 0:
            return
        x = self.viewport_x_for_time(self._playhead_display_seconds)
        if x <= width * 0.8:
            return
        scene_x = self._time_to_x(self._playhead_display_seconds)
        bar = self.horizontalScrollBar()
        target = int(round(scene_x - width * 0.2))
        bar.setValue(max(bar.minimum(), min(bar.maximum(), target)))


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


    # ------------------------------------------------------------------
    # 背景（琴键行 + 秒线 + 小节线）
    # ------------------------------------------------------------------


    # ------------------------------------------------------------------
    # 乐器音域框
    # ------------------------------------------------------------------




    # ------------------------------------------------------------------
    # 音符图元
    # ------------------------------------------------------------------



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
    def clipboard_notes(self) -> List[Dict]:
        """返回内部剪贴板的副本（用于撤销快照）。"""
        return [dict(n) for n in self._clipboard]

    def restore_clipboard(self, notes: List[Dict]) -> None:
        """恢复内部剪贴板（撤销/前进时使用）。"""
        self._clipboard = [dict(n) for n in notes]

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

    def _nudge_selected(self, step: float) -> None:
        """按 step 秒平移选中音符；起点不允许小于 0。"""
        selected = [n for n in self._notes if n["id"] in self._selected_ids]
        if not selected:
            return
        delta = step
        if delta < 0:
            delta = max(delta, -min(n["start"] for n in selected))
        if abs(delta) < 1e-9:
            return
        for note in selected:
            note["start"] = round(max(0.0, note["start"] + delta), 3)
            self._update_item_geometry(note)
        self.notesChanged.emit()

    def _transpose_selected(self, semitones: int) -> None:
        """把选中音符整体移调 semitones 个半音；任一音符会越界时整组不动。"""
        if not self._selected_ids:
            return
        selected = [n for n in self._notes if n["id"] in self._selected_ids]
        if not selected:
            return
        if any(
            not (MIN_PITCH <= n["pitch"] + semitones <= MAX_PITCH) for n in selected
        ):
            return
        for note in selected:
            note["pitch"] = int(note["pitch"]) + semitones
            note["mapped"] = note["pitch"] in self._mapped_pitches
            self._update_item_geometry(note)
        self.notesChanged.emit()

    def arpeggiate_selected(self, seconds_per_beat: float) -> int:
        """对选中音符执行 1/32 拍琶音展开；返回实际发生变化的音符数。"""
        if self._read_only:
            return 0
        selected = set(self._selected_ids)
        if not selected:
            return 0
        before = {n["id"]: (n["start"], n["duration"]) for n in self._notes if n["id"] in selected}
        self._notes = arpeggiate_notes(self._notes, selected, seconds_per_beat)
        remaining = {n["id"] for n in self._notes}
        removed = set(before) - remaining
        for note_id in removed:
            item = self._note_items.pop(note_id, None)
            if item is not None:
                self._scene.removeItem(item)
            self._selected_ids.discard(note_id)
        changed = len(removed)
        for note in self._notes:
            if note.get("id") in before and before[note["id"]] != (
                note["start"],
                note["duration"],
            ):
                changed += 1
            self._update_item_geometry(note)
        if changed == 0:
            return 0
        total = max(
            (n["start"] + n["duration"] for n in self._notes), default=MIN_SCENE_SECONDS
        )
        self._ensure_scene_width(total)
        self.notesChanged.emit()
        return changed

    # ------------------------------------------------------------------
    # 鼠标 / 键盘交互
    # ------------------------------------------------------------------





