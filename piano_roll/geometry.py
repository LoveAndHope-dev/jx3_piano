"""铺面几何、时间轴换算与音符数学（常量与纯函数）。"""

import math
from typing import Dict, List, Optional, Set, Tuple

from PyQt5.QtGui import QColor

from build_music import tempo_us_from_bpm


MIN_PITCH = 21  # A0
MAX_PITCH = 108  # C8
PITCH_COUNT = MAX_PITCH - MIN_PITCH + 1  # 88

ROW_HEIGHT = 10
PIXELS_PER_SECOND = 70
DEFAULT_NOTE_DURATION = 0.4
MIN_NOTE_DURATION = 0.05
RESIZE_MARGIN = 6.0
DEFAULT_NUDGE_SECONDS = 0.1
MIN_SCENE_SECONDS = 10.0
TRAILING_PADDING_SECONDS = 5.0
CLICK_DRAG_THRESHOLD = 4.0
KEYBOARD_WIDTH = 30
MIN_MEASURE_SECONDS = 0.05  # 拍号/BPM 异常导致小节过短时的安全下限，避免画出海量小节线

# 横向缩放
MIN_PIXELS_PER_SECOND = 10.0
MAX_PIXELS_PER_SECOND = 600.0
ZOOM_STEP_FACTOR = 1.25

# 播放起点过滤的浮点比较容差
PLAYHEAD_EPSILON = 1e-6

# 顶部拍数标尺高度（像素）
RULER_HEIGHT = 28

RANGE_FILL_COLOR = QColor(255, 196, 0, 110)
RANGE_BORDER_COLOR = QColor(255, 214, 10, 235)
SELECT_RECT_FILL_COLOR = QColor(244, 208, 63, 40)
SELECT_RECT_BORDER_COLOR = QColor(244, 208, 63, 220)
SECOND_LINE_COLOR = QColor("#25313D")
MEASURE_LINE_COLOR = QColor("#55708A")

# 一个八度内的黑键相对半音位置（以C为0）
_BLACK_KEY_OFFSETS = {1, 3, 6, 8, 10}


def _is_black_key(pitch: int) -> bool:
    return (pitch % 12) in _BLACK_KEY_OFFSETS


def pasted_starts(clipboard: List[Dict], anchor: float) -> List[float]:
    """剪贴板音符按最早 start 对齐 anchor（秒）后的起始时间列表；不修改输入。"""
    if not clipboard:
        return []
    base = min(float(n.get("start", 0.0)) for n in clipboard)
    return [max(0.0, float(anchor) + float(n.get("start", 0.0)) - base) for n in clipboard]


def octave_shift_pitches(
    notes: List[Dict], selected_ids: Set[int], delta: int
) -> Dict[int, int]:
    """按 delta 半音整体移动选中音符；新音高超出 A0～C8 的音符保持原音高。"""
    targets: Dict[int, int] = {}
    for note in notes:
        note_id = note.get("id")
        if note_id not in selected_ids:
            continue
        pitch = int(note["pitch"])
        target = pitch + delta
        targets[note_id] = target if MIN_PITCH <= target <= MAX_PITCH else pitch
    return targets


def playback_notes_from_position(notes: List[Dict], playhead: float) -> List[Dict]:
    """只保留起始时间不早于 playhead 的音符，并把 start 平移到相对时间。"""
    result: List[Dict] = []
    for note in notes:
        start = float(note.get("start", 0.0))
        if start >= playhead - PLAYHEAD_EPSILON:
            cloned = dict(note)
            cloned["start"] = max(0.0, start - playhead)
            result.append(cloned)
    return result


def first_playable_start(
    notes: List[Dict], pitch_range: Optional[Tuple[int, int]] = None
) -> float:
    """返回参与播放的第一个音符的相对起始时间；无音符时返回 0。"""
    low = pitch_range[0] - 1 if pitch_range else None
    high = pitch_range[1] + 1 if pitch_range else None
    starts = [
        float(n.get("start", 0.0))
        for n in notes
        if low is None or low <= int(n["pitch"]) <= high
    ]
    return min(starts, default=0.0)


def clamp_pixels_per_second(value: float) -> float:
    return max(MIN_PIXELS_PER_SECOND, min(MAX_PIXELS_PER_SECOND, float(value)))


def anchored_scroll_value(anchor_time: float, screen_x: float, pixels_per_second: float) -> float:
    """缩放后应设置的横向滚动值（像素），使 anchor_time 仍落在屏幕 screen_x 处。"""
    return max(0.0, float(anchor_time) * float(pixels_per_second) - float(screen_x))


def bpm_scale_factor(old_bpm: float, new_bpm: float) -> float:
    """旧/新 BPM 的时间缩放因子；任一 BPM 非正时抛 ValueError。"""
    if old_bpm <= 0 or new_bpm <= 0:
        raise ValueError("BPM 必须大于 0")
    return float(old_bpm) / float(new_bpm)


def grid_seconds_for_bpm(bpm: float, numerator: int, denominator: int) -> Tuple[float, float]:
    """返回 (每小节秒数, 每拍秒数)；拍长 = 60/BPM * 4/分母。"""
    if bpm <= 0:
        raise ValueError("BPM 必须大于 0")
    beat_seconds = (60.0 / float(bpm)) * (4.0 / float(denominator))
    return beat_seconds * int(numerator), beat_seconds


def scaled_note_times(notes: List[Dict], factor: float) -> List[Dict]:
    """返回音符浅拷贝（音符为扁平字典），start 与 duration 乘以 factor；不修改输入。"""
    result: List[Dict] = []
    for note in notes:
        cloned = dict(note)
        cloned["start"] = float(note.get("start", 0.0)) * factor
        cloned["duration"] = float(note.get("duration", 0.0)) * factor
        result.append(cloned)
    return result
