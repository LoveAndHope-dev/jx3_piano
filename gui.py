import sys
import os
import shutil
import threading
import subprocess
import json
import time
import glob
from datetime import datetime
from typing import Optional
import ctypes

import mido

# PyQt5 imports
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPushButton,
    QListWidget,
    QTextEdit,
    QLabel,
    QFileDialog,
    QMessageBox,
    QFrame,
    QListWidgetItem,
    QProgressBar,
    QStatusBar,
    QToolBar,
    QAction,
    QGroupBox,
    QTabWidget,
    QStackedWidget,
    QComboBox,
)
from PyQt5.QtCore import (
    Qt,
    QThread,
    pyqtSignal,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QRect,
)
from PyQt5.QtGui import (
    QFont,
    QIcon,
    QPalette,
    QColor,
    QPixmap,
    QPainter,
    QBrush,
    QLinearGradient,
    QTextCharFormat,
)

# 导入主程序模块
try:
    from build_music import (
        MidiToKeysConverter,
        build_music,
        MID_DIR_PATH,
        PLAY_CODE_DIR,
        get_midi_dir_path,
        get_play_code_dir_path,
        get_natural_key_ladder,
    )
except ImportError:
    print("错误: 无法导入主程序模块，请确保主程序文件在同一目录下")
    sys.exit(1)

from piano_roll import PianoRollWidget


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
                    target_path = os.path.join(get_midi_dir_path(), filename)

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


class PlayThread(QThread):
    """使用新播放器模块的播放线程；播放数据在内存中生成，不经过任何文件"""

    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(float)  # 距实际播放开始的已耗时秒数
    finished_signal = pyqtSignal(bool)  # True=正常完成, False=被中断

    def __init__(self, data: dict):
        super().__init__()
        self.data = data
        self.player = None
        self.should_stop = False

    def run(self):
        try:
            # 导入播放器模块
            from player import JX3Player

            # 创建播放器实例，设置日志回调与进度回调
            self.player = JX3Player(
                log_callback=self.log_signal.emit,
                progress_callback=self.progress_signal.emit,
            )

            # 开始播放（直接使用内存数据，不读取文件）
            success = self.player.play_from_data(self.data)

            self.finished_signal.emit(success)

        except Exception as e:
            self.log_signal.emit(f"❌ 播放器启动失败: {e}")
            self.finished_signal.emit(False)

    def stop(self):
        """停止播放"""
        self.should_stop = True
        if self.player:
            self.player.stop()

        self.log_signal.emit("🛑 正在停止播放...")

        # 等待线程结束
        if self.isRunning():
            self.wait(3000)  # 等待最多3秒
            if self.isRunning():
                self.terminate()  # 强制终止


class MidiConverterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 剑网三自动演奏工具")
        self.setGeometry(100, 100, 1000, 700)

        # 播放相关变量
        self.play_thread = None
        self.is_playing = False
        self.currently_playing_midi_path = None

        # 铺面编辑相关变量
        self.current_midi_path = None
        self.current_processed_tracks = []
        self.current_transpose = 0
        self.piano_roll_dirty = False

        # 乐器音域框相关变量
        self.key_ladder = get_natural_key_ladder()

        # 设置应用样式
        self.setup_style()

        # 创建界面
        self.setup_ui()

        # 初始化
        self.refresh_play_list()
        self.log("🎵 剑网三自动演奏工具已启动")
        self.log("💡 请导入MIDI文件开始使用")

    def setup_style(self):
        """设置应用程序样式"""
        self.setStyleSheet(
            """
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2C3E50, stop:1 #34495E);
            }
            
            QWidget {
                background-color: transparent;
                color: #ECF0F1;
                font-family: 'Microsoft YaHei UI', 'Segoe UI', Arial;
                font-size: 14px;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498DB, stop:1 #2980B9);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 18px;
                min-height: 25px;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5DADE2, stop:1 #3498DB);
                transform: translateY(-2px);
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2980B9, stop:1 #21618C);
            }
            
            QPushButton#importBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #27AE60, stop:1 #229954);
            }
            
            QPushButton#importBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #58D68D, stop:1 #27AE60);
            }
            
            QPushButton#playBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F39C12, stop:1 #E67E22);
                min-width: 50px;
                font-size: 16px;
                font-weight: bold;
            }
            
            QPushButton#playBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F8C471, stop:1 #F39C12);
            }
            
            QPushButton#stopBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #E74C3C, stop:1 #C0392B);
            }
            
            QPushButton#stopBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F1948A, stop:1 #E74C3C);
            }
            
            QPushButton#refreshBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #8E44AD, stop:1 #7D3C98);
                min-width: 30px;
                max-width: 35px;
                padding: 8px 8px;
                font-size: 12px;
            }
            
            QPushButton#clearBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #E74C3C, stop:1 #C0392B);
                font-size: 10px;
                padding: 5px 10px;
                min-height: 15px;
            }
            
            QListWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(52, 73, 94, 0.8), stop:1 rgba(44, 62, 80, 0.8));
                border: 2px solid #34495E;
                border-radius: 10px;
                padding: 5px;
                font-size: 13px;
                selection-background-color: #3498DB;
            }
            
            QListWidget::item {
                background: rgba(52, 152, 219, 0.1);
                border: 1px solid rgba(52, 152, 219, 0.3);
                border-radius: 5px;
                padding: 8px;
                margin: 2px;
            }
            
            QListWidget::item:hover {
                background: rgba(52, 152, 219, 0.3);
                border: 1px solid rgba(52, 152, 219, 0.6);
            }
            
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498DB, stop:1 #2980B9);
                border: 1px solid #2980B9;
            }
            
            QTextEdit {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(44, 62, 80, 0.9), stop:1 rgba(52, 73, 94, 0.9));
                border: 2px solid #34495E;
                border-radius: 10px;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 13px;
                color: #ECF0F1;
                selection-background-color: #3498DB;
            }
            
            QLabel {
                color: #ECF0F1;
                font-weight: bold;
                font-size: 15px;
            }
            
            QLabel#creditLabel {
                color: #7F8C8D;
                font-size: 9px;
                font-weight: normal;
                font-style: italic;
            }
            
            QGroupBox {
                border: 2px solid #34495E;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #ECF0F1;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498DB, stop:1 #2980B9);
                border-radius: 5px;
                color: white;
            }
            
            QFrame#leftPanel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(52, 73, 94, 0.7), stop:1 rgba(44, 62, 80, 0.7));
                border: 2px solid #34495E;
                border-radius: 15px;
                margin: 5px;
            }
            
            QFrame#rightPanel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(44, 62, 80, 0.7), stop:1 rgba(52, 73, 94, 0.7));
                border: 2px solid #34495E;
                border-radius: 15px;
                margin: 5px;
            }
            
            QSplitter::handle {
                background: #34495E;
                width: 3px;
                border-radius: 1px;
            }
            
            QSplitter::handle:hover {
                background: #3498DB;
            }

            QTabWidget::pane {
                background: rgba(44, 62, 80, 0.7);
                border: 2px solid #34495E;
                border-radius: 10px;
                top: -1px;
            }

            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34495E, stop:1 #2C3E50);
                color: #ECF0F1;
                border: 1px solid #34495E;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 16px;
                margin-right: 2px;
                font-size: 13px;
            }

            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498DB, stop:1 #2980B9);
                color: white;
            }

            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #45607A, stop:1 #34495E);
            }

            QComboBox {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(52, 73, 94, 0.8), stop:1 rgba(44, 62, 80, 0.8));
                border: 2px solid #34495E;
                border-radius: 6px;
                padding: 4px 8px;
                color: #ECF0F1;
                font-size: 13px;
                min-width: 50px;
            }

            QComboBox:hover {
                border: 2px solid #3498DB;
            }

            QComboBox QAbstractItemView {
                background: #2C3E50;
                color: #ECF0F1;
                selection-background-color: #3498DB;
                border: 1px solid #34495E;
            }

        """
        )

    def setup_ui(self):
        """设置用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧面板
        left_frame = QFrame()
        left_frame.setObjectName("leftPanel")
        left_frame.setFixedWidth(350)
        splitter.addWidget(left_frame)

        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(15, 15, 15, 15)

        # 控制按钮组
        control_group = QGroupBox("🎛️ 控制面板")
        left_layout.addWidget(control_group)

        control_layout = QVBoxLayout(control_group)

        # 按钮行1
        btn_row1 = QHBoxLayout()

        self.import_btn = QPushButton("📁 导入MIDI")
        self.import_btn.setObjectName("importBtn")
        self.import_btn.clicked.connect(self.import_midi_file)
        btn_row1.addWidget(self.import_btn)

        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setObjectName("refreshBtn")
        self.refresh_btn.setToolTip("刷新列表")
        self.refresh_btn.clicked.connect(self.refresh_play_list)
        btn_row1.addWidget(self.refresh_btn)

        control_layout.addLayout(btn_row1)

        # 添加作者信息
        credit_label = QLabel("by 66maer")
        credit_label.setObjectName("creditLabel")
        credit_label.setAlignment(Qt.AlignCenter)
        control_layout.addWidget(credit_label)

        # 播放列表组
        list_group = QGroupBox("🎼 播放列表")
        left_layout.addWidget(list_group)

        list_layout = QVBoxLayout(list_group)

        self.play_listbox = QListWidget()
        self.play_listbox.itemSelectionChanged.connect(self.on_select_play_file)
        self.play_listbox.currentItemChanged.connect(self.on_piano_roll_selection_changed)
        list_layout.addWidget(self.play_listbox)

        # 右侧面板
        right_frame = QFrame()
        right_frame.setObjectName("rightPanel")
        splitter.addWidget(right_frame)

        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(15, 15, 15, 15)

        self.right_tabs = QTabWidget()
        right_layout.addWidget(self.right_tabs)

        self._setup_piano_roll_tab()
        self._setup_log_tab()

        # 设置分割器比例
        splitter.setSizes([350, 650])

    def _setup_piano_roll_tab(self):
        """构建「铺面编辑」标签页"""
        piano_tab = QWidget()
        piano_layout = QVBoxLayout(piano_tab)
        piano_layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        title_label = QLabel("🎼 铺面编辑")
        title_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        toolbar.addWidget(title_label)
        toolbar.addStretch()

        self.piano_dirty_label = QLabel("")
        toolbar.addWidget(self.piano_dirty_label)

        self.play_btn = QPushButton("▶️ 播放")
        self.play_btn.setObjectName("playBtn")
        self.play_btn.clicked.connect(self.toggle_play)
        toolbar.addWidget(self.play_btn)

        self.piano_save_btn = QPushButton("💾 保存")
        self.piano_save_btn.setEnabled(False)
        self.piano_save_btn.clicked.connect(self.save_piano_roll)
        toolbar.addWidget(self.piano_save_btn)

        piano_layout.addLayout(toolbar)

        # 乐器音域框工具栏
        range_toolbar = QHBoxLayout()

        self.range_toggle_btn = QPushButton("🟨 显示映射")
        self.range_toggle_btn.setCheckable(True)
        self.range_toggle_btn.setEnabled(False)
        self.range_toggle_btn.clicked.connect(self.on_range_toggle_clicked)
        range_toolbar.addWidget(self.range_toggle_btn)

        range_toolbar.addWidget(QLabel("最低映射:"))
        self.range_low_combo = QComboBox()
        self.range_low_combo.setEnabled(False)
        range_toolbar.addWidget(self.range_low_combo)

        range_toolbar.addWidget(QLabel("最高映射:"))
        self.range_high_combo = QComboBox()
        self.range_high_combo.setEnabled(False)
        range_toolbar.addWidget(self.range_high_combo)

        range_toolbar.addStretch()
        piano_layout.addLayout(range_toolbar)

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
        self.piano_stack.addWidget(self.piano_roll)  # index 2

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

        default_low_pitch = self._pitch_for_label("A")
        default_high_pitch = self._pitch_for_label("J")
        self._select_combo_by_pitch(self.range_low_combo, default_low_pitch)
        self._select_combo_by_pitch(self.range_high_combo, default_high_pitch)

    def _pitch_for_label(self, label: str) -> int:
        for pitch, key_label in self.key_ladder:
            if key_label == label:
                return pitch
        return self.key_ladder[0][0]

    def _select_combo_by_pitch(self, combo: QComboBox, pitch: int):
        for i in range(combo.count()):
            if combo.itemData(i) == pitch:
                combo.blockSignals(True)
                combo.setCurrentIndex(i)
                combo.blockSignals(False)
                return

    def _setup_log_tab(self):
        """构建「操作日志」标签页"""
        log_tab = QWidget()
        log_tab_layout = QVBoxLayout(log_tab)
        log_tab_layout.setContentsMargins(0, 0, 0, 0)

        # 日志标题和功能按钮
        log_header = QHBoxLayout()

        log_label = QLabel("📋 操作日志")
        log_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        log_header.addWidget(log_label)

        log_header.addStretch()

        self.topmost_btn = QPushButton("📌 置顶")
        self.topmost_btn.setObjectName("clearBtn")
        self.topmost_btn.setCheckable(True)
        self.topmost_btn.clicked.connect(self.toggle_topmost)
        log_header.addWidget(self.topmost_btn)

        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.setObjectName("clearBtn")
        self.clear_btn.clicked.connect(self.clear_log)
        log_header.addWidget(self.clear_btn)

        log_tab_layout.addLayout(log_header)

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_tab_layout.addWidget(self.log_text)

        self.right_tabs.addTab(log_tab, "📋 操作日志")

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

    def log(self, message: str):
        """添加日志信息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        # 添加到日志框
        self.log_text.append(log_message)

        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.log("📋 日志已清空")

    def toggle_topmost(self):
        """切换窗口置顶状态"""
        if self.topmost_btn.isChecked():
            # 设置窗口置顶
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.show()
            self.topmost_btn.setText("📌 取消置顶")
            self.log("📌 窗口已置顶")
        else:
            # 取消窗口置顶
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.show()
            self.topmost_btn.setText("📌 置顶")
            self.log("📌 窗口已取消置顶")

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
        """刷新播放文件列表（直接列出 midi/ 目录下已导入的 MIDI 文件）"""
        self.play_listbox.clear()

        try:
            midi_files = glob.glob(
                os.path.join(get_midi_dir_path(), "*.mid")
            ) + glob.glob(os.path.join(get_midi_dir_path(), "*.midi"))

            for file_path in sorted(midi_files):
                filename = os.path.basename(file_path)
                display_name = f"🎵 {os.path.splitext(filename)[0]}"

                item = QListWidgetItem(display_name)
                item.setData(Qt.UserRole, file_path)
                self.play_listbox.addItem(item)

            if midi_files:
                self.log(f"🔄 已刷新列表，找到 {len(midi_files)} 个已导入的 MIDI 文件")
            else:
                self.log("📝 暂无已导入的 MIDI 文件，请导入MIDI文件")

        except Exception as e:
            self.log(f"❌ 刷新列表失败: {str(e)}")

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

    def _load_piano_roll(self, midi_path: str):
        """从 MIDI 文件即时解析结构化音符数据并加载到铺面编辑区域"""
        try:
            converter = MidiToKeysConverter()
            track_filter, transpose = converter.auto_select_tracks_and_transpose(midi_path)
            if not track_filter:
                raise ValueError("未找到足够的音符以自动选择音轨")
            notes = converter.extract_notes(midi_path, track_filter=track_filter, transpose=transpose)
        except Exception as e:
            # 解析失败：不把 current_midi_path 指向一个从未成功加载音符的文件，
            # 避免播放/保存误用铺面上残留的上一首曲目的音符
            self.current_midi_path = None
            self.log(f"❌ 解析 MIDI 失败: {e}")
            self.piano_stack.setCurrentWidget(self.piano_error_label)
            self.piano_save_btn.setEnabled(False)
            self._set_range_controls_enabled(False)
            return

        self.current_midi_path = midi_path
        self.current_processed_tracks = track_filter
        self.current_transpose = transpose

        # 新增音符必须落在实际会被处理/保存的音轨上，否则另存为 MIDI 时会被静默丢弃
        self.piano_roll.set_default_track(track_filter[0])
        self.piano_roll.set_notes(notes)
        self.piano_roll.set_read_only(self.is_playing)
        if not (self.is_playing and midi_path == self.currently_playing_midi_path):
            self.piano_roll.set_playhead(None)

        self._reset_instrument_range()
        self._set_range_controls_enabled(True)

        self.piano_stack.setCurrentWidget(self.piano_roll)
        self.piano_roll_dirty = False
        self.piano_save_btn.setEnabled(False)
        self._update_piano_dirty_indicator()

    def on_piano_roll_notes_changed(self):
        """铺面上任意一次编辑（新增/删除/移动/调整时长）完成后触发"""
        self.piano_roll_dirty = True
        self.piano_save_btn.setEnabled(True)
        self._update_piano_dirty_indicator()

    def _update_piano_dirty_indicator(self):
        self.piano_dirty_label.setText("● 未保存" if self.piano_roll_dirty else "")

    def _set_range_controls_enabled(self, enabled: bool):
        self.range_toggle_btn.setEnabled(enabled)
        self.range_low_combo.setEnabled(enabled)
        self.range_high_combo.setEnabled(enabled)
        if not enabled:
            self.range_toggle_btn.setChecked(False)

    def _reset_instrument_range(self):
        """每次切换选中曲目时，乐器音域框重置为默认范围（A~J）并隐藏"""
        default_low_pitch = self._pitch_for_label("A")
        default_high_pitch = self._pitch_for_label("J")

        self._select_combo_by_pitch(self.range_low_combo, default_low_pitch)
        self._select_combo_by_pitch(self.range_high_combo, default_high_pitch)

        self.range_toggle_btn.setChecked(False)
        self.range_toggle_btn.setText("🟨 显示映射")

        self.piano_roll.set_instrument_range(default_low_pitch, default_high_pitch)
        self.piano_roll.set_instrument_range_visible(False)

    def on_range_toggle_clicked(self):
        """切换乐器音域框在铺面中的可见性（纯视觉开关，不影响播放使用的范围）"""
        visible = self.range_toggle_btn.isChecked()
        self.range_toggle_btn.setText("🟨 隐藏映射" if visible else "🟨 显示映射")
        self.piano_roll.set_instrument_range_visible(visible)

    def on_range_low_combo_changed(self, index: int):
        """最低映射变化：只重新计算框体跨度（保持框体当前低边界不变），不移动框体位置"""
        if index < 0:
            return
        low_pitch = self.range_low_combo.itemData(index)
        high_pitch = self.range_high_combo.itemData(self.range_high_combo.currentIndex())
        if low_pitch > high_pitch:
            self._select_combo_by_pitch(self.range_high_combo, low_pitch)
            high_pitch = low_pitch
        span_idx = self._ladder_index_for_pitch(high_pitch) - self._ladder_index_for_pitch(low_pitch)
        self.piano_roll.set_instrument_span(span_idx)

    def on_range_high_combo_changed(self, index: int):
        """最高映射变化：只重新计算框体跨度（保持框体当前低边界不变），不移动框体位置"""
        if index < 0:
            return
        high_pitch = self.range_high_combo.itemData(index)
        low_pitch = self.range_low_combo.itemData(self.range_low_combo.currentIndex())
        if high_pitch < low_pitch:
            self._select_combo_by_pitch(self.range_low_combo, high_pitch)
            low_pitch = high_pitch
        span_idx = self._ladder_index_for_pitch(high_pitch) - self._ladder_index_for_pitch(low_pitch)
        self.piano_roll.set_instrument_span(span_idx)

    def _ladder_index_for_pitch(self, pitch: int) -> int:
        for i, (p, _label) in enumerate(self.key_ladder):
            if p == pitch:
                return i
        return 0

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
                self.current_midi_path, notes, self.current_processed_tracks, output_path
            )

            self.piano_roll_dirty = False
            self.piano_save_btn.setEnabled(False)
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

    def _select_play_list_item_by_path(self, path: str):
        for i in range(self.play_listbox.count()):
            item = self.play_listbox.item(i)
            if item.data(Qt.UserRole) == path:
                self.play_listbox.setCurrentRow(i)
                return

    def on_play_progress(self, elapsed: float):
        """播放线程上报的实时播放进度，驱动铺面播放线"""
        if (
            self.currently_playing_midi_path
            and self.current_midi_path == self.currently_playing_midi_path
        ):
            self.piano_roll.set_playhead(elapsed)

    def toggle_play(self):
        """切换播放状态"""
        if self.is_playing:
            self.stop_playing()
        else:
            self.start_playing()

    def start_playing(self):
        """开始播放"""
        current_item = self.play_listbox.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个播放文件")
            return

        if not self.current_midi_path or current_item.data(Qt.UserRole) != self.current_midi_path:
            QMessageBox.warning(self, "警告", "请先在铺面中打开要播放的曲目")
            return

        try:
            filename = os.path.basename(self.current_midi_path)

            # 基于铺面当前状态（含编辑）与乐器音域框范围，在内存中生成播放数据
            notes = self.piano_roll.get_notes()
            low_pitch, high_pitch = self.piano_roll.get_instrument_range()
            # 移调量：只用「最低映射」作锚点，把框体范围内的音符整体移调到目标按键范围
            target_low_pitch = self.range_low_combo.itemData(self.range_low_combo.currentIndex())
            transpose = target_low_pitch - low_pitch

            converter = MidiToKeysConverter()
            result = converter.regenerate_playback_from_notes(
                notes, pitch_range=(low_pitch, high_pitch), transpose=transpose
            )
            playback_data = result["playback_data"]

            if not playback_data:
                QMessageBox.warning(self, "警告", "当前乐器音域范围内没有可播放的音符")
                return

            data = {
                "type": "jx3_piano_complete",
                "version": "2.0",
                "filename": os.path.splitext(filename)[0],
                "transpose": self.current_transpose,
                "processed_tracks": self.current_processed_tracks,
                "playback_data": playback_data,
                "statistics": result["statistics"],
            }

            self.log("")
            self.log(f"▶️ 开始播放: {filename}")

            # 使用新的播放线程（直接播放内存数据，不落盘）
            self.play_thread = PlayThread(data)
            self.play_thread.log_signal.connect(self.log)
            self.play_thread.progress_signal.connect(self.on_play_progress)
            self.play_thread.finished_signal.connect(self.on_play_finished)
            self.play_thread.start()

            self.is_playing = True
            self.currently_playing_midi_path = self.current_midi_path
            self.piano_roll.set_read_only(True)

            # 更新按钮
            self.play_btn.setText("⏹️ 停止(ESC)")
            self.play_btn.setObjectName("stopBtn")
            self.play_btn.setStyleSheet("")  # 重新应用样式

        except Exception as e:
            self.log(f"❌ 播放失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"播放失败：{str(e)}")

    def stop_playing(self):
        """停止播放"""
        self.log("🛑 正在停止播放...")

        # 停止新的播放线程
        if hasattr(self, "play_thread") and self.play_thread:
            try:
                self.play_thread.stop()
                if self.play_thread.isRunning():
                    self.play_thread.wait(3000)  # 等待最多3秒
                self.play_thread = None
            except:
                pass

        self.is_playing = False
        self.currently_playing_midi_path = None
        self.piano_roll.set_read_only(False)
        self.piano_roll.set_playhead(None)

        # 更新按钮
        self.play_btn.setText("▶️ 播放")
        self.play_btn.setObjectName("playBtn")
        self.play_btn.setStyleSheet("")  # 重新应用样式

        self.log("⏹️ 播放已停止")

    def closeEvent(self, event):
        """程序关闭事件"""
        if self.piano_roll_dirty:
            if not self._confirm_discard_piano_changes():
                event.ignore()
                return
        if self.is_playing:
            self.stop_playing()
        event.accept()

    def on_play_finished(self, success: bool):
        """播放完成后的回调"""
        if self.is_playing:  # 只在确实在播放时才更新状态
            self.is_playing = False
            self.currently_playing_midi_path = None
            self.play_thread = None
            self.piano_roll.set_read_only(False)
            self.piano_roll.set_playhead(None)

            # 更新按钮
            self.play_btn.setText("▶️ 播放")
            self.play_btn.setObjectName("playBtn")
            self.play_btn.setStyleSheet("")  # 重新应用样式

            if success:
                self.log("✅ 播放完成")
            else:
                self.log("⏹️ 播放被中断")


def is_admin():
    """检查程序是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """请求以管理员权限重新运行程序"""
    if is_admin():
        return True
    else:
        try:
            # 获取当前脚本路径
            if getattr(sys, "frozen", False):
                # 如果是打包后的exe
                script = sys.executable
                params = " ".join(sys.argv[1:])
            else:
                # 如果是Python脚本
                script = sys.argv[0]
                params = " ".join(sys.argv[1:])

            # 使用ShellExecute以管理员权限运行
            ctypes.windll.shell32.ShellExecuteW(None, "runas", script, params, None, 1)
            return False
        except:
            return False


def main():
    """主程序入口"""
    # 检查管理员权限
    if not is_admin():
        # 如果不是管理员权限，请求重新以管理员权限运行
        if run_as_admin():
            return  # 如果已经是管理员权限，继续执行
        else:
            sys.exit(1)  # 重新启动程序或用户拒绝，退出当前实例

    # 检查并创建必要的文件夹
    from build_music import ensure_directories_exist

    ensure_directories_exist()

    app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("剑网三自动演奏工具")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Jx3 Piano")

    # 设置全局字体
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)

    # 创建并显示主窗口
    window = MidiConverterGUI()
    window.show()

    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
