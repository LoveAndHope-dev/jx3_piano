import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from piano_roll import PianoRollWidget

_app = None


def _application():
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


class PianoRollWidgetTest(unittest.TestCase):
    def setUp(self):
        _application()
        self.widget = PianoRollWidget(set(range(21, 109)))
        self.widget.resize(900, 420)
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

    def test_zoom_keeps_anchor_time_under_cursor(self):
        self.canvas.set_pixels_per_second(70.0)
        self.canvas.horizontalScrollBar().setValue(0)
        anchor_time = self.canvas.time_at_viewport_x(140.0)
        new_pps = 140.0
        value = int(round(anchor_time * new_pps - 140.0))
        self.canvas.horizontalScrollBar().setValue(value)
        self.canvas.set_pixels_per_second(new_pps)
        self.assertAlmostEqual(self.canvas.time_at_viewport_x(140.0), anchor_time, places=3)

    def test_zoom_is_clamped(self):
        self.canvas.set_pixels_per_second(1.0)
        self.assertEqual(self.canvas.pixels_per_second(), 10.0)
        self.canvas.set_pixels_per_second(99999.0)
        self.assertEqual(self.canvas.pixels_per_second(), 600.0)

    def test_ruler_click_sets_playhead_anchor(self):
        self.canvas.set_pixels_per_second(70.0)
        self.canvas.horizontalScrollBar().setValue(0)
        QTest.mouseClick(self.widget._ruler, Qt.LeftButton, pos=QPoint(70, 10))
        self.assertAlmostEqual(self.widget.get_playhead_position(), 1.0, places=3)

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


if __name__ == "__main__":
    unittest.main()
