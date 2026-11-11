import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QPoint, QPointF, Qt
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from piano_roll import PianoRollWidget

_app = None


def _application():
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


def _wheel(canvas, x: float, delta: int = 120, shift: bool = True):
    modifiers = Qt.ShiftModifier if shift else Qt.NoModifier
    return QWheelEvent(
        QPointF(x, 5.0),
        QPointF(x, 5.0),
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
        self.widget.set_read_only(True)
        QTest.mouseClick(self.widget._ruler, Qt.LeftButton, pos=QPoint(350, 10))
        self.assertAlmostEqual(self.widget.get_playhead_position(), 2.0, places=3)
        self.widget.set_read_only(False)

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


if __name__ == "__main__":
    unittest.main()
