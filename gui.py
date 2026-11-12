import sys
import os
import shutil
import threading
import subprocess
import json
import time
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
    QLineEdit,
    QDoubleSpinBox,
)
from PyQt5.QtCore import (
    Qt,
    QThread,
    pyqtSignal,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QRect,
    QSize,
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

from play_assets import (
    base_name,
    build_play_code_data,
    edited_midi_path,
    play_code_path,
    read_play_code,
    write_play_code,
)
from playlist_store import (
    create_blank_midi,
    filter_entries,
    list_entries,
    sort_entries,
    unique_midi_name,
)
from piano_roll import (
    PianoRollWidget,
    bpm_scale_factor,
    grid_seconds_for_bpm,
    playback_notes_from_position,
)

# 铺面 BPM 的可编辑范围（控件本身允许更宽的输入，提交时再钳制）
MIN_PIANO_BPM = 20.0
MAX_PIANO_BPM = 300.0

# 量化下拉框选项 -> 传统音符时值分母（1/4 恒等于一拍，只依赖 BPM，不依赖拍号）
QUANTIZE_LABEL_TO_N = {
    "1/2": 2,
    "1/4": 4,
    "1/8": 8,
    "1/16": 16,
    "1/32": 32,
    "1/64": 64,
    "1/128": 128,
}


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
            success = self.player.play_from_data(
                self.data, start_at=float(self.data.get("start_at", 0.0))
            )

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
        self._playback_start_seconds = 0.0  # 本次播放的起点（播放辅助线位置）

        # 铺面编辑相关变量
        self.current_midi_path = None
        self.current_processed_tracks = []
        self.current_transpose = 0
        self.piano_roll_dirty = False
        self.current_bpm = 120.0
        self.current_time_signature = (4, 4)
        self.quantize_choice = "关闭"
        self._updating_bpm = False

        # 撤销 / 前进历史
        self._undo_stack = []
        self._redo_stack = []
        self._history_applying = False
        self._history_limit = 50
        self._history_baseline = None

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
                padding: 2px 12px;
                min-height: 22px;
                max-height: 26px;
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

            QFrame#controlPanel {
                border: 2px solid #34495E;
                border-radius: 10px;
                margin-top: 0px;
            }

            QLabel#panelTitle {
                padding: 2px 10px 2px 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498DB, stop:1 #2980B9);
                border-radius: 5px;
                color: white;
                font-weight: bold;
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

            QDoubleSpinBox {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(52, 73, 94, 0.8), stop:1 rgba(44, 62, 80, 0.8));
                border: 2px solid #34495E;
                border-radius: 6px;
                padding: 4px 8px;
                color: #ECF0F1;
                font-size: 13px;
                min-width: 50px;
            }

            QDoubleSpinBox:hover {
                border: 2px solid #3498DB;
            }

            QDoubleSpinBox:focus {
                border: 2px solid #3498DB;
            }

            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 0px;
                border: none;
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

        # 控制面板（标题行右侧放置窗口置顶按钮）
        control_group = QFrame()
        control_group.setObjectName("controlPanel")
        left_layout.addWidget(control_group)

        control_layout = QVBoxLayout(control_group)
        control_layout.setContentsMargins(10, 8, 10, 10)

        panel_header = QHBoxLayout()
        panel_title = QLabel("🎛️ 控制面板")
        panel_title.setObjectName("panelTitle")
        panel_header.addWidget(panel_title)
        panel_header.addStretch()

        self.topmost_btn = QPushButton("📌 置顶")
        self.topmost_btn.setObjectName("clearBtn")
        self.topmost_btn.setCheckable(True)
        self.topmost_btn.clicked.connect(self.toggle_topmost)
        panel_header.addWidget(self.topmost_btn)

        control_layout.addLayout(panel_header)

        # 按钮行1
        btn_row1 = QHBoxLayout()

        self.import_btn = QPushButton("📁 导入MIDI")
        self.import_btn.setObjectName("importBtn")
        self.import_btn.clicked.connect(self.import_midi_file)
        btn_row1.addWidget(self.import_btn)

        self.new_play_btn = QPushButton("➕ 新建")
        self.new_play_btn.setToolTip("新建一个空白 MIDI 并加入列表")
        self.new_play_btn.clicked.connect(self.on_new_play_item)
        btn_row1.addWidget(self.new_play_btn)

        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setObjectName("refreshBtn")
        self.refresh_btn.setToolTip("刷新列表")
        self.refresh_btn.clicked.connect(self.refresh_play_list)
        btn_row1.addWidget(self.refresh_btn)

        control_layout.addLayout(btn_row1)

        # 添加作者信息
        credit_label = QLabel("created by 66maer updated by Loveanope_Dev")
        credit_label.setObjectName("creditLabel")
        credit_label.setAlignment(Qt.AlignCenter)
        control_layout.addWidget(credit_label)

        # 播放列表组
        list_group = QGroupBox("🎼 播放列表")
        left_layout.addWidget(list_group)

        list_layout = QVBoxLayout(list_group)

        search_row = QHBoxLayout()
        self.play_search = QLineEdit()
        self.play_search.setPlaceholderText("搜索曲目…")
        self.play_search.textChanged.connect(self.refresh_play_list)
        self.play_sort_combo = QComboBox()
        self.play_sort_combo.addItem("名称", "name")
        self.play_sort_combo.addItem("导入时间", "mtime")
        self.play_sort_combo.currentIndexChanged.connect(self.refresh_play_list)
        search_row.addWidget(self.play_search, 1)
        search_row.addWidget(self.play_sort_combo)
        list_layout.addLayout(search_row)

        list_row = QHBoxLayout()
        self.play_listbox = QListWidget()
        self.play_listbox.itemSelectionChanged.connect(self.on_select_play_file)
        self.play_listbox.currentItemChanged.connect(self.on_piano_roll_selection_changed)

        list_row.addWidget(self.play_listbox, 1)
        list_layout.addLayout(list_row)

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

        action_row = QHBoxLayout()
        title_label = QLabel("🎼 铺面编辑")
        title_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        action_row.addWidget(title_label)
        action_row.addStretch()
        piano_layout.addLayout(action_row)

        toolbar = QHBoxLayout()
        self.play_btn = QPushButton("▶️ 弹奏")
        self.play_btn.setObjectName("playBtn")
        self.play_btn.clicked.connect(self.toggle_play)
        toolbar.addWidget(self.play_btn)

        self.arpeggiate_btn = QPushButton("🪄 曲谱优化")
        self.arpeggiate_btn.setToolTip("对选中音符做琶音整理（1/32 拍展开）")
        self.arpeggiate_btn.setEnabled(False)
        self.arpeggiate_btn.clicked.connect(self.on_arpeggiate_clicked)
        toolbar.addWidget(self.arpeggiate_btn)

        self.piano_dirty_label = QLabel("")
        toolbar.addWidget(self.piano_dirty_label)

        self.piano_save_btn = QPushButton("💾 保存")
        self.piano_save_btn.setEnabled(False)
        self.piano_save_btn.clicked.connect(self.save_piano_roll)
        toolbar.addWidget(self.piano_save_btn)

        # 演奏/编辑模式与键位映射：第一行到「演奏最高键位映射」结束
        self.range_toggle_btn = QPushButton("🎹 演奏模式")
        self.range_toggle_btn.setCheckable(True)
        self.range_toggle_btn.setEnabled(False)
        self.range_toggle_btn.clicked.connect(self.on_range_toggle_clicked)
        toolbar.addWidget(self.range_toggle_btn)

        toolbar.addWidget(QLabel("演奏最低键位映射:"))
        self.range_low_combo = QComboBox()
        self.range_low_combo.setEnabled(False)
        toolbar.addWidget(self.range_low_combo)

        toolbar.addWidget(QLabel("演奏最高键位映射:"))
        self.range_high_combo = QComboBox()
        self.range_high_combo.setEnabled(False)
        toolbar.addWidget(self.range_high_combo)
        # 行尾弹性空白吸收多余宽度，保证所有操作贴左且位置不随窗口宽度漂移
        toolbar.addStretch()

        piano_layout.addLayout(toolbar)

        toolbar_row2 = QHBoxLayout()
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

        toolbar_row2.addWidget(QLabel("量化:"))
        self.quantize_combo = QComboBox()
        self.quantize_combo.setEnabled(False)
        for label in ("关闭", "1/2", "1/4", "1/8", "1/16", "1/32", "1/64", "1/128"):
            self.quantize_combo.addItem(label)
        self.quantize_combo.currentTextChanged.connect(self.on_quantize_combo_changed)
        toolbar_row2.addWidget(self.quantize_combo)

        toolbar_row2.addWidget(QLabel("BPM:"))
        self.bpm_spin = QDoubleSpinBox()
        self.bpm_spin.setRange(0.0, 10000.0)
        self.bpm_spin.setDecimals(1)
        self.bpm_spin.setSingleStep(1.0)
        self.bpm_spin.setKeyboardTracking(False)
        self.bpm_spin.setValue(120.0)
        self.bpm_spin.setEnabled(False)
        self.bpm_spin.valueChanged.connect(self.on_bpm_changed)
        toolbar_row2.addWidget(self.bpm_spin)
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
            self.piano_save_btn.setEnabled(False)
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
        self.piano_save_btn.setEnabled(False)
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
        self.piano_save_btn.setEnabled(True)
        self._update_piano_dirty_indicator()
        self._record_history()

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
            self.piano_save_btn.setEnabled(is_dirty)
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
        self.play_btn.setEnabled(play_mode or self.is_playing)
        self.arpeggiate_btn.setEnabled(
            bool(self.current_midi_path) and not play_mode and not self.is_playing
        )

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
        self.piano_save_btn.setEnabled(False)
        self._update_piano_dirty_indicator()
        self._set_range_controls_enabled(False)
        self.piano_stack.setCurrentWidget(self.piano_placeholder)
        self._undo_stack = []
        self._redo_stack = []
        self._history_baseline = None

    def on_play_progress(self, elapsed: float):
        """播放线程上报的实时播放进度，驱动铺面播放线"""
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
            self.play_thread = PlayThread(data)
            self.play_thread.log_signal.connect(self.log)
            self.play_thread.progress_signal.connect(self.on_play_progress)
            self.play_thread.finished_signal.connect(self.on_play_finished)
            self.play_thread.start()

            self.is_playing = True
            self.currently_playing_midi_path = self.current_midi_path
            self._sync_roll_mode()
            self.piano_roll.set_playhead_locked(True)
            self._sync_bpm_enabled()

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
        self._sync_roll_mode()
        self.piano_roll.set_playhead_locked(False)
        self.piano_roll.set_playhead(None)
        self._sync_bpm_enabled()

        # 更新按钮
        self.play_btn.setText("▶️ 弹奏")
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
            self._sync_roll_mode()
            self.piano_roll.set_playhead_locked(False)
            self.piano_roll.set_playhead(None)
            self._sync_bpm_enabled()

            # 更新按钮
            self.play_btn.setText("▶️ 弹奏")
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
