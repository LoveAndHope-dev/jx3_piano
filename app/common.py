"""界面与流程模块共享的导入、常量和目录包装。

各 mixin 通过 `from app.common import *` 取得 Qt 控件、项目工具与常量，
避免每个模块重复维护一长串导入。
"""

import ctypes
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Optional

import mido

from PyQt5.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QThread,
    QTimer,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QTextCharFormat,
)
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

import music.paths as _paths
from app.workers.batch_import import BatchConversionWorker
from app.workers.play_thread import PlayThread
from build_music import (
    MID_DIR_PATH,
    PLAY_CODE_DIR,
    MidiToKeysConverter,
    build_music,
    get_natural_key_ladder,
)
from piano_roll import (
    PianoRollWidget,
    bpm_scale_factor,
    grid_seconds_for_bpm,
    playback_notes_from_position,
)
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


def get_midi_dir_path():
    """动态转发到 music.paths，便于测试整体替换目录。"""
    return _paths.get_midi_dir_path()


def get_play_code_dir_path():
    return _paths.get_play_code_dir_path()
