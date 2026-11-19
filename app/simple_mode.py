"""简单模式：隐藏铺面编辑，固定键位，一键优化并播放。"""

from app.common import *  # noqa: F401,F403


class SimpleModeMixin:
    """「懒人模式」：只保留选曲与一键优化播放。"""

    def on_simple_mode_toggled(self, checked: bool) -> None:
        if checked:
            self._enter_simple_mode()
        else:
            self._exit_simple_mode()

    def _enter_simple_mode(self) -> None:
        """进入简单模式：隐藏铺面编辑、丢弃未保存修改、固定键位映射。"""
        self.simple_mode = True
        if self.is_playing:
            self.stop_playing()

        # 静默丢弃未保存修改并清空铺面（不写盘）
        self.piano_roll_dirty = False
        self.piano_roll.set_notes([])
        self.piano_roll.set_playhead_anchor(0.0)
        self.piano_stack.setCurrentWidget(self.piano_placeholder)
        self._undo_stack = []
        self._redo_stack = []
        self._history_baseline = None
        self._play_assets_stale = True
        self._update_piano_dirty_indicator()
        self._update_primary_btn()

        # 移除「铺面编辑」标签页
        index = self.right_tabs.indexOf(self._piano_tab_widget)
        if index != -1:
            self.right_tabs.removeTab(index)

        # 固定 Z / 7，黄色框固定覆盖 C2~B5
        low_pitch = self._pitch_for_label("Z")
        high_pitch = self._pitch_for_label("7")
        self._select_combo_by_pitch(self.range_low_combo, low_pitch)
        self._select_combo_by_pitch(self.range_high_combo, high_pitch)
        self.range_low_combo.setEnabled(False)
        self.range_high_combo.setEnabled(False)
        self.range_toggle_btn.setChecked(False)
        self.piano_roll.set_instrument_range(low_pitch, high_pitch)
        self._refresh_range_display()

        self.simple_play_btn.setVisible(True)
        self.simple_mode_btn.setText("🧩 正常模式")
        self.log("🧩 已进入简单模式：铺面编辑已隐藏，播放前会自动执行曲谱优化")

    def _exit_simple_mode(self) -> None:
        """退出简单模式：恢复铺面编辑标签与映射，并重新加载原始 MIDI。"""
        self.simple_mode = False
        self.simple_play_btn.setVisible(False)
        self.simple_mode_btn.setText("🧩 简单模式")

        if self.right_tabs.indexOf(self._piano_tab_widget) == -1:
            index = min(self._piano_tab_index, self.right_tabs.count())
            self.right_tabs.insertTab(index, self._piano_tab_widget, "🎼 铺面编辑")

        # 重新加载未经优化的原始 MIDI；解析成功后会恢复映射控件可用状态
        if self.current_midi_path:
            self._load_piano_roll(self.current_midi_path)
        else:
            self._set_range_controls_enabled(False)
        self.log("🧩 已退出简单模式：铺面编辑已恢复")

    def on_simple_play_clicked(self) -> None:
        """简单播放：重读原始 MIDI → 全量曲谱优化 → 保存资产 → 播放。"""
        if self.is_playing:
            self.log("⏳ 正在播放，请先停止后再点击播放")
            return

        path = self.current_midi_path
        if not path:
            item = self.play_listbox.currentItem()
            if item is not None:
                path = item.data(Qt.UserRole)
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "提示", "请先选择一个曲目")
            return

        # 让列表当前项与要播放的曲目保持一致（start_playing 会校验）
        item = self.play_listbox.currentItem()
        if item is not None and item.data(Qt.UserRole) != path:
            self._select_play_list_item_by_path(path)

        try:
            converter = MidiToKeysConverter()
            track_filter, transpose = converter.auto_select_tracks_and_transpose(path)
            if not track_filter:
                track_filter = [0]
                notes = []
            else:
                notes = converter.extract_notes(
                    path, track_filter=track_filter, transpose=transpose
                )
            bpm, numerator, denominator = converter.get_tempo_and_time_signature(path)
        except Exception as exc:
            self.log(f"❌ 读取原始 MIDI 失败：{exc}")
            return

        self.current_midi_path = path
        self.current_processed_tracks = track_filter
        self.current_transpose = transpose
        self.current_bpm = bpm
        self.current_time_signature = (numerator, denominator)
        self._updating_bpm = True
        self.bpm_spin.setValue(float(bpm))
        self._updating_bpm = False

        seconds_per_beat = 60.0 / bpm * (4.0 / denominator)
        self.piano_roll.set_measure_grid(seconds_per_beat * numerator)
        self.piano_roll.set_beat_grid(seconds_per_beat, numerator)
        self.piano_roll.set_default_track(track_filter[0])
        self.piano_roll.set_notes(notes)
        self.piano_stack.setCurrentWidget(self.piano_roll)
        self.piano_roll.set_playhead_locked(False)
        self.piano_roll.set_playhead_anchor(0.0)

        # 固定 Z / 7 与 C2 / B5
        low_pitch = self._pitch_for_label("Z")
        high_pitch = self._pitch_for_label("7")
        self._select_combo_by_pitch(self.range_low_combo, low_pitch)
        self._select_combo_by_pitch(self.range_high_combo, high_pitch)
        self.piano_roll.set_instrument_range(low_pitch, high_pitch)
        self._refresh_range_display()

        # 全量曲谱优化：每次都从原始 MIDI 重新开始，避免重复叠加
        try:
            if bpm <= 0:
                raise ValueError("当前 BPM 无效")
            count = self.piano_roll.arpeggiate_all(60.0 / bpm)
        except Exception as exc:
            self.log(f"❌ 曲谱优化失败：{exc}")
            return
        self.log(f"🪄 简单模式已优化 {count} 个音符")

        # 保存优化后的编辑 MIDI 与 play_code JSON，再读取 JSON 播放
        if not self._save_current_play_assets():
            return

        self.piano_roll_dirty = False
        self._update_piano_dirty_indicator()
        baseline = self._snapshot_state()
        self._undo_stack = [baseline]
        self._redo_stack = []
        self._history_baseline = baseline

        self.start_playing()
