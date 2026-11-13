"""铺面编辑页。"""

from app.common import *  # noqa: F401,F403


class PianoPageMixin:
    def _setup_piano_roll_tab(self):
        """构建「铺面编辑」标签页"""
        piano_tab = QWidget()
        piano_layout = QVBoxLayout(piano_tab)
        piano_layout.setContentsMargins(0, 0, 0, 0)

        action_row = QHBoxLayout()
        title_label = QLabel("🎼 铺面编辑")
        title_label.setObjectName("pageTitle")
        title_label.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        action_row.addWidget(title_label)
        action_row.addStretch()

        # 第一行右侧：演奏/编辑模式切换
        self.range_toggle_btn = QPushButton("🎹 演奏模式")
        self.range_toggle_btn.setCheckable(True)
        self.range_toggle_btn.setEnabled(False)
        self.range_toggle_btn.clicked.connect(self.on_range_toggle_clicked)
        action_row.addWidget(self.range_toggle_btn)
        piano_layout.addLayout(action_row)

        # 第二行：主按钮 + 曲谱优化靠左，量化/BPM 靠右
        toolbar = QHBoxLayout()
        self.play_btn = QPushButton("💾 保存")
        self.play_btn.setObjectName("primaryBtn")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.on_primary_action)
        toolbar.addWidget(self.play_btn)

        self.arpeggiate_btn = QPushButton("🪄 曲谱优化")
        self.arpeggiate_btn.setToolTip("对选中音符做琶音整理（1/32 拍展开）")
        self.arpeggiate_btn.setEnabled(False)
        self.arpeggiate_btn.clicked.connect(self.on_arpeggiate_clicked)
        toolbar.addWidget(self.arpeggiate_btn)

        self.piano_dirty_label = QLabel("")
        toolbar.addWidget(self.piano_dirty_label)

        toolbar.addStretch()

        toolbar.addWidget(QLabel("量化:"))
        self.quantize_combo = QComboBox()
        self.quantize_combo.setEnabled(False)
        for label in ("关闭", "1/2", "1/4", "1/8", "1/16", "1/32", "1/64", "1/128"):
            self.quantize_combo.addItem(label)
        self.quantize_combo.currentTextChanged.connect(self.on_quantize_combo_changed)
        toolbar.addWidget(self.quantize_combo)

        toolbar.addWidget(QLabel("BPM:"))
        self.bpm_spin = QDoubleSpinBox()
        self.bpm_spin.setRange(0.0, 10000.0)
        self.bpm_spin.setDecimals(1)
        self.bpm_spin.setSingleStep(1.0)
        self.bpm_spin.setKeyboardTracking(False)
        self.bpm_spin.setValue(120.0)
        self.bpm_spin.setEnabled(False)
        self.bpm_spin.valueChanged.connect(self.on_bpm_changed)
        toolbar.addWidget(self.bpm_spin)

        piano_layout.addLayout(toolbar)

        # 第三行：键位映射与钢琴绝对音域，全部靠左
        toolbar_row2 = QHBoxLayout()
        toolbar_row2.addWidget(QLabel("演奏最低键位映射:"))
        self.range_low_combo = QComboBox()
        self.range_low_combo.setEnabled(False)
        toolbar_row2.addWidget(self.range_low_combo)

        toolbar_row2.addWidget(QLabel("演奏最高键位映射:"))
        self.range_high_combo = QComboBox()
        self.range_high_combo.setEnabled(False)
        toolbar_row2.addWidget(self.range_high_combo)

        toolbar_row2.addWidget(QLabel("钢琴音域绝对最低键:"))
        self.range_bottom_display = QLineEdit()
        self.range_bottom_display.setReadOnly(True)
        self.range_bottom_display.setFixedWidth(48)
        self.range_bottom_display.setAlignment(Qt.AlignCenter)
        toolbar_row2.addWidget(self.range_bottom_display)

        toolbar_row2.addWidget(QLabel("钢琴音域绝对最高键:"))
        self.range_top_display = QLineEdit()
        self.range_top_display.setReadOnly(True)
        self.range_top_display.setFixedWidth(48)
        self.range_top_display.setAlignment(Qt.AlignCenter)
        toolbar_row2.addWidget(self.range_top_display)
        toolbar_row2.addStretch()

        piano_layout.addLayout(toolbar_row2)

        self._populate_range_combos()
        self.range_low_combo.currentIndexChanged.connect(self.on_range_low_combo_changed)
        self.range_high_combo.currentIndexChanged.connect(self.on_range_high_combo_changed)

        self.piano_stack = QStackedWidget()

        self.piano_placeholder = QLabel("请选择左侧播放列表中的曲目以查看铺面")
        self.piano_placeholder.setAlignment(Qt.AlignCenter)
        self.piano_stack.addWidget(self.piano_placeholder)  # index 0

        self.piano_error_label = QLabel(
            "无法解析该 MIDI 文件，请确认文件格式是否正确"
        )
        self.piano_error_label.setAlignment(Qt.AlignCenter)
        self.piano_error_label.setWordWrap(True)
        self.piano_stack.addWidget(self.piano_error_label)  # index 1

        self.mapped_pitches = self._build_mapped_pitch_set()
        self.piano_roll = PianoRollWidget(self.mapped_pitches)
        self.piano_roll.notesChanged.connect(self.on_piano_roll_notes_changed)
        self.piano_roll.instrumentRangeChanged.connect(lambda *_: self._refresh_range_display())
        self.piano_roll.undoRequested.connect(self.undo_last_edit)
        self.piano_roll.redoRequested.connect(self.redo_last_edit)
        self.piano_stack.addWidget(self.piano_roll)  # index 2
        self._refresh_range_display()
        self._sync_roll_mode()

        self.piano_stack.setCurrentWidget(self.piano_placeholder)
        piano_layout.addWidget(self.piano_stack)

        self.right_tabs.addTab(piano_tab, "🎼 铺面编辑")

    def _populate_range_combos(self):
        """用全部88键范围内的自然音键位标签（按音高升序）填充最低/最高映射下拉框"""
        for combo in (self.range_low_combo, self.range_high_combo):
            combo.blockSignals(True)
            combo.clear()
            for pitch, label in self.key_ladder:
                combo.addItem(label, pitch)
            combo.blockSignals(False)

        default_low_pitch = self._pitch_for_label("Z")
        default_high_pitch = self._pitch_for_label("7")
        self._select_combo_by_pitch(self.range_low_combo, default_low_pitch)
        self._select_combo_by_pitch(self.range_high_combo, default_high_pitch)

    def _pitch_for_label(self, label: str) -> int:
        for pitch, key_label in self.key_ladder:
            if key_label == label:
                return pitch
        return self.key_ladder[0][0]

    def _note_name_for_pitch(self, pitch: int) -> str:
        """返回标准钢琴音名（如 C4），与下拉框使用的游戏按键字母标签无关"""
        return MidiToKeysConverter().get_note_name(pitch)

    def _select_combo_by_pitch(self, combo: QComboBox, pitch: int):
        for i in range(combo.count()):
            if combo.itemData(i) == pitch:
                combo.blockSignals(True)
                combo.setCurrentIndex(i)
                combo.blockSignals(False)
                return

    def _refresh_range_display(self):
        """用黄色映射框当前的绝对音域刷新只读字段（跟随框体移动）。"""
        low_pitch, high_pitch = self.piano_roll.get_instrument_range()
        self.range_bottom_display.setText(self._note_name_for_pitch(low_pitch))
        self.range_top_display.setText(self._note_name_for_pitch(high_pitch))

    def _build_mapped_pitch_set(self):
        """计算88键范围内可被映射为游戏按键的MIDI音高集合"""
        converter = MidiToKeysConverter()
        mapped = set()
        for pitch in range(21, 109):
            key_sequence, _ = converter.midi_note_to_key_sequence(
                pitch, {"sharp": False, "flat": False}
            )
            if key_sequence:
                mapped.add(pitch)
        return mapped

    def _load_piano_roll(self, midi_path: str):
        """从 MIDI 文件即时解析结构化音符数据并加载到铺面编辑区域"""
        try:
            converter = MidiToKeysConverter()
            track_filter, transpose = converter.auto_select_tracks_and_transpose(midi_path)
            if not track_filter:
                # 解析成功但音符不足以自动选轨（例如「➕ 新建」生成的空白 MIDI）：
                # 退化为第一个音轨上的空铺面，而不是报错，否则空曲目永远无法编辑。
                track_filter = [0]
                notes = []
            else:
                notes = converter.extract_notes(
                    midi_path, track_filter=track_filter, transpose=transpose
                )
        except Exception as e:
            # 解析失败：不把 current_midi_path 指向一个从未成功加载音符的文件，
            # 避免播放/保存误用铺面上残留的上一首曲目的音符
            self.current_midi_path = None
            self.log(f"❌ 解析 MIDI 失败: {e}")
            self.piano_stack.setCurrentWidget(self.piano_error_label)
            self._update_primary_btn()
            self._set_range_controls_enabled(False)
            self._undo_stack = []
            self._redo_stack = []
            self._history_baseline = None
            return

        self.current_midi_path = midi_path
        self.current_processed_tracks = track_filter
        self.current_transpose = transpose

        bpm, numerator, denominator = converter.get_tempo_and_time_signature(midi_path)
        self.current_bpm = bpm
        self.current_time_signature = (numerator, denominator)
        self._updating_bpm = True
        self.bpm_spin.setValue(float(bpm))
        self._updating_bpm = False
        seconds_per_beat = 60.0 / bpm * (4.0 / denominator)
        self.piano_roll.set_measure_grid(seconds_per_beat * numerator)
        self.piano_roll.set_beat_grid(seconds_per_beat, numerator)

        # 新增音符必须落在实际会被处理/保存的音轨上，否则另存为 MIDI 时会被静默丢弃
        self.piano_roll.set_default_track(track_filter[0])
        self.piano_roll.set_notes(notes)
        self.piano_roll.set_playhead_locked(self.is_playing)
        # set_notes 内部已把播放辅助线锚点归零；这里显式再设一次，保证
        # 「切换曲目 ⇒ 辅助线回到 0 秒」是唯一可依赖的规则
        self.piano_roll.set_playhead_anchor(0.0)

        self._reset_instrument_range()
        self._sync_roll_mode()
        self._set_range_controls_enabled(True)
        self._apply_quantize_grid()

        self.piano_stack.setCurrentWidget(self.piano_roll)
        self.piano_roll_dirty = False
        self._update_primary_btn()
        self._update_piano_dirty_indicator()
        self._save_current_play_assets()

        # 载入完成后记录撤销基线
        baseline = self._snapshot_state()
        self._undo_stack = [baseline]
        self._redo_stack = []
        self._history_baseline = baseline

    def on_piano_roll_notes_changed(self):
        """铺面上任意一次编辑（新增/删除/移动/调整时长）完成后触发"""
        self.piano_roll_dirty = True
        self._update_primary_btn()
        self._update_piano_dirty_indicator()
        self._record_history()

    def _set_range_controls_enabled(self, enabled: bool):
        self.range_toggle_btn.setEnabled(enabled)
        self.range_low_combo.setEnabled(enabled)
        self.range_high_combo.setEnabled(enabled)
        self.quantize_combo.setEnabled(enabled)
        self._sync_bpm_enabled()
        if not enabled:
            self.range_toggle_btn.setChecked(False)
        self._sync_roll_mode()

    def _sync_bpm_enabled(self) -> None:
        """BPM 只在有曲目且未播放时可编辑。"""
        self.bpm_spin.setEnabled(bool(self.current_midi_path) and not self.is_playing)

    def on_quantize_combo_changed(self, text: str) -> None:
        self.quantize_choice = text
        self._apply_quantize_grid()

    def on_bpm_changed(self, value: float) -> None:
        """BPM 数值框提交后：按拍位不变重算音符时间，并同步网格、量化与未保存状态。"""
        if self._updating_bpm or not self.current_midi_path:
            return
        if self.is_playing:
            # 播放中不允许改速度；把显示复位回当前值
            self._updating_bpm = True
            self.bpm_spin.setValue(float(self.current_bpm))
            self._updating_bpm = False
            return

        new_bpm = min(MAX_PIANO_BPM, max(MIN_PIANO_BPM, float(value)))
        if abs(new_bpm - float(value)) > 1e-9:
            # 输入越界时先回写钳制后的值，再按它更新铺面
            self._updating_bpm = True
            self.bpm_spin.setValue(new_bpm)
            self._updating_bpm = False
        if abs(new_bpm - self.current_bpm) < 1e-9:
            return

        factor = bpm_scale_factor(self.current_bpm, new_bpm)
        # 先更新 BPM，再缩放音符：rescale_times 会同步触发 notesChanged 记录历史，
        # 快照必须包含变更后的 BPM，否则撤销/前进会把新旧速度与音符错配
        self.current_bpm = new_bpm
        self.piano_roll.rescale_times(factor)

        numerator = self.current_time_signature[0]
        denominator = self.current_time_signature[1]
        measure_seconds, beat_seconds = grid_seconds_for_bpm(
            new_bpm, numerator, denominator
        )
        self.piano_roll.set_measure_grid(measure_seconds)
        self.piano_roll.set_beat_grid(beat_seconds, numerator)

        self._apply_quantize_grid()

    def on_arpeggiate_clicked(self):
        """对选中音符执行曲谱优化：调用项目内 arpeggiate.py 脚本展开琶音。"""
        if self.is_playing or self.range_toggle_btn.isChecked():
            return
        if not self.piano_roll._canvas._selected_ids:
            self.log("🪄 请先选中要优化的音符")
            return
        # 脚本以四分音符为单位计算 1/32 拍窗口与步长
        try:
            if self.current_bpm <= 0:
                raise ValueError("当前 BPM 无效")
            seconds_per_beat = 60.0 / self.current_bpm
            count = self.piano_roll.arpeggiate_selected(seconds_per_beat)
        except Exception as exc:  # 脚本失败时铺面保持不变
            self.log(f"❌ 曲谱优化失败：{exc}")
            return
        if count == 0:
            self.log("🪄 当前选中音符无需优化")
            return
        self.log(f"🪄 已对 {count} 个音符执行曲谱优化")

    def _apply_quantize_grid(self) -> None:
        """把当前量化下拉框选项按曲目实际 BPM 换算为网格秒数并下发给铺面；
        「关闭」或分母缺失时传 None（自由拖动）。1/4 恒等于一拍，只依赖 BPM，
        与拍号无关（拍号只用于小节线）。"""
        n = QUANTIZE_LABEL_TO_N.get(self.quantize_choice)
        if n is None:
            self.piano_roll.set_quantize_grid(None)
            return
        seconds_per_beat = 60.0 / self.current_bpm
        grid_seconds = seconds_per_beat * (4.0 / n)
        self.piano_roll.set_quantize_grid(grid_seconds)

    def _reset_instrument_range(self):
        """切换曲目时：映射下拉重置为 Z~7，黄色框默认覆盖 C2~B2。"""
        default_low_pitch = self._pitch_for_label("Z")
        default_high_pitch = self._pitch_for_label("7")

        self._select_combo_by_pitch(self.range_low_combo, default_low_pitch)
        self._select_combo_by_pitch(self.range_high_combo, default_high_pitch)

        self.range_toggle_btn.setChecked(False)
        self.range_toggle_btn.setText("🎹 演奏模式")

        # 黄色映射框默认覆盖映射默认值 Z(36)~7(83)，即 C2~B5
        self.piano_roll.set_instrument_range(default_low_pitch, default_high_pitch)
        self.piano_roll.set_instrument_range_visible(False)
        self._refresh_range_display()

    def _sync_roll_mode(self) -> None:
        """统一同步演奏/编辑模式的四处状态：勾选、文案、映射框、铺面只读。"""
        play_mode = self.range_toggle_btn.isChecked()
        self.piano_roll.set_instrument_range_visible(play_mode)
        self.piano_roll.set_read_only(play_mode or self.is_playing)
        self.range_toggle_btn.setText("✏️ 编辑模式" if play_mode else "🎹 演奏模式")
        self.arpeggiate_btn.setEnabled(
            bool(self.current_midi_path) and not play_mode and not self.is_playing
        )
        self._update_primary_btn()

    def _update_primary_btn(self) -> None:
        """按模式与播放状态更新合并主按钮的文案、样式与可用状态。"""
        play_mode = self.range_toggle_btn.isChecked()
        if play_mode:
            if self.is_playing:
                text, object_name, enabled = "⏹️ 停止", "stopBtn", True
            else:
                text = "▶️ 演奏"
                object_name = "primaryBtn"
                enabled = bool(self.current_midi_path)
        else:
            text = "💾 保存"
            object_name = "primaryBtn"
            enabled = bool(self.current_midi_path) and bool(self.piano_roll_dirty)
        self.play_btn.setText(text)
        self.play_btn.setObjectName(object_name)
        self.play_btn.setStyleSheet("")
        self.play_btn.setEnabled(enabled)

    def on_primary_action(self) -> None:
        """主按钮：编辑模式保存，演奏模式播放 / 停止。"""
        if self.range_toggle_btn.isChecked():
            self.toggle_play()
        else:
            self.save_piano_roll()

    def on_range_toggle_clicked(self):
        """切换演奏/编辑模式：进入演奏模式前自动保存 MIDI 与 play_code。"""
        if self.range_toggle_btn.isChecked():
            self._save_current_play_assets()
        self._sync_roll_mode()

    def on_range_low_combo_changed(self, index: int):
        """最低映射变化：只重新计算框体跨度（保持框体当前低边界不变），不移动框体位置"""
        if index < 0:
            return
        low_pitch = self.range_low_combo.itemData(index)
        high_pitch = self.range_high_combo.itemData(self.range_high_combo.currentIndex())
        if low_pitch > high_pitch:
            self._select_combo_by_pitch(self.range_high_combo, low_pitch)
            high_pitch = low_pitch
        span = high_pitch - low_pitch
        self.piano_roll.set_instrument_span(span)
        self._refresh_range_display()

    def on_range_high_combo_changed(self, index: int):
        """最高映射变化：只重新计算框体跨度（保持框体当前低边界不变），不移动框体位置"""
        if index < 0:
            return
        high_pitch = self.range_high_combo.itemData(index)
        low_pitch = self.range_low_combo.itemData(self.range_low_combo.currentIndex())
        if high_pitch < low_pitch:
            self._select_combo_by_pitch(self.range_low_combo, high_pitch)
            low_pitch = high_pitch
        span = high_pitch - low_pitch
        self.piano_roll.set_instrument_span(span)
        self._refresh_range_display()

    def _save_current_play_assets(self) -> None:
        """保存当前铺面的工作 MIDI 副本与 play_code JSON（导入/进入演奏模式时调用）。"""
        if not self.current_midi_path:
            return
        try:
            converter = MidiToKeysConverter()
            notes = self.piano_roll.get_notes()
            name = base_name(self.current_midi_path)
            midi_target = edited_midi_path(get_midi_dir_path(), name)
            os.makedirs(os.path.dirname(midi_target), exist_ok=True)
            converter.write_notes_to_midi(
                self.current_midi_path,
                notes,
                self.current_processed_tracks,
                midi_target,
                tempo_bpm=self.current_bpm,
            )

            low_pitch, high_pitch = self.piano_roll.get_instrument_range()
            target_low_pitch = self.range_low_combo.itemData(
                self.range_low_combo.currentIndex()
            )
            data = build_play_code_data(
                converter,
                notes,
                self.current_bpm,
                name,
                pitch_range=(low_pitch, high_pitch),
                transpose=target_low_pitch - low_pitch,
            )
            write_play_code(play_code_path(get_play_code_dir_path(), name), data)
            excluded = sum(
                1 for n in notes if not (low_pitch - 1 <= n["pitch"] <= high_pitch + 1)
            )
            if excluded:
                self.log(
                    f"⚠️ {excluded} 个音符在黄色映射框外，演奏时会被跳过"
                    "（可拖动黄框或改映射范围）"
                )
            self.log(f"💾 已保存铺面 MIDI 与 play_code: {name}")
        except Exception as exc:
            self.log(f"❌ 保存铺面资源失败: {exc}")

    def save_piano_roll(self):
        """把铺面编辑结果另存为一个新的 MIDI 文件（不覆盖原始导入文件）"""
        if not self.current_midi_path:
            return

        try:
            notes = self.piano_roll.get_notes()
            base_name = os.path.splitext(os.path.basename(self.current_midi_path))[0]
            output_path = self._next_available_edited_midi_path(base_name)

            converter = MidiToKeysConverter()
            converter.write_notes_to_midi(
                self.current_midi_path,
                notes,
                self.current_processed_tracks,
                output_path,
                tempo_bpm=self.current_bpm,
            )

            self.piano_roll_dirty = False
            self._update_primary_btn()
            self._update_piano_dirty_indicator()
            self.log(f"💾 已另存为新 MIDI 文件: {os.path.basename(output_path)}")

            self.refresh_play_list()
            self._select_play_list_item_by_path(output_path)

        except Exception as e:
            self.log(f"❌ 保存 MIDI 失败: {str(e)}")
            QMessageBox.critical(self, "保存失败", f"保存 MIDI 失败：{str(e)}")

    def _next_available_edited_midi_path(self, base_name: str) -> str:
        """为另存为生成一个不与现有文件冲突的新文件名"""
        midi_dir = get_midi_dir_path()
        candidate = os.path.join(midi_dir, f"{base_name}_edited.mid")
        if not os.path.exists(candidate):
            return candidate
        i = 2
        while True:
            candidate = os.path.join(midi_dir, f"{base_name}_edited_{i}.mid")
            if not os.path.exists(candidate):
                return candidate
            i += 1

    def _clear_piano_roll_cache(self):
        """删除当前曲目后清空铺面、播放与 BPM 等工具内缓存。"""
        if self.is_playing:
            self.stop_playing()

        self.range_toggle_btn.setChecked(False)
        self._sync_roll_mode()
        self.piano_roll.set_notes([])
        self.piano_roll.set_playhead_anchor(0.0)

        self.current_midi_path = None
        self.current_processed_tracks = []
        self.current_transpose = 0
        self.current_bpm = 120.0
        self.current_time_signature = (4, 4)
        self._playback_start_seconds = 0.0
        self._updating_bpm = True
        self.bpm_spin.setValue(120.0)
        self._updating_bpm = False

        self.piano_roll_dirty = False
        self._update_primary_btn()
        self._update_piano_dirty_indicator()
        self._set_range_controls_enabled(False)
        self.piano_stack.setCurrentWidget(self.piano_placeholder)
        self._undo_stack = []
        self._redo_stack = []
        self._history_baseline = None

    def _confirm_discard_piano_changes(self) -> bool:
        """存在未保存的铺面修改时，弹出确认框询问是否放弃"""
        reply = QMessageBox.question(
            self,
            "未保存的修改",
            "当前铺面存在未保存的修改，是否放弃这些修改？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes
