import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import gui
from PyQt5.QtWidgets import QApplication, QMessageBox

_app = None


def _application():
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


class PlaylistGuiTest(unittest.TestCase):
    def setUp(self):
        _application()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._original_midi_dir = gui.get_midi_dir_path
        gui.get_midi_dir_path = lambda: self.tmp.name
        self.addCleanup(self._restore_midi_dir)
        self.window = gui.MidiConverterGUI()
        self.addCleanup(self._close_window)

    def _close_window(self):
        # 关闭前清未保存标记，避免 offscreen 下弹出确认框
        self.window.piano_roll_dirty = False
        self.window.close()

    def _restore_midi_dir(self):
        gui.get_midi_dir_path = self._original_midi_dir

    def test_new_blank_midi_loads_empty_roll(self):
        self.window.on_new_play_item()
        self.assertTrue(self.window.current_midi_path)
        self.assertEqual(self.window.play_listbox.count(), 1)
        self.assertEqual(self.window.play_listbox.currentRow(), 0)
        self.assertEqual(self.window.bpm_spin.value(), 120.0)
        self.assertEqual(self.window.piano_roll.get_notes(), [])
        self.assertIs(self.window.piano_stack.currentWidget(), self.window.piano_roll)
        self.assertFalse(self.window.piano_roll_dirty)

    def test_new_clears_active_search(self):
        self.window.play_search.setText("zzz")
        self.window.on_new_play_item()
        self.assertEqual(self.window.play_search.text(), "")
        self.assertEqual(self.window.play_listbox.count(), 1)
        self.assertEqual(self.window.play_listbox.currentRow(), 0)

    def test_delete_current_track_clears_cache(self):
        self.window.on_new_play_item()
        path = self.window.current_midi_path
        with patch.object(gui.QMessageBox, "question", return_value=QMessageBox.Yes):
            self.window.on_delete_play_item()
        self.assertEqual(self.window.play_listbox.count(), 0)
        self.assertIsNone(self.window.current_midi_path)
        self.assertEqual(self.window.piano_roll.get_notes(), [])
        self.assertEqual(self.window.bpm_spin.value(), 120.0)
        self.assertFalse(self.window.piano_roll_dirty)
        self.assertIs(self.window.piano_stack.currentWidget(), self.window.piano_placeholder)
        self.assertFalse(os.path.exists(path))

    def test_cancel_delete_keeps_everything(self):
        self.window.on_new_play_item()
        path = self.window.current_midi_path
        with patch.object(gui.QMessageBox, "question", return_value=QMessageBox.No):
            self.window.on_delete_play_item()
        self.assertEqual(self.window.play_listbox.count(), 1)
        self.assertTrue(self.window.current_midi_path)
        self.assertTrue(os.path.exists(path))

    def test_deleted_track_not_listed_after_refresh(self):
        self.window.on_new_play_item()
        with patch.object(gui.QMessageBox, "question", return_value=QMessageBox.Yes):
            self.window.on_delete_play_item()
        self.window.refresh_play_list()
        self.assertEqual(self.window.play_listbox.count(), 0)

    def test_list_row_shows_name_once(self):
        self.window.on_new_play_item()
        item = self.window.play_listbox.item(0)
        self.assertEqual(item.text(), "")
        row = self.window.play_listbox.itemWidget(item)
        self.assertIsNotNone(row)
        labels = [w.text() for w in row.findChildren(gui.QLabel)]
        self.assertTrue(any("🎵" in text for text in labels))

    def test_search_does_not_break_loaded_track(self):
        self.window.on_new_play_item()
        path = self.window.current_midi_path
        self.window.play_search.setText("no-such-track")
        self.assertEqual(self.window.play_listbox.count(), 0)
        self.assertEqual(self.window.current_midi_path, path)
        self.assertIsNotNone(self.window.piano_roll.get_notes() is not None)

    def test_mode_toggle_locks_roll(self):
        canvas = self.window.piano_roll._canvas
        self.assertFalse(self.window.play_btn.isEnabled())
        self.window.range_toggle_btn.setChecked(True)
        self.window.on_range_toggle_clicked()
        self.assertTrue(canvas.is_read_only())
        self.assertTrue(self.window.play_btn.isEnabled())
        self.assertEqual(self.window.range_toggle_btn.text(), "✏️ 编辑模式")
        self.window.range_toggle_btn.setChecked(False)
        self.window.on_range_toggle_clicked()
        self.assertFalse(canvas.is_read_only())
        self.assertFalse(self.window.play_btn.isEnabled())
        self.assertEqual(self.window.range_toggle_btn.text(), "🎹 演奏模式")

    def test_default_mapping_and_range_box(self):
        self.window.on_new_play_item()
        self.assertEqual(self.window.range_low_combo.currentData(), 36)
        self.assertEqual(self.window.range_high_combo.currentData(), 83)
        self.assertEqual(self.window.piano_roll.get_instrument_range(), (36, 47))

    def test_absolute_key_fields_show_full_piano_range(self):
        self.window.on_new_play_item()
        self.assertEqual(self.window.range_bottom_display.text(), "A0")
        self.assertEqual(self.window.range_top_display.text(), "C8")
        self.window.piano_roll.set_instrument_range(60, 72)
        self.window._refresh_range_display()
        self.assertEqual(self.window.range_bottom_display.text(), "A0")
        self.assertEqual(self.window.range_top_display.text(), "C8")

    def test_row_items_have_room_for_delete_button(self):
        self.window.on_new_play_item()
        item = self.window.play_listbox.item(0)
        self.assertGreaterEqual(item.sizeHint().height(), 40)

    def test_disabling_controls_resyncs_mode(self):
        self.window.on_new_play_item()
        self.window.range_toggle_btn.setChecked(True)
        self.window.on_range_toggle_clicked()
        self.window.current_midi_path = None
        self.window._set_range_controls_enabled(False)
        self.assertFalse(self.window.piano_roll._canvas.is_read_only())
        self.assertFalse(self.window.play_btn.isEnabled())
        self.assertFalse(self.window.arpeggiate_btn.isEnabled())
        self.assertEqual(self.window.range_toggle_btn.text(), "🎹 演奏模式")

    def test_arpeggiate_single_note_does_not_dirty(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 1.0, "duration": 0.5, "track": 0},
        ])
        self.window.piano_roll._canvas._set_selection({0})
        self.window.piano_roll_dirty = False
        self.window.on_arpeggiate_clicked()
        self.assertFalse(self.window.piano_roll_dirty)

    def test_arpeggiate_selected_notes(self):
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 1.0, "duration": 0.5, "track": 0},
            {"id": 1, "pitch": 64, "start": 1.0, "duration": 0.5, "track": 0},
        ])
        self.window.piano_roll._canvas._set_selection({0, 1})
        self.window.on_arpeggiate_clicked()
        starts = sorted(n["start"] for n in self.window.piano_roll.get_notes())
        self.assertGreater(starts[1], starts[0])

    def test_stop_playback_keeps_play_mode_locked(self):
        canvas = self.window.piano_roll._canvas
        self.window.range_toggle_btn.setChecked(True)
        self.window.on_range_toggle_clicked()
        self.window.is_playing = True
        self.window.stop_playing()
        self.assertTrue(canvas.is_read_only())
        self.assertEqual(self.window.range_toggle_btn.text(), "✏️ 编辑模式")

    def test_loading_another_track_resets_to_edit_mode(self):
        canvas = self.window.piano_roll._canvas
        self.window.on_new_play_item()
        self.window.range_toggle_btn.setChecked(True)
        self.window.on_range_toggle_clicked()
        self.assertTrue(canvas.is_read_only())
        self.window.on_new_play_item()
        self.assertFalse(self.window.range_toggle_btn.isChecked())
        self.assertFalse(canvas.is_read_only())
        self.assertEqual(self.window.range_toggle_btn.text(), "🎹 演奏模式")


if __name__ == "__main__":
    unittest.main()
