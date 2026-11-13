"""画布鼠标与键盘交互处理器。"""

from typing import Dict, List, Optional, Set, Tuple

from PyQt5.QtCore import QPoint, QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen
from PyQt5.QtWidgets import QAction, QGraphicsRectItem, QMenu

from .geometry import *  # noqa: F401,F403


class CanvasInputMixin:
    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        if self._read_only:
            # 演奏模式：只允许拖动可见的音域框，音符编辑一律拒绝
            if (
                event.button() == Qt.LeftButton
                and self._range_visible
                and self._is_within_range_band(scene_pos.y())
            ):
                self._select_note(None)
                self._drag_mode = "range"
                self._drag_start_scene = scene_pos
                low_idx = self._nearest_ladder_index_for_pitch(self._range_low_pitch)
                high_idx = self._nearest_ladder_index_for_pitch(self._range_high_pitch)
                self._drag_range_start_low_idx = low_idx
                self._drag_range_span_idx = high_idx - low_idx
                event.accept()
            return

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
            near_left_edge = (
                not near_right_edge and (scene_pos.x() - rect.left()) <= RESIZE_MARGIN
            )

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
            elif near_left_edge:
                # 左边缘调整起始时间，结束时间保持不变
                self._set_selection({note_id})
                self._drag_mode = "resize-start"
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
            # 空白处只记录起点：单击（未拖动）取消选择，拖动则框选，均不新建音符
            self._pending_create_note = None
            self._drag_mode = "select-rect-or-create"
            self._drag_start_scene = scene_pos
            self._select_rect_item = None

        event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_mode == "range":
            scene_pos = self.mapToScene(event.pos())
            dy = scene_pos.y() - self._drag_start_scene.y()
            # 目标音高必须按渲染网格的像素/半音比例（self._row_height 像素 = 1 个半音）换算，
            # 与框体的实际渲染位置（_pitch_to_y）保持 1:1，再吸附到距离最近的键位序列
            # 位置。这里刻意保留连续（未取整的）目标音高，不对 dy/self._row_height 提前取整：
            # 提前取整会和随后按最近音高吸附时的平局裁决叠加，使 B、E 两个键的可命中像
            # 素窗口显著窄于其余键位（实测约 10px vs 20px），正常速度拖动时更容易被跳
            # 过；改为连续目标音高后，每个自然键的命中窗口只由其左右真实半音间隔决定
            # （多数键 20px，B-C/E-F 相关的 4 个键各 15px），不再因为浮点/整数取整顺序
            # 产生额外的不对称收窄。
            drag_start_low_pitch = self._ladder[self._drag_range_start_low_idx][0]
            target_low_pitch = drag_start_low_pitch - dy / self._row_height
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

        if self._drag_mode in ("move", "resize", "resize-start") and not self._read_only and self._drag_note_start is not None:
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

                row_delta = round(dy / self._row_height)
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
            elif self._drag_mode == "resize-start":
                dx = scene_pos.x() - self._drag_start_scene.x()
                if dx:
                    self._drag_moved = True
                end = self._drag_note_start["start"] + self._drag_note_start["duration"]
                raw_start = self._drag_note_start["start"] + dx / self._pixels_per_second
                snapped_start = self._snap_time(raw_start)
                max_start = end - MIN_NOTE_DURATION
                new_start = min(max(0.0, snapped_start), max_start)
                anchor_note["start"] = round(new_start, 3)
                anchor_note["duration"] = round(end - new_start, 3)
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
            else:
                # 单击空白：取消当前选择，且不新建音符
                self._set_selection(set())
            self._pending_create_note = None
            self._drag_mode = None
            return

        if self._drag_mode in ("move", "resize", "resize-start"):
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

    def mouseDoubleClickEvent(self, event):
        """双击空白新建音符（DAW 习惯）；双击已有音符走默认处理。"""
        if self._read_only or event.button() != Qt.LeftButton:
            super().mouseDoubleClickEvent(event)
            return

        scene_pos = self.mapToScene(event.pos())
        if self._hit_test(scene_pos) is not None:
            super().mouseDoubleClickEvent(event)
            return

        pitch = self._y_to_pitch(scene_pos.y())
        start = self._snap_time(max(0.0, self._x_to_time(scene_pos.x())))
        duration = self._quantize_seconds or DEFAULT_NOTE_DURATION
        note = {
            "id": self._next_id,
            "track": self._default_track,
            "channel": 0,
            "pitch": pitch,
            "start": round(start, 3),
            "duration": round(duration, 3),
            "velocity": 100,
            "mapped": pitch in self._mapped_pitches,
        }
        self._next_id += 1
        self._notes.append(note)
        self._add_note_item(note)
        self._select_note(note["id"])
        self._ensure_scene_width(start + duration)
        self.notesChanged.emit()
        event.accept()

    def keyPressEvent(self, event):
        if self._read_only:
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key_A and bool(event.modifiers() & Qt.ControlModifier):
            self._set_selection(set(self._note_items.keys()))
            event.accept()
            return

        if event.key() == Qt.Key_Z and bool(event.modifiers() & Qt.ControlModifier):
            if event.modifiers() & Qt.ShiftModifier:
                self.redoRequested.emit()
            else:
                self.undoRequested.emit()
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

        if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down) and self._selected_ids:
            modifiers = event.modifiers()
            if not (modifiers & (Qt.ControlModifier | Qt.AltModifier)):
                step = self._quantize_seconds or DEFAULT_NUDGE_SECONDS
                if event.key() == Qt.Key_Left:
                    self._nudge_selected(-step)
                elif event.key() == Qt.Key_Right:
                    self._nudge_selected(step)
                elif event.key() == Qt.Key_Up:
                    self._transpose_selected(1)
                else:
                    self._transpose_selected(-1)
                event.accept()
                return

        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self._selected_ids:
            self._delete_selected()
            event.accept()
            return

        super().keyPressEvent(event)

    def wheelEvent(self, event):
        """Shift+滚轮纵向缩放；Ctrl+滚轮横向缩放；否则保持原有纵向滚动。"""
        modifiers = event.modifiers()
        delta_y = event.angleDelta().y()

        if (modifiers & Qt.ShiftModifier) and not (modifiers & Qt.ControlModifier):
            if delta_y == 0:
                super().wheelEvent(event)
                return
            factor = ROW_ZOOM_STEP_FACTOR if delta_y > 0 else 1.0 / ROW_ZOOM_STEP_FACTOR
            viewport_pos = event.pos()
            scene_pos = self.mapToScene(viewport_pos)
            self.set_row_height(
                self._row_height * factor,
                anchor_scene_y=float(scene_pos.y()),
                anchor_viewport_y=float(viewport_pos.y()),
            )
            event.accept()
            return

        if not (modifiers & Qt.ControlModifier):
            super().wheelEvent(event)
            return

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

    def _show_context_menu(self, note_id: int, global_pos) -> None:
        menu = QMenu(self)
        delete_action = QAction("删除音符", self)
        delete_action.triggered.connect(lambda: self._delete_note(note_id))
        menu.addAction(delete_action)
        menu.exec_(global_pos)

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
