"""撤销 / 前进历史。"""

from app.common import *  # noqa: F401,F403


class HistoryMixin:
    def _snapshot_state(self) -> dict:
        return {
            "notes": self.piano_roll.get_notes(),
            "bpm": float(self.current_bpm),
            "signature": tuple(self.current_time_signature),
            "playhead": float(self.piano_roll.get_playhead_position()),
            "clipboard": self.piano_roll.clipboard_notes(),
        }

    @staticmethod
    def _states_equal(a: dict, b: dict) -> bool:
        if a is None or b is None:
            return False
        return (
            a["notes"] == b["notes"]
            and abs(float(a["bpm"]) - float(b["bpm"])) < 1e-9
            and tuple(a["signature"]) == tuple(b["signature"])
        )

    def _current_track_loaded(self) -> bool:
        return bool(self.current_midi_path) and self._history_baseline is not None

    def _record_history(self) -> None:
        if self._history_applying or not self._current_track_loaded():
            return
        snapshot = self._snapshot_state()
        if self._undo_stack and self._states_equal(snapshot, self._undo_stack[-1]):
            return
        self._undo_stack.append(snapshot)
        # +1 是基线快照；保证最多保留 50 个可撤销步骤
        if len(self._undo_stack) > self._history_limit + 1:
            del self._undo_stack[0]
        self._redo_stack.clear()

    def _apply_history_state(self, state: dict) -> None:
        self._history_applying = True
        try:
            self.current_bpm = float(state["bpm"])
            self.current_time_signature = tuple(state["signature"])
            numerator, denominator = self.current_time_signature
            measure_seconds, beat_seconds = grid_seconds_for_bpm(
                self.current_bpm, numerator, denominator
            )
            self.piano_roll.set_measure_grid(measure_seconds)
            self.piano_roll.set_beat_grid(beat_seconds, numerator)
            self._updating_bpm = True
            self.bpm_spin.setValue(self.current_bpm)
            self._updating_bpm = False
            self.piano_roll.set_notes(state["notes"])
            self.piano_roll.restore_clipboard(state.get("clipboard", []))
            self.piano_roll.set_playhead_anchor(state["playhead"])
            self._apply_quantize_grid()
            is_dirty = not self._states_equal(state, self._history_baseline)
            self.piano_roll_dirty = is_dirty
            self._update_primary_btn()
            self._update_piano_dirty_indicator()
        finally:
            self._history_applying = False

    def undo_last_edit(self) -> None:
        if self.is_playing or self.range_toggle_btn.isChecked():
            return
        if len(self._undo_stack) <= 1:
            return
        current = self._undo_stack.pop()
        self._redo_stack.append(current)
        target = dict(self._undo_stack[-1])
        # 撤销恢复的是「执行该编辑时」的辅助线位置，而不是上一步的旧位置
        target["playhead"] = current["playhead"]
        self._apply_history_state(target)
        self.log("↩️ 已撤销上一步编辑")

    def redo_last_edit(self) -> None:
        if self.is_playing or self.range_toggle_btn.isChecked():
            return
        if not self._redo_stack:
            return
        state = self._redo_stack.pop()
        self._undo_stack.append(state)
        self._apply_history_state(state)
        self.log("↪️ 已前进到下一步编辑")

    def _update_piano_dirty_indicator(self):
        self.piano_dirty_label.setText("● 未保存" if self.piano_roll_dirty else "")
