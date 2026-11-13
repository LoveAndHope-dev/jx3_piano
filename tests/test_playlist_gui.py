import json
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import gui
import arpeggiate
from PyQt5.QtCore import QPoint, QThread
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
        self._original_play_code_dir = gui.get_play_code_dir_path
        gui.get_play_code_dir_path = lambda: os.path.join(self.tmp.name, "play_code")
        self.addCleanup(self._restore_dirs)
        self.window = gui.MidiConverterGUI()
        self.addCleanup(self._close_window)

    def _close_window(self):
        # 关闭前清未保存标记，避免 offscreen 下弹出确认框
        self.window.piano_roll_dirty = False
        self.window.close()

    def _restore_dirs(self):
        gui.get_midi_dir_path = self._original_midi_dir
        gui.get_play_code_dir_path = self._original_play_code_dir

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

    def test_entering_play_mode_saves_midi_and_play_code(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 0.0, "duration": 0.5, "track": 0},
            {"id": 1, "pitch": 64, "start": 0.0, "duration": 0.5, "track": 0},
        ])
        self.window.range_toggle_btn.setChecked(True)
        self.window.on_range_toggle_clicked()
        name = os.path.splitext(os.path.basename(self.window.current_midi_path))[0]
        edited = os.path.join(self.tmp.name, "edited", name + ".mid")
        code = os.path.join(self.tmp.name, "play_code", name + ".json")
        self.assertTrue(os.path.exists(edited))
        self.assertTrue(os.path.exists(code))
        with open(code, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertTrue(data["playback_data"])

    def test_undo_restores_deleted_notes(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 0.0, "duration": 0.5, "track": 0},
            {"id": 1, "pitch": 64, "start": 0.0, "duration": 0.5, "track": 0},
        ])
        self.window._record_history()
        self.window.piano_roll._canvas._set_selection({0, 1})
        self.window.piano_roll._canvas._delete_selected()
        self.assertEqual(self.window.piano_roll.get_notes(), [])
        self.window.undo_last_edit()
        self.assertEqual(len(self.window.piano_roll.get_notes()), 2)
        self.assertTrue(self.window.piano_roll_dirty)
        self.window.redo_last_edit()
        self.assertEqual(self.window.piano_roll.get_notes(), [])
        self.assertFalse(self.window.piano_roll_dirty)

    def test_bpm_change_then_redo_keeps_new_tempo(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 1.0, "duration": 0.5, "track": 0},
        ])
        self.window._record_history()
        self.window.on_bpm_changed(60.0)
        self.window.undo_last_edit()
        self.window.redo_last_edit()
        self.assertAlmostEqual(self.window.current_bpm, 60.0)
        self.assertAlmostEqual(self.window.piano_roll.get_notes()[0]["start"], 2.0, delta=1e-6)

    def test_bpm_change_then_edit_then_undo(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 1.0, "duration": 0.5, "track": 0},
        ])
        self.window._record_history()
        self.window.on_bpm_changed(60.0)
        self.window.piano_roll._canvas._set_selection({0})
        self.window.piano_roll._canvas._nudge_selected(0.1)
        self.window.undo_last_edit()
        self.assertAlmostEqual(self.window.current_bpm, 60.0)
        self.assertAlmostEqual(self.window.piano_roll.get_notes()[0]["start"], 2.0, delta=1e-6)

    def test_new_edit_clears_redo(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 0.0, "duration": 0.5, "track": 0},
        ])
        self.window._record_history()
        self.window.piano_roll._canvas._set_selection({0})
        self.window.piano_roll._canvas._delete_selected()
        self.window.undo_last_edit()
        self.window.piano_roll._canvas._set_selection({0})
        self.window.piano_roll._canvas._nudge_selected(0.1)
        self.window.redo_last_edit()
        self.assertEqual(len(self.window.piano_roll.get_notes()), 1)
        self.assertAlmostEqual(
            self.window.piano_roll.get_notes()[0]["start"], 0.1, delta=1e-6
        )

    def test_undo_restores_playhead(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 0.0, "duration": 0.5, "track": 0},
        ])
        self.window._record_history()
        self.window.piano_roll.set_playhead_anchor(10.0)
        self.window._record_history()
        self.window.piano_roll._canvas._set_selection({0})
        self.window.piano_roll._canvas._delete_selected()
        self.window.piano_roll.set_playhead_anchor(20.0)
        self.window.undo_last_edit()
        self.assertAlmostEqual(self.window.piano_roll.get_playhead_position(), 10.0)

    def test_undo_is_not_recorded_as_edit(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 0.0, "duration": 0.5, "track": 0},
        ])
        self.window._record_history()
        self.window.piano_roll._canvas._set_selection({0})
        self.window.piano_roll._canvas._delete_selected()
        before = len(self.window._undo_stack)
        self.window.undo_last_edit()
        self.assertEqual(len(self.window._undo_stack), before - 1)
        self.assertEqual(len(self.window._redo_stack), 1)

    def test_undo_to_initial_state_clears_dirty(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 0.0, "duration": 0.5, "track": 0},
        ])
        baseline = self.window._snapshot_state()
        self.window._history_baseline = baseline
        self.window._undo_stack = [baseline]
        self.window.piano_roll._canvas._set_selection({0})
        self.window.piano_roll._canvas._delete_selected()
        self.assertTrue(self.window.piano_roll_dirty)
        self.window.undo_last_edit()
        self.assertEqual(len(self.window.piano_roll.get_notes()), 1)
        self.assertFalse(self.window.piano_roll_dirty)

    def test_undo_restores_bpm(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 1.0, "duration": 0.5, "track": 0},
        ])
        self.window._record_history()
        self.window.on_bpm_changed(60.0)
        self.assertAlmostEqual(self.window.current_bpm, 60.0)
        self.window.undo_last_edit()
        self.assertAlmostEqual(self.window.current_bpm, 120.0)
        self.assertAlmostEqual(self.window.piano_roll.get_notes()[0]["start"], 1.0)

    def test_undo_ignored_in_play_mode(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 0.0, "duration": 0.5, "track": 0},
        ])
        self.window.piano_roll._canvas._set_selection({0})
        self.window.piano_roll._canvas._delete_selected()
        self.window.range_toggle_btn.setChecked(True)
        self.window.on_range_toggle_clicked()
        self.window.undo_last_edit()
        self.assertEqual(self.window.piano_roll.get_notes(), [])

    def test_history_limit_is_fifty(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 0.0, "duration": 0.5, "track": 0},
        ])
        for _ in range(60):
            self.window.piano_roll._canvas._set_selection({0})
            self.window.piano_roll._canvas._nudge_selected(0.01)
        undos = 0
        while len(self.window._undo_stack) > 1:
            self.window.undo_last_edit()
            undos += 1
            if undos > 100:
                break
        self.assertEqual(undos, 50)

    def test_delete_removes_saved_assets(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 0.0, "duration": 0.5, "track": 0},
        ])
        self.window.range_toggle_btn.setChecked(True)
        self.window.on_range_toggle_clicked()
        path = self.window.current_midi_path
        name = os.path.splitext(os.path.basename(path))[0]
        edited = os.path.join(self.tmp.name, "edited", name + ".mid")
        code = os.path.join(self.tmp.name, "play_code", name + ".json")
        self.assertTrue(os.path.exists(edited))
        with patch.object(gui.QMessageBox, "question", return_value=QMessageBox.Yes):
            self.window.on_delete_play_item(path, name + ".mid")
        self.assertFalse(os.path.exists(edited))
        self.assertFalse(os.path.exists(code))

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
        self.assertEqual(self.window.piano_roll.get_instrument_range(), (36, 83))

    def test_absolute_key_fields_follow_range_box(self):
        self.window.on_new_play_item()
        self.assertEqual(self.window.range_bottom_display.text(), "C2")
        self.assertEqual(self.window.range_top_display.text(), "B5")
        self.window.piano_roll.set_instrument_range(60, 72)
        self.window._refresh_range_display()
        self.assertEqual(self.window.range_bottom_display.text(), "C4")
        self.assertEqual(self.window.range_top_display.text(), "C5")

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

    def test_arpeggiate_is_undoable(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 1.0, "duration": 0.5, "track": 0},
            {"id": 1, "pitch": 64, "start": 1.0, "duration": 0.5, "track": 0},
        ])
        self.window._record_history()
        self.window.piano_roll._canvas._set_selection({0, 1})
        self.window.on_arpeggiate_clicked()
        self.assertGreater(len(self.window._undo_stack), 1)
        self.window.undo_last_edit()
        starts = [n["start"] for n in self.window.piano_roll.get_notes()]
        self.assertEqual(starts, [1.0, 1.0])

    def test_arpeggiate_script_failure_keeps_roll(self):
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 1.0, "duration": 0.5, "track": 0},
            {"id": 1, "pitch": 64, "start": 1.0, "duration": 0.5, "track": 0},
        ])
        canvas = self.window.piano_roll._canvas
        canvas._set_selection({0, 1})
        notes_before = [dict(n) for n in self.window.piano_roll.get_notes()]
        items_before = set(canvas._note_items)
        undo_before = len(self.window._undo_stack)
        dirty_before = self.window.piano_roll_dirty
        with patch.object(arpeggiate, "main", side_effect=RuntimeError("boom")):
            self.window.on_arpeggiate_clicked()
        self.assertEqual(self.window.piano_roll.get_notes(), notes_before)
        self.assertEqual(set(canvas._note_items), items_before)
        self.assertEqual(canvas._selected_ids, {0, 1})
        self.assertEqual(len(self.window._undo_stack), undo_before)
        self.assertEqual(self.window.piano_roll_dirty, dirty_before)
        self.assertIn("曲谱优化失败", self.window.log_text.toPlainText())

    def test_arpeggiate_dedupe_removes_note_item_and_is_undoable(self):
        self.window.on_new_play_item()
        self.window.piano_roll.set_notes([
            {"id": 0, "pitch": 60, "start": 1.0, "duration": 0.5, "track": 0},
            {"id": 1, "pitch": 60, "start": 1.0, "duration": 0.25, "track": 0},
        ])
        self.window._record_history()
        canvas = self.window.piano_roll._canvas
        canvas._set_selection({0, 1})
        undo_before = len(self.window._undo_stack)
        self.window.piano_roll_dirty = False
        self.window.on_arpeggiate_clicked()
        self.assertEqual([n["id"] for n in self.window.piano_roll.get_notes()], [0])
        self.assertEqual(set(canvas._note_items), {0})
        self.assertEqual(canvas._selected_ids, {0})
        self.assertTrue(self.window.piano_roll_dirty)
        self.assertEqual(len(self.window._undo_stack), undo_before + 1)
        self.window.undo_last_edit()
        self.assertEqual(
            sorted(n["id"] for n in self.window.piano_roll.get_notes()), [0, 1]
        )

    def test_topmost_toggle_updates_text_and_log(self):
        self.window.topmost_btn.setChecked(True)
        self.window.toggle_topmost()
        self.assertEqual(self.window.topmost_btn.text(), "📌 取消置顶")
        self.assertIn("窗口已置顶", self.window.log_text.toPlainText())
        self.window.topmost_btn.setChecked(False)
        self.window.toggle_topmost()
        self.assertEqual(self.window.topmost_btn.text(), "📌 置顶")

    def _find_layout_containing(self, layout, widget):
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item.widget() is widget:
                return layout
            child = item.layout()
            if child is not None:
                found = self._find_layout_containing(child, widget)
                if found is not None:
                    return found
        return None

    def test_topmost_button_lives_in_control_panel_header(self):
        button = self.window.topmost_btn
        self.assertEqual(button.parentWidget().objectName(), "controlPanel")
        header = button.parentWidget().layout().itemAt(0).layout()
        title = next(
            header.itemAt(i).widget()
            for i in range(header.count())
            if header.itemAt(i).widget() is not None
            and header.itemAt(i).widget().objectName() == "panelTitle"
        )
        self.assertLess(header.indexOf(title), header.indexOf(button))
        log_tab = self.window.right_tabs.widget(1)
        self.assertNotIn(button, log_tab.findChildren(gui.QPushButton))

    def test_piano_toolbar_rows_hug_left(self):
        piano_tab = self.window.right_tabs.widget(0)
        first_row = self._find_layout_containing(piano_tab.layout(), self.window.play_btn)
        self.assertIsNotNone(first_row)
        self.assertIs(first_row.itemAt(0).widget(), self.window.play_btn)
        first_spacers = [
            index
            for index in range(first_row.count())
            if first_row.itemAt(index).spacerItem() is not None
        ]
        self.assertEqual(first_spacers, [first_row.count() - 1])

        second_row = self._find_layout_containing(piano_tab.layout(), self.window.bpm_spin)
        self.assertIsNotNone(second_row)
        second_spacers = [
            index
            for index in range(second_row.count())
            if second_row.itemAt(index).spacerItem() is not None
        ]
        self.assertEqual(second_spacers, [second_row.count() - 1])

    def test_piano_toolbar_positions_stable_when_window_grows(self):
        widgets = [
            self.window.play_btn,
            self.window.range_low_combo,
            self.window.range_high_combo,
            self.window.bpm_spin,
        ]

        def sample():
            _application().processEvents()
            return [
                (w.mapTo(self.window, QPoint(0, 0)).x(), w.width()) for w in widgets
            ]

        self.window.resize(1400, 900)
        wide = sample()
        self.window.resize(2200, 900)
        wider = sample()
        self.assertEqual(wide, wider)

    def test_play_finished_keeps_thread_reference(self):
        self.window.on_new_play_item()
        thread = QThread()
        self.window.play_thread = thread
        self.window.is_playing = True
        try:
            self.window.on_play_finished(True)
            self.assertIs(self.window.play_thread, thread)
            self.assertFalse(self.window.is_playing)
        finally:
            self.window.play_thread = None
            thread.deleteLater()

    def test_cleanup_play_thread_releases_reference(self):
        thread = QThread()
        self.window.play_thread = thread
        self.window._cleanup_play_thread()
        self.assertIsNone(self.window.play_thread)

    def test_cleanup_play_thread_is_safe_without_thread(self):
        self.window.play_thread = None
        self.window._cleanup_play_thread()
        self.assertIsNone(self.window.play_thread)

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
