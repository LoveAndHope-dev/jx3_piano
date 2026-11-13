import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt5.QtGui import QMouseEvent, QWheelEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from piano_roll import PianoRollWidget

_app = None


def _application():
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


def _wheel(canvas, x: float, delta: int = 120, ctrl: bool = True, shift: bool = False, y: float = 5.0):
    modifiers = Qt.NoModifier
    if ctrl:
        modifiers |= Qt.ControlModifier
    if shift:
        modifiers |= Qt.ShiftModifier
    return QWheelEvent(
        QPointF(x, y),
        QPointF(x, y),
        QPoint(0, 0),
        QPoint(0, delta),
        Qt.NoButton,
        modifiers,
        Qt.NoScrollPhase,
        False,
    )


class PianoRollWidgetTest(unittest.TestCase):
    def setUp(self):
        app = _application()
        self.widget = PianoRollWidget(set(range(21, 109)))
        self.widget.resize(900, 420)
        self.widget.show()
        app.processEvents()
        self.widget.set_notes(
            [
                {"id": 0, "pitch": 60, "start": 1.0, "duration": 0.5, "track": 0, "mapped": True},
                {"id": 1, "pitch": 64, "start": 3.0, "duration": 0.5, "track": 0, "mapped": True},
            ]
        )
        self.widget.set_beat_grid(0.5, 4)
        self.canvas = self.widget._canvas

    def tearDown(self):
        self.widget.deleteLater()

    def test_playhead_defaults_to_zero(self):
        self.assertEqual(self.widget.get_playhead_position(), 0.0)

    def test_paste_lands_on_playhead_anchor(self):
        self.widget.set_playhead_anchor(10.0)
        self.canvas._set_selection({0, 1})
        self.canvas._copy_selected()
        self.canvas._paste_clipboard()
        starts = sorted(n["start"] for n in self.widget.get_notes())
        self.assertEqual(starts, [1.0, 3.0, 10.0, 12.0])
        self.assertEqual(self.canvas._selected_ids, {2, 3})

    def test_paste_with_empty_clipboard_is_noop(self):
        self.canvas._paste_clipboard()
        self.assertEqual(len(self.widget.get_notes()), 2)

    def test_cut_removes_notes_and_keeps_clipboard(self):
        self.canvas._set_selection({0})
        self.canvas._copy_selected()
        self.canvas._delete_selected()
        self.assertEqual(len(self.widget.get_notes()), 1)
        self.widget.set_playhead_anchor(6.0)
        self.canvas._paste_clipboard()
        self.assertEqual(sorted(n["start"] for n in self.widget.get_notes()), [3.0, 6.0])

    def test_octave_shift_moves_selection(self):
        self.canvas._set_selection({0})
        self.canvas._shift_selected_octave(12)
        self.assertEqual([n["pitch"] for n in self.widget.get_notes() if n["id"] == 0], [72])
        self.canvas._shift_selected_octave(-12)
        self.assertEqual([n["pitch"] for n in self.widget.get_notes() if n["id"] == 0], [60])

    def test_octave_shift_skips_notes_out_of_range(self):
        self.widget.set_notes([{"id": 0, "pitch": 100, "start": 1.0, "duration": 0.5}])
        self.canvas._set_selection({0})
        self.canvas._shift_selected_octave(12)
        self.assertEqual([n["pitch"] for n in self.widget.get_notes()], [100])

    def test_zoom_is_clamped(self):
        self.canvas.set_pixels_per_second(1.0)
        self.assertEqual(self.canvas.pixels_per_second(), 10.0)
        self.canvas.set_pixels_per_second(99999.0)
        self.assertEqual(self.canvas.pixels_per_second(), 600.0)

    def test_ruler_click_sets_playhead_anchor(self):
        self.canvas.set_pixels_per_second(70.0)
        self.canvas.horizontalScrollBar().setValue(0)
        ruler = self.widget._ruler
        QTest.mouseClick(ruler, Qt.LeftButton, pos=QPoint(int(round(ruler._tick_x(1.0))), 10))
        self.assertAlmostEqual(self.widget.get_playhead_position(), 1.0, places=2)

    def test_ruler_ignored_while_playing(self):
        self.widget.set_playhead_anchor(2.0)
        self.canvas.set_pixels_per_second(70.0)
        self.canvas.horizontalScrollBar().setValue(0)
        self.canvas.set_playhead_locked(True)
        QTest.mouseClick(self.widget._ruler, Qt.LeftButton, pos=QPoint(350, 10))
        self.assertAlmostEqual(self.widget.get_playhead_position(), 2.0, places=3)
        self.canvas.set_playhead_locked(False)

    def test_stopping_playback_falls_back_to_anchor(self):
        self.widget.set_playhead_anchor(4.0)
        self.widget.set_playhead(9.0)
        self.assertEqual(self.canvas._playhead_display_seconds, 9.0)
        self.widget.set_playhead(None)
        self.assertEqual(self.canvas._playhead_display_seconds, 4.0)

    def test_switching_notes_resets_playhead_anchor(self):
        self.widget.set_playhead_anchor(7.0)
        self.widget.set_notes([{"id": 0, "pitch": 60, "start": 0.0, "duration": 0.5}])
        self.assertEqual(self.widget.get_playhead_position(), 0.0)
        self.assertEqual(self.canvas._playhead_display_seconds, 0.0)

    def test_viewport_mapping_matches_scene_when_zoomed_out(self):
        self.widget.set_notes([{"id": 0, "pitch": 60, "start": 4.0, "duration": 0.5}])
        self.canvas.set_pixels_per_second(10.0)
        _application().processEvents()
        expected = self.canvas.mapFromScene(QPointF(0.0, 0.0)).x()
        self.assertAlmostEqual(self.canvas.viewport_x_for_time(0.0), expected, delta=0.5)
        self.assertAlmostEqual(
            self.canvas.time_at_viewport_x(float(expected)), 0.0, delta=1e-6
        )

    def test_wheel_zoom_keeps_anchor_at_end_of_timeline(self):
        self.widget.set_notes(
            [{"id": 0, "pitch": 60, "start": 50.0, "duration": 1.0, "track": 0, "mapped": True}]
        )
        self.canvas.set_pixels_per_second(70.0)
        bar = self.canvas.horizontalScrollBar()
        bar.setValue(bar.maximum())
        x = float(self.canvas.viewport().width()) - 25.0
        before = self.canvas.time_at_viewport_x(x)
        self.canvas.wheelEvent(_wheel(self.canvas, x))
        after = self.canvas.time_at_viewport_x(x)
        self.assertAlmostEqual(before, after, delta=0.05)

    def test_wheel_zoom_keeps_anchor_in_middle(self):
        self.widget.set_notes(
            [{"id": 0, "pitch": 60, "start": 50.0, "duration": 1.0, "track": 0, "mapped": True}]
        )
        self.canvas.set_pixels_per_second(70.0)
        bar = self.canvas.horizontalScrollBar()
        bar.setValue(bar.maximum() // 2)
        x = float(self.canvas.viewport().width()) / 2.0
        before = self.canvas.time_at_viewport_x(x)
        self.canvas.wheelEvent(_wheel(self.canvas, x))
        after = self.canvas.time_at_viewport_x(x)
        self.assertAlmostEqual(before, after, delta=0.05)

    def test_horizontal_wheel_with_shift_does_not_zoom_out(self):
        self.canvas.set_pixels_per_second(70.0)
        before = self.canvas.pixels_per_second()
        self.canvas.wheelEvent(_wheel(self.canvas, 100.0, delta=0))
        self.assertEqual(self.canvas.pixels_per_second(), before)

    def test_ruler_tick_stays_aligned_when_scene_is_narrow(self):
        self.widget.set_notes([{"id": 0, "pitch": 60, "start": 2.0, "duration": 0.5}])
        self.widget.set_beat_grid(0.5, 4)
        self.canvas.set_pixels_per_second(10.0)
        _application().processEvents()
        ruler = self.widget._ruler
        scaled = ruler.grab().toImage()
        self.assertFalse(scaled.isNull())
        expected = self.canvas.viewport_x_for_time(0.0) + ruler._viewport_origin()
        self.assertAlmostEqual(ruler._tick_x(0.0), expected, delta=0.5)

    def test_keyboard_copy_and_paste_emit_notes_changed(self):
        signals = []
        self.widget.notesChanged.connect(lambda: signals.append(1))
        self.canvas.setFocus()
        self.canvas._set_selection({0})
        QTest.keyClick(self.canvas, Qt.Key_C, Qt.ControlModifier)
        self.assertEqual(signals, [])
        QTest.keyClick(self.canvas, Qt.Key_V, Qt.ControlModifier)
        self.assertEqual(len(signals), 1)
        self.assertEqual(len(self.widget.get_notes()), 3)

    def test_keyboard_cut_removes_selection(self):
        self.canvas._set_selection({0, 1})
        QTest.keyClick(self.canvas, Qt.Key_X, Qt.ControlModifier)
        self.assertEqual(self.widget.get_notes(), [])
        self.assertEqual(len(self.canvas._clipboard), 2)

    def test_keyboard_shift_up_moves_octave(self):
        signals = []
        self.widget.notesChanged.connect(lambda: signals.append(1))
        self.canvas._set_selection({0})
        QTest.keyClick(self.canvas, Qt.Key_Up, Qt.ShiftModifier)
        self.assertEqual([n["pitch"] for n in self.widget.get_notes() if n["id"] == 0], [72])
        self.assertEqual(len(signals), 1)

    def test_read_only_canvas_ignores_paste_and_octave(self):
        self.canvas._set_selection({0})
        QTest.keyClick(self.canvas, Qt.Key_C, Qt.ControlModifier)
        self.widget.set_read_only(True)
        QTest.keyClick(self.canvas, Qt.Key_V, Qt.ControlModifier)
        QTest.keyClick(self.canvas, Qt.Key_Up, Qt.ShiftModifier)
        self.assertEqual(len(self.widget.get_notes()), 2)
        self.assertEqual([n["pitch"] for n in self.widget.get_notes() if n["id"] == 0], [60])
        self.widget.set_read_only(False)

    def test_octave_shift_with_empty_selection_does_nothing(self):
        before = self.widget.get_notes()
        self.canvas._set_selection(set())
        self.canvas._shift_selected_octave(12)
        self.assertEqual(self.widget.get_notes(), before)

    def test_rescale_times_scales_notes_and_playhead(self):
        self.widget.set_playhead_anchor(2.0)
        self.widget.rescale_times(2.0)
        starts = sorted(n["start"] for n in self.widget.get_notes())
        self.assertEqual(starts, [2.0, 6.0])
        durations = sorted(n["duration"] for n in self.widget.get_notes())
        self.assertEqual(durations, [1.0, 1.0])
        self.assertEqual(self.widget.get_playhead_position(), 4.0)
        self.assertEqual(self.canvas._playhead_display_seconds, 4.0)

    def test_rescale_times_emits_notes_changed(self):
        signals = []
        self.widget.notesChanged.connect(lambda: signals.append(1))
        self.widget.rescale_times(0.5)
        self.assertEqual(len(signals), 1)

    def test_rescale_times_round_trip(self):
        before = sorted((n["start"], n["duration"]) for n in self.widget.get_notes())
        self.widget.rescale_times(0.75)
        self.widget.rescale_times(1.0 / 0.75)
        after = sorted((n["start"], n["duration"]) for n in self.widget.get_notes())
        for (s0, d0), (s1, d1) in zip(before, after):
            self.assertAlmostEqual(s0, s1, delta=1e-6)
            self.assertAlmostEqual(d0, d1, delta=1e-6)

    def test_measure_lines_follow_new_tempo(self):
        from PyQt5.QtWidgets import QGraphicsLineItem

        self.canvas.set_pixels_per_second(70.0)
        self.widget.set_measure_grid(4.0)
        self.widget.set_beat_grid(1.0, 4)
        xs = [
            round(item.line().x1(), 3)
            for item in self.canvas._background_items
            if isinstance(item, QGraphicsLineItem)
        ]
        for expected in (0.0, 280.0, 560.0):
            self.assertIn(expected, xs)
        ruler = self.widget._ruler
        self.assertAlmostEqual(
            ruler._tick_x(4.0) - ruler._tick_x(0.0), 280.0, delta=0.5
        )

    def test_clipboard_is_rescaled_with_tempo(self):
        self.canvas._set_selection({0})
        self.canvas._copy_selected()
        self.widget.rescale_times(2.0)
        self.widget.set_playhead_anchor(10.0)
        self.canvas._paste_clipboard()
        pasted = self.widget.get_notes()[-1]
        self.assertEqual(pasted["duration"], 1.0)

    def _click_at(self, seconds: float, pitch: int, double: bool = False):
        pos = self.canvas.mapFromScene(
            QPointF(self.canvas._time_to_x(seconds), self.canvas._pitch_to_y(pitch) + 5)
        )
        if double:
            QTest.mouseDClick(self.canvas.viewport(), Qt.LeftButton, pos=pos)
        else:
            QTest.mouseClick(self.canvas.viewport(), Qt.LeftButton, pos=pos)

    def test_click_empty_clears_selection_without_creating(self):
        self.canvas._set_selection({0})
        self._click_at(6.0, 70)
        self.assertEqual(self.canvas._selected_ids, set())
        self.assertEqual(len(self.widget.get_notes()), 2)

    def test_double_click_empty_creates_note(self):
        self._click_at(6.0, 70, double=True)
        notes = self.widget.get_notes()
        self.assertEqual(len(notes), 3)
        created = [n for n in notes if abs(n["start"] - 6.0) < 0.01 and n["pitch"] == 70]
        self.assertEqual(len(created), 1)
        self.assertEqual(self.canvas._selected_ids, {created[0]["id"]})

    def _drag_empty(self, start_pos, end_pos):
        QTest.mousePress(self.canvas.viewport(), Qt.LeftButton, pos=start_pos)
        move = QMouseEvent(
            QEvent.MouseMove, QPointF(end_pos), Qt.NoButton, Qt.LeftButton, Qt.NoModifier
        )
        QApplication.sendEvent(self.canvas.viewport(), move)
        QTest.mouseRelease(self.canvas.viewport(), Qt.LeftButton, pos=end_pos)

    def test_drag_empty_marquee_selects_without_creating(self):
        start = self.canvas.mapFromScene(QPointF(20.0, self.canvas._pitch_to_y(66) + 5))
        end = self.canvas.mapFromScene(QPointF(140.0, self.canvas._pitch_to_y(54) + 5))
        self._drag_empty(start, end)
        self.assertEqual(len(self.widget.get_notes()), 2)
        self.assertIn(0, self.canvas._selected_ids)

    def test_drag_left_edge_trims_start_and_keeps_end(self):
        note = [n for n in self.widget.get_notes() if n["id"] == 0][0]
        end = note["start"] + note["duration"]
        self.canvas.verticalScrollBar().setValue(int(self.canvas._pitch_to_y(note["pitch"])) - 60)
        start_pos = self.canvas.mapFromScene(
            QPointF(self.canvas._time_to_x(note["start"]) + 2.0, self.canvas._pitch_to_y(note["pitch"]) + 5)
        )
        end_pos = self.canvas.mapFromScene(
            QPointF(self.canvas._time_to_x(note["start"]) + 14.0, self.canvas._pitch_to_y(note["pitch"]) + 5)
        )
        self._drag_empty(start_pos, end_pos)
        edited = [n for n in self.widget.get_notes() if n["id"] == 0][0]
        self.assertGreater(edited["start"], note["start"])
        self.assertAlmostEqual(edited["start"] + edited["duration"], end, delta=0.01)

    def test_arrow_keys_nudge_and_transpose(self):
        self.canvas.set_quantize_grid(0.25)
        self.canvas._set_selection({0})
        QTest.keyClick(self.canvas, Qt.Key_Right)
        note = [n for n in self.widget.get_notes() if n["id"] == 0][0]
        self.assertAlmostEqual(note["start"], 1.25, delta=1e-6)
        QTest.keyClick(self.canvas, Qt.Key_Up)
        note = [n for n in self.widget.get_notes() if n["id"] == 0][0]
        self.assertEqual(note["pitch"], 61)
        QTest.keyClick(self.canvas, Qt.Key_Down, Qt.ShiftModifier)
        note = [n for n in self.widget.get_notes() if n["id"] == 0][0]
        self.assertEqual(note["pitch"], 49)

    def test_ctrl_z_emits_undo_and_redo_requests(self):
        undo_calls = []
        redo_calls = []
        self.widget.undoRequested.connect(lambda: undo_calls.append(1))
        self.widget.redoRequested.connect(lambda: redo_calls.append(1))
        self.canvas.setFocus()
        QTest.keyClick(self.canvas, Qt.Key_Z, Qt.ControlModifier)
        QTest.keyClick(self.canvas, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
        self.assertEqual(len(undo_calls), 1)
        self.assertEqual(len(redo_calls), 1)
        self.canvas.set_read_only(True)
        QTest.keyClick(self.canvas, Qt.Key_Z, Qt.ControlModifier)
        self.assertEqual(len(undo_calls), 1)
        self.canvas.set_read_only(False)

    def test_read_only_blocks_editing_but_ruler_still_seeks(self):
        self.canvas._set_selection({0})
        self.canvas._copy_selected()
        before = self.widget.get_notes()
        self.canvas.set_read_only(True)
        self.canvas.set_playhead_locked(False)
        self._click_at(6.0, 70, double=True)
        QTest.keyClick(self.canvas, Qt.Key_Right)
        QTest.keyClick(self.canvas, Qt.Key_Delete)
        QTest.keyClick(self.canvas, Qt.Key_V, Qt.ControlModifier)
        self.assertEqual(self.widget.get_notes(), before)
        self.assertEqual(self.canvas._selected_ids, {0})
        ruler = self.widget._ruler
        QTest.mouseClick(ruler, Qt.LeftButton, pos=QPoint(int(round(ruler._tick_x(2.0))), 10))
        self.assertAlmostEqual(self.widget.get_playhead_position(), 2.0, places=2)
        self.canvas.set_read_only(False)

    def test_shift_wheel_does_not_zoom(self):
        self.canvas.set_pixels_per_second(70.0)
        self.canvas.wheelEvent(_wheel(self.canvas, 100.0, ctrl=False, shift=True))
        self.assertEqual(self.canvas.pixels_per_second(), 70.0)

    def test_left_edge_drag_past_end_keeps_min_duration(self):
        note = [n for n in self.widget.get_notes() if n["id"] == 0][0]
        self.canvas.verticalScrollBar().setValue(int(self.canvas._pitch_to_y(note["pitch"])) - 60)
        start_pos = self.canvas.mapFromScene(
            QPointF(self.canvas._time_to_x(note["start"]) + 2.0, self.canvas._pitch_to_y(note["pitch"]) + 5)
        )
        end_pos = self.canvas.mapFromScene(
            QPointF(self.canvas._time_to_x(note["start"] + note["duration"]) + 80.0,
                    self.canvas._pitch_to_y(note["pitch"]) + 5)
        )
        self._drag_empty(start_pos, end_pos)
        edited = [n for n in self.widget.get_notes() if n["id"] == 0][0]
        self.assertAlmostEqual(edited["duration"], 0.05, delta=1e-6)
        self.assertAlmostEqual(
            edited["start"], note["start"] + note["duration"] - 0.05, delta=1e-6
        )

    def test_nudge_without_selection_does_nothing(self):
        signals = []
        self.widget.notesChanged.connect(lambda: signals.append(1))
        self.canvas._set_selection(set())
        QTest.keyClick(self.canvas, Qt.Key_Right)
        self.assertEqual(signals, [])
        self.assertEqual(len(self.widget.get_notes()), 2)

    def test_nudge_keeps_group_spacing(self):
        self.canvas.set_quantize_grid(0.25)
        self.canvas._set_selection({0, 1})
        QTest.keyClick(self.canvas, Qt.Key_Right)
        notes = {n["id"]: n["start"] for n in self.widget.get_notes()}
        self.assertAlmostEqual(notes[0], 1.25, delta=1e-6)
        self.assertAlmostEqual(notes[1], 3.25, delta=1e-6)

    def test_transpose_skips_whole_group_at_boundary(self):
        self.widget.set_notes([
            {"id": 0, "pitch": 107, "start": 1.0, "duration": 0.5, "mapped": True},
            {"id": 1, "pitch": 108, "start": 1.0, "duration": 0.5, "mapped": True},
        ])
        self.canvas._set_selection({0, 1})
        self.canvas._transpose_selected(1)
        self.assertEqual([n["pitch"] for n in self.widget.get_notes()], [107, 108])

    def test_playhead_lock_ignores_ruler(self):
        self.widget.set_playhead_anchor(1.0)
        self.canvas.set_playhead_locked(True)
        ruler = self.widget._ruler
        QTest.mouseClick(ruler, Qt.LeftButton, pos=QPoint(int(round(ruler._tick_x(2.0))), 10))
        self.assertAlmostEqual(self.widget.get_playhead_position(), 1.0, places=2)
        self.canvas.set_playhead_locked(False)

    def test_follow_scrolls_page_when_playhead_passes_threshold(self):
        self.widget.set_notes([
            {"id": 0, "pitch": 60, "start": 20.0, "duration": 0.5, "track": 0}
        ])
        self.canvas.set_pixels_per_second(70.0)
        self.canvas.horizontalScrollBar().setValue(0)
        self.canvas.set_read_only(True)
        self.canvas.set_playhead_locked(True)
        self.canvas.set_playhead(15.0)
        bar = self.canvas.horizontalScrollBar()
        self.assertGreater(bar.value(), 0)
        expected = round(15.0 * 70.0 - self.canvas.viewport().width() * 0.2)
        self.assertAlmostEqual(bar.value(), expected, delta=2)
        self.canvas.set_playhead_locked(False)
        self.canvas.set_read_only(False)

    def test_follow_clamps_at_scroll_maximum(self):
        self.widget.set_notes([
            {"id": 0, "pitch": 60, "start": 30.0, "duration": 0.5, "track": 0}
        ])
        self.canvas.set_pixels_per_second(70.0)
        self.canvas.horizontalScrollBar().setValue(0)
        self.canvas.set_read_only(True)
        self.canvas.set_playhead_locked(True)
        self.canvas.set_playhead(29.0)
        bar = self.canvas.horizontalScrollBar()
        self.assertGreater(bar.value(), 0)
        self.assertEqual(bar.value(), bar.maximum())
        self.canvas.set_playhead_locked(False)
        self.canvas.set_read_only(False)

    def test_follow_keeps_scroll_inside_threshold(self):
        self.widget.set_notes([
            {"id": 0, "pitch": 60, "start": 20.0, "duration": 0.5, "track": 0}
        ])
        self.canvas.set_pixels_per_second(70.0)
        self.canvas.horizontalScrollBar().setValue(0)
        self.canvas.set_read_only(True)
        self.canvas.set_playhead_locked(True)
        self.canvas.set_playhead(2.0)
        self.assertEqual(self.canvas.horizontalScrollBar().value(), 0)
        self.canvas.set_playhead_locked(False)
        self.canvas.set_read_only(False)

    def test_no_follow_in_play_mode_without_playing(self):
        self.widget.set_notes([
            {"id": 0, "pitch": 60, "start": 20.0, "duration": 0.5, "track": 0}
        ])
        self.canvas.set_pixels_per_second(70.0)
        self.canvas.horizontalScrollBar().setValue(0)
        self.canvas.set_read_only(True)
        self.canvas.set_playhead_locked(False)
        calls = []
        original = self.canvas.follow_playhead
        self.canvas.follow_playhead = lambda: calls.append(1)
        try:
            self.canvas.set_playhead(15.0)
        finally:
            self.canvas.follow_playhead = original
        self.assertEqual(calls, [])
        self.canvas.set_read_only(False)

    def test_no_follow_when_not_playing(self):
        self.widget.set_notes([
            {"id": 0, "pitch": 60, "start": 20.0, "duration": 0.5, "track": 0}
        ])
        self.canvas.set_pixels_per_second(70.0)
        self.canvas.horizontalScrollBar().setValue(0)
        self.canvas.set_read_only(False)
        calls = []
        original = self.canvas.follow_playhead
        self.canvas.follow_playhead = lambda: calls.append(1)
        try:
            self.canvas.set_playhead(15.0)
        finally:
            self.canvas.follow_playhead = original
        self.assertEqual(calls, [])


    def test_row_height_zoom_clamps(self):
        self.canvas.set_row_height(999)
        self.assertAlmostEqual(self.canvas.row_height, 24)
        self.canvas.set_row_height(1)
        self.assertAlmostEqual(self.canvas.row_height, 6)
        self.canvas.set_row_height(10)

    def test_shift_wheel_zooms_rows_with_pitch_anchor(self):
        self.canvas.set_row_height(10)
        self.canvas.verticalScrollBar().setValue(160)
        x, y = 220.0, 120.0
        old_height = self.canvas.row_height
        scene_before = self.canvas.mapToScene(QPoint(int(x), int(y)))
        row_before = int(scene_before.y() // old_height)
        emitted = []
        self.canvas.notesChanged.connect(lambda: emitted.append(1))

        self.canvas.wheelEvent(_wheel(self.canvas, x, y=y, ctrl=False, shift=True))

        new_height = self.canvas.row_height
        self.assertGreater(new_height, old_height)
        scene_after = self.canvas.mapToScene(QPoint(int(x), int(y)))
        row_after = int(scene_after.y() // new_height)
        self.assertLessEqual(abs(row_after - row_before), 1)
        self.assertEqual(emitted, [])

    def test_playhead_lock_centers_instrument_range(self):
        self.widget.set_instrument_range(48, 72)
        self.canvas.set_instrument_range_visible(True)
        self.canvas.verticalScrollBar().setValue(0)
        self.canvas.set_playhead_locked(True)

        y_top, y_bottom = self.canvas._range_band_y_bounds()
        expected = (y_top + y_bottom) / 2.0 - self.canvas.viewport().height() / 2.0
        self.assertAlmostEqual(self.canvas.verticalScrollBar().value(), expected, delta=2)
        self.canvas.set_playhead_locked(False)

    def test_keyboard_stays_pinned_when_scrolling_horizontally(self):
        keyboard = self.widget._keyboard
        before = keyboard.geometry()
        self.canvas.horizontalScrollBar().setValue(120)
        _application().processEvents()
        self.assertEqual(keyboard.geometry(), before)
        self.assertEqual(keyboard.x(), 0)


if __name__ == "__main__":
    unittest.main()
