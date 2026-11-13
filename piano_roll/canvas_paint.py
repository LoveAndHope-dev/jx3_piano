"""画布绘制处理器。"""

from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
)

from .geometry import *  # noqa: F401,F403
from .geometry import _is_black_key


class CanvasPaintMixin:
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

    def set_measure_grid(self, seconds_per_measure: Optional[float]) -> None:
        """设置背景小节线的间距（秒）；传 None 或过小的值表示不画小节线"""
        if seconds_per_measure and seconds_per_measure >= MIN_MEASURE_SECONDS:
            self._measure_seconds = seconds_per_measure
        else:
            self._measure_seconds = None
        self._build_background(self._current_total_seconds)
        self._update_range_item_geometry()
