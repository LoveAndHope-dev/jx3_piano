"""播放控制与播放线程生命周期。"""

from app.common import *  # noqa: F401,F403
from app.workers.play_thread import PlayThread


class PlaybackMixin:
    def on_play_progress(self, elapsed: float, thread=None):
        """播放线程上报的实时播放进度，驱动铺面播放线"""
        if thread is None:
            thread = self.sender()
        if (
            self.play_thread is not None
            and thread is not None
            and thread is not self.play_thread
        ):
            return  # 过期的进度信号
        if (
            self.currently_playing_midi_path
            and self.current_midi_path == self.currently_playing_midi_path
        ):
            self.piano_roll.set_playhead(self._playback_start_seconds + elapsed)

    def toggle_play(self):
        """切换播放状态"""
        if self.is_playing:
            self.stop_playing()
        else:
            self.start_playing()

    def start_playing(self):
        """开始播放（搜索过滤导致列表无选中时，仍按当前铺面曲目播放）"""
        # 上一次播放的线程可能仍在收尾；此时不能覆盖引用，否则会销毁运行中的 QThread
        if not self._drain_previous_play_thread():
            return

        current_item = self.play_listbox.currentItem()
        if not self.current_midi_path:
            QMessageBox.warning(self, "警告", "请先选择一个播放文件")
            return

        if current_item is not None and current_item.data(Qt.UserRole) != self.current_midi_path:
            QMessageBox.warning(self, "警告", "请先在铺面中打开要播放的曲目")
            return

        try:
            filename = os.path.basename(self.current_midi_path)

            # 播放数据来自 play_code JSON（进入演奏模式或导入时已自动保存），
            # 不在每次点击「弹奏」时重新做音符→按键映射。
            playhead = self.piano_roll.get_playhead_position()
            notes = self.piano_roll.get_notes()
            name = base_name(self.current_midi_path)
            code_path = play_code_path(get_play_code_dir_path(), name)
            play_data = read_play_code(code_path)
            if play_data is None:
                # 兜底：现场生成并写回，保证首次播放可用
                self._save_current_play_assets()
                play_data = read_play_code(code_path)
            if play_data is None:
                QMessageBox.warning(
                    self, "提示", "未找到可播放数据，请切换一次演奏模式后重试"
                )
                return

            playback_data = play_data.get("playback_data", [])
            if not playback_data:
                QMessageBox.warning(self, "警告", "当前乐器音域范围内没有可播放的音符")
                return

            source_notes = play_data.get("notes") or notes
            relative_notes = playback_notes_from_position(source_notes, playhead)
            if not relative_notes:
                QMessageBox.warning(self, "提示", "当前位置之后没有可播放的音符")
                return

            low_pitch, high_pitch = self.piano_roll.get_instrument_range()
            # JSON 时间轴已对齐到 0 秒，辅助线直接从辅助线位置起算
            self._playback_start_seconds = playhead

            data = dict(play_data)
            data["start_at"] = playhead
            data["transpose"] = self.current_transpose
            data["processed_tracks"] = self.current_processed_tracks

            self.log("")
            self.log(f"▶️ 开始播放: {filename}")

            # 使用新的播放线程（直接播放内存数据，不落盘）
            thread = PlayThread(data)
            self.play_thread = thread
            thread.log_signal.connect(self.log)
            thread.progress_signal.connect(self.on_play_progress)
            thread.finished_signal.connect(self.on_play_finished)
            # 线程真正退出后再清理引用，避免销毁运行中的 QThread
            thread.finished.connect(self._cleanup_play_thread)
            thread.start()

            self.is_playing = True
            self.currently_playing_midi_path = self.current_midi_path
            self._sync_roll_mode()
            self.piano_roll.set_playhead_locked(True)
            self._sync_bpm_enabled()

            # 更新主按钮为「停止」
            self._update_primary_btn()

        except Exception as e:
            self.log(f"❌ 播放失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"播放失败：{str(e)}")

    def stop_playing(self):
        """停止播放"""
        self.log("🛑 正在停止播放...")

        # 停止新的播放线程
        if hasattr(self, "play_thread") and self.play_thread:
            thread = self.play_thread
            try:
                thread.stop()
                if thread.isRunning():
                    thread.wait(3000)  # 等待最多3秒
            except Exception:
                pass
            # 线程未退出时保留引用，交给 finished 清理，避免销毁运行中的 QThread
            if not thread.isRunning():
                self.play_thread = None
                thread.deleteLater()

        self.is_playing = False
        self.currently_playing_midi_path = None
        self._sync_roll_mode()
        self.piano_roll.set_playhead_locked(False)
        self.piano_roll.set_playhead(None)
        self._sync_bpm_enabled()

        # 更新主按钮回「保存 / 演奏」
        self._update_primary_btn()

        self.log("⏹️ 播放已停止")

    def _drain_previous_play_thread(self) -> bool:
        """确保没有仍在运行的旧播放线程；返回是否可以开始新播放。"""
        thread = self.play_thread
        if thread is None:
            return True
        if thread.isRunning():
            self.log("⏳ 上一次播放仍在收尾，请稍后再试")
            return False
        self._cleanup_play_thread(thread)
        return True

    def _cleanup_play_thread(self, thread=None):
        """QThread.finished：线程已退出，安全释放引用（仅当它仍是当前线程）。"""
        if thread is None:
            thread = self.sender()
        if thread is None:
            thread = self.play_thread
        if thread is None:
            return
        if self.play_thread is thread:
            self.play_thread = None
        thread.deleteLater()

    def on_play_finished(self, success: bool, thread=None):
        """播放完成后的回调（只更新状态与界面，不销毁线程）"""
        if thread is None:
            thread = self.sender()
        if (
            self.play_thread is not None
            and thread is not None
            and thread is not self.play_thread
        ):
            return  # 过期线程的完成信号，不得打断当前播放
        if self.is_playing:  # 只在确实在播放时才更新状态
            self.is_playing = False
            self.currently_playing_midi_path = None
            self._sync_roll_mode()
            self.piano_roll.set_playhead_locked(False)
            self.piano_roll.set_playhead(None)
            self._sync_bpm_enabled()

            # 更新主按钮
            self._update_primary_btn()

            if success:
                self.log("✅ 播放完成")
            else:
                self.log("⏹️ 播放被中断")
