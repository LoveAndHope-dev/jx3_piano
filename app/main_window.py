"""主窗口：只保留装配与跨页协调。"""

from app.common import *  # noqa: F401,F403
from app.history import HistoryMixin
from app.playback import PlaybackMixin
from app.ui.log_page import LogPageMixin
from app.ui.piano_page import PianoPageMixin
from app.ui.playlist_page import PlaylistPageMixin
from app.ui.theme import build_stylesheet


class MidiConverterGUI(
    HistoryMixin,
    PlaybackMixin,
    PianoPageMixin,
    PlaylistPageMixin,
    LogPageMixin,
    QMainWindow,
):
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
        """应用 Ant Design 深色主题（令牌集中在 app/ui/theme.py）。"""
        self.setStyleSheet(build_stylesheet())

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

    def closeEvent(self, event):
        """程序关闭事件"""
        if self.piano_roll_dirty:
            if not self._confirm_discard_piano_changes():
                event.ignore()
                return
        if self.play_thread is not None:
            self.stop_playing()
            if self.play_thread is not None and self.play_thread.isRunning():
                event.ignore()
                return
        event.accept()
