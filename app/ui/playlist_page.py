"""播放列表页。"""

from app.common import *  # noqa: F401,F403


class PlaylistPageMixin:
    def import_midi_file(self):
        """导入MIDI文件（支持多选）"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择MIDI文件", "", "MIDI files (*.mid *.midi);;All files (*.*)"
        )

        if file_paths:
            try:
                self.log(f"📁 准备导入 {len(file_paths)} 个文件...")

                # 开始批量导入
                self.batch_conversion_worker = BatchConversionWorker(file_paths)
                self.batch_conversion_worker.log_signal.connect(self.log)
                self.batch_conversion_worker.finished_signal.connect(
                    self.on_batch_conversion_finished
                )
                self.batch_conversion_worker.start()

                # 禁用导入按钮
                self.import_btn.setEnabled(False)
                self.import_btn.setText("🔄 批量导入中...")

            except Exception as e:
                self.log(f"❌ 导入失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"导入文件失败：{str(e)}")

    def on_batch_conversion_finished(self, success: bool, result: str):
        """批量转换完成回调"""
        # 恢复导入按钮
        self.import_btn.setEnabled(True)
        self.import_btn.setText("📁 导入MIDI")

        if success:
            self.refresh_play_list()
            self.log("🎊 批量导入完成!")
        else:
            self.log(f"❌ 批量导入失败: {result}")
            QMessageBox.critical(self, "批量导入失败", f"批量导入失败：{result}")

    def refresh_play_list(self):
        """按「隐藏记录 → 过滤 → 搜索 → 排序」重建播放列表，并尽量恢复选中项。"""
        try:
            midi_dir = get_midi_dir_path()
            entries = list_entries(midi_dir)
            entries = filter_entries(entries, self.play_search.text())
            entries = sort_entries(entries, self.play_sort_combo.currentData())

            current_path = self.current_midi_path
            self.play_listbox.blockSignals(True)
            try:
                self.play_listbox.clear()
                for name, path, _mtime in entries:
                    display_name = f"🎵 {os.path.splitext(name)[0]}"
                    item = QListWidgetItem("")
                    item.setData(Qt.UserRole, path)
                    item.setData(Qt.UserRole + 1, name)
                    item.setSizeHint(QSize(0, 48))
                    self.play_listbox.addItem(item)
                    self.play_listbox.setItemWidget(
                        item, self._make_play_row(item, name, display_name)
                    )
                    if path == current_path:
                        self.play_listbox.setCurrentItem(item)
            finally:
                self.play_listbox.blockSignals(False)

            if not entries and not self.play_search.text().strip():
                self.log("📝 midi/ 目录下没有可显示的 MIDI 文件")
        except Exception as e:
            self.log(f"❌ 刷新列表失败: {str(e)}")

    def _make_play_row(self, item, name: str, display_name: str) -> QWidget:
        """生成播放列表的行控件：名称 + 行末删除按钮。"""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 0, 2, 0)
        layout.setSpacing(4)

        label = QLabel(display_name)
        layout.addWidget(label, 1)

        delete_btn = QPushButton("🗑")
        delete_btn.setFixedSize(34, 26)
        delete_btn.setStyleSheet("padding: 0px 2px;")
        delete_btn.setToolTip(f"从列表移除「{name}」（保留磁盘文件）")
        delete_btn.clicked.connect(
            lambda _checked=False, p=item.data(Qt.UserRole), n=name: self.on_delete_play_item(p, n)
        )
        layout.addWidget(delete_btn)

        row.mousePressEvent = lambda _event, it=item: self.play_listbox.setCurrentItem(it)
        label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        return row

    def on_select_play_file(self):
        """选择播放文件时的处理"""
        current_item = self.play_listbox.currentItem()
        if not current_item:
            return

        try:
            midi_path = current_item.data(Qt.UserRole)
            filename = os.path.basename(midi_path)

            self.log(f"📄 已选择: {filename}")

            try:
                converter = MidiToKeysConverter()
                analysis = converter.analyze_midi_file(midi_path)
                if "error" in analysis:
                    self.log(f"⚠️ 无法读取文件信息: {analysis['error']}")
                else:
                    file_info = analysis["文件信息"]
                    self.log("=" * 50)
                    self.log("📊 文件信息:")
                    self.log(f"  🎼 音轨数量: {file_info['音轨数量']}")
                    self.log(f"  ⏱️ 总时长: {file_info['总时长']:.2f}秒")
                    self.log(f"  🔢 音符数量: {sum(analysis['音符统计'].values())}")
                    self.log("=" * 50)

            except Exception as e:
                self.log(f"⚠️ 无法读取文件信息: {str(e)}")

        except Exception as e:
            self.log(f"❌ 选择文件时出错: {str(e)}")

    def on_piano_roll_selection_changed(self, current, previous):
        """播放列表选中项变化时，按需切换铺面编辑区域显示的曲目"""
        if self.piano_roll_dirty:
            if not self._confirm_discard_piano_changes():
                self.play_listbox.blockSignals(True)
                self.play_listbox.setCurrentItem(previous)
                self.play_listbox.blockSignals(False)
                return
            self.piano_roll_dirty = False
            self._update_piano_dirty_indicator()

        if current is None:
            self.current_midi_path = None
            self.piano_stack.setCurrentWidget(self.piano_placeholder)
            self.piano_save_btn.setEnabled(False)
            self._set_range_controls_enabled(False)
            return

        midi_path = current.data(Qt.UserRole)
        self._load_piano_roll(midi_path)

    def _select_play_list_item_by_path(self, path: str):
        for i in range(self.play_listbox.count()):
            item = self.play_listbox.item(i)
            if item.data(Qt.UserRole) == path:
                self.play_listbox.setCurrentRow(i)
                return

    def on_new_play_item(self):
        """新建一个空白 MIDI 并加入播放列表，随后自动加载。"""
        midi_dir = get_midi_dir_path()
        try:
            os.makedirs(midi_dir, exist_ok=True)
            name = unique_midi_name(midi_dir)
            path = os.path.join(midi_dir, name)
            create_blank_midi(path)
        except Exception as exc:
            QMessageBox.critical(self, "新建失败", f"新建空 MIDI 失败：{exc}")
            return

        # 清空搜索过滤，确保新曲目一定出现在列表里并被选中加载
        self.play_search.blockSignals(True)
        self.play_search.clear()
        self.play_search.blockSignals(False)
        self.refresh_play_list()
        self._select_play_list_item_by_path(path)
        self.log(f"➕ 已新建空曲目: {name}")

    def on_delete_play_item(self, path=None, name=None):
        """删除指定曲目（默认当前选中项）：删除 midi/ 里的副本并按需清缓存。"""
        if path is None:
            item = self.play_listbox.currentItem()
            if item is None:
                return
            path = item.data(Qt.UserRole)
            name = item.data(Qt.UserRole + 1)
        if not path or not name:
            self.log("❌ 删除失败：列表项缺少文件名")
            return
        extra = (
            "\n（该曲目有未保存修改，删除会丢失这些修改）"
            if (path == self.current_midi_path and self.piano_roll_dirty)
            else ""
        )
        reply = QMessageBox.question(
            self,
            "删除曲目",
            f"删除「{name}」？{extra}\n会删除 midi 文件夹中的副本，导入的原始文件不受影响。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except OSError as exc:
            QMessageBox.critical(self, "删除失败", f"删除 MIDI 文件失败：{exc}")
            return

        self._remove_play_assets(path)

        if path == self.current_midi_path:
            self._clear_piano_roll_cache()
        self.refresh_play_list()
        self.log(f"🗑 已删除曲目: {name}")

    def _remove_play_assets(self, midi_path: str) -> None:
        """删除曲目时一并清理它的工作 MIDI 与 play_code JSON。"""
        name = base_name(midi_path)
        targets = (
            edited_midi_path(get_midi_dir_path(), name),
            play_code_path(get_play_code_dir_path(), name),
        )
        for target in targets:
            try:
                os.remove(target)
            except FileNotFoundError:
                continue
            except OSError as exc:
                self.log(f"⚠️ 清理缓存失败 {os.path.basename(target)}: {exc}")
