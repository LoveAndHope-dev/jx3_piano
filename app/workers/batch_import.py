"""批量导入 MIDI 的后台线程。"""

import os
import shutil

import mido
from PyQt5.QtCore import QThread, pyqtSignal

import music.paths as paths


class BatchConversionWorker(QThread):
    """批量MIDI导入工作线程（只校验+复制到 midi/，不再转换/生成 play_code json）"""

    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths

    def run(self):
        try:
            total_files = len(self.file_paths)
            successful_imports = 0
            failed_imports = 0

            self.log_signal.emit(f"🔄 开始批量导入 {total_files} 个MIDI文件...")

            for i, file_path in enumerate(self.file_paths, 1):
                try:
                    filename = os.path.basename(file_path)
                    target_path = os.path.join(paths.get_midi_dir_path(), filename)

                    self.log_signal.emit(f"📁 [{i}/{total_files}] 正在处理: {filename}")

                    # 校验：能被 mido 解析，且至少存在一个音符
                    try:
                        mid = mido.MidiFile(file_path)
                        has_note = any(
                            msg.type == "note_on" and msg.velocity > 0
                            for track in mid.tracks
                            for msg in track
                        )
                    except Exception as parse_error:
                        self.log_signal.emit(
                            f"❌ [{i}/{total_files}] {filename} 无法解析: {parse_error}"
                        )
                        failed_imports += 1
                        continue

                    if not has_note:
                        self.log_signal.emit(
                            f"⚠️ [{i}/{total_files}] {filename} 未找到可用音符，已跳过"
                        )
                        failed_imports += 1
                        continue

                    # 复制文件（如果目标文件不存在或者源文件更新）
                    if not os.path.exists(target_path) or os.path.getmtime(
                        file_path
                    ) > os.path.getmtime(target_path):
                        try:
                            if os.path.exists(target_path):
                                os.remove(target_path)
                            shutil.copy2(file_path, target_path)
                            # copy2 会保留源文件的修改时间，导致「导入时间」排序按源文件算；
                            # 这里把目标文件时间刷成导入时刻
                            os.utime(target_path, None)
                            self.log_signal.emit(
                                f"📋 [{i}/{total_files}] 已复制文件到工作目录"
                            )
                        except Exception as copy_error:
                            self.log_signal.emit(
                                f"❌ [{i}/{total_files}] {filename} 复制失败: {copy_error}"
                            )
                            failed_imports += 1
                            continue
                    else:
                        self.log_signal.emit(
                            f"📋 [{i}/{total_files}] 文件已存在，跳过复制"
                        )

                    self.log_signal.emit(f"✅ [{i}/{total_files}] {filename} 导入完成")
                    successful_imports += 1

                except Exception as e:
                    self.log_signal.emit(
                        f"❌ [{i}/{total_files}] {os.path.basename(file_path)} 导入失败: {str(e)}"
                    )
                    failed_imports += 1
                    continue

            # 汇总结果
            if successful_imports > 0:
                self.log_signal.emit(
                    f"🎉 批量导入完成! 成功: {successful_imports}, 失败: {failed_imports}"
                )
                self.finished_signal.emit(
                    True, f"成功导入 {successful_imports} 个文件"
                )
            else:
                self.finished_signal.emit(False, "所有文件导入失败")

        except Exception as e:
            self.finished_signal.emit(False, str(e))
