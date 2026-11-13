"""MidiToKeysConverter：组合各职责 mixin，公开方法保持不变。"""

from typing import List, Tuple

from music.analysis import AnalysisMixin
from music.cli import CliMixin
from music.mapping import MappingMixin
from music.midi_io import MidiIoMixin
from music.playback import PlaybackMixin

# 一个八度内的黑键相对半音位置（以C为0），与 piano_roll 的黑键口径一致
_LADDER_BLACK_KEY_OFFSETS = {1, 3, 6, 8, 10}


class MidiToKeysConverter(
    MappingMixin,
    AnalysisMixin,
    MidiIoMixin,
    PlaybackMixin,
    CliMixin,
):
    def __init__(self, log_callback=None):
        """
        初始化转换器
        log_callback: 用于GUI日志输出的回调函数
        """
        self.log_callback = log_callback

        # 标准音符映射 - 只映射自然音符（白键）
        # 标准中央C (C4) = MIDI 60
        self.base_note_mapping = {
            # 倍低音域 1234567
            36: "Z",  # 倍低1 (C2)
            38: "X",  # 倍低2 (D2)
            40: "C",  # 倍低3 (E2)
            41: "V",  # 倍低4 (F2)
            43: "B",  # 倍低5 (G2)
            45: "N",  # 倍低6 (A2)
            47: "M",  # 倍低7 (B2)
            # 低音域 1234567
            48: "A",  # 低1 (C3)
            50: "S",  # 低2 (D3)
            52: "D",  # 低3 (E3)
            53: "F",  # 低4 (F3)
            55: "G",  # 低5 (G3)
            57: "H",  # 低6 (A3)
            59: "J",  # 低7 (B3)
            # 中音域 1234567
            60: "Q",  # 中1 (C4)
            62: "W",  # 中2 (D4)
            64: "E",  # 中3 (E4)
            65: "R",  # 中4 (F4)
            67: "T",  # 中5 (G4)
            69: "Y",  # 中6 (A4)
            71: "U",  # 中7 (B4)
            # 高音域 1234567
            72: "1",  # 高1 (C5)
            74: "2",  # 高2 (D5)
            76: "3",  # 高3 (E5)
            77: "4",  # 高4 (F5)
            79: "5",  # 高5 (G5)
            81: "6",  # 高6 (A5)
            83: "7",  # 高7 (B5)
        }

        # 半音映射表（升号音符）
        self.sharp_notes = {
            # 倍低音域
            37: (36, True),  # C#2 -> 倍低1#
            39: (38, True),  # D#2 -> 倍低2#
            42: (41, True),  # F#2 -> 倍低4#
            44: (43, True),  # G#2 -> 倍低5#
            46: (45, True),  # A#2 -> 倍低6#
            # 低音域
            49: (48, True),  # C#3 -> 低1#
            51: (50, True),  # D#3 -> 低2#
            54: (53, True),  # F#3 -> 低4#
            56: (55, True),  # G#3 -> 低5#
            58: (57, True),  # A#3 -> 低6#
            # 中音域
            61: (60, True),  # C#4 -> 中1#
            63: (62, True),  # D#4 -> 中2#
            66: (65, True),  # F#4 -> 中4#
            68: (67, True),  # G#4 -> 中5#
            70: (69, True),  # A#4 -> 中6#
            # 高音域
            73: (72, True),  # C#5 -> 高1#
            75: (74, True),  # D#5 -> 高2#
            78: (77, True),  # F#5 -> 高4#
            80: (79, True),  # G#5 -> 高5#
            82: (81, True),  # A#5 -> 高6#
            # 超出 28 键最高实体键的边界半音（音域框上边界向外扩 1 个半音时可达）
            84: (83, True),  # C6 -> 高7#
        }

        # 特殊功能键
        self.special_keys = {
            "sharp": "+",  # 升半音
            "flat": "-",  # 降半音
            "harmonic": "shift",  # 泛音
            "trill": "ctrl",  # 轮指
            "slide_up": "up",  # 上滑
            "slide_down": "down",  # 下滑
        }


def get_natural_key_ladder() -> List[Tuple[int, str]]:
    """
    返回覆盖钢琴全部88键（MIDI 21~108）范围内全部自然音位置的键位映射，
    按 MIDI 音高升序排列，供「最低映射/最高映射」下拉框使用（代表 28 个
    游戏实际按键身份，黑键没有对应的实体按键，因此不枚举在这里）。
    其中 MIDI 36~83 的 28 个位置为游戏实际可用按键，标签取自单一数据来源
    MidiToKeysConverter.base_note_mapping（避免出现第二份不一致的副本）；
    其余超出游戏 28 键映射范围的自然音位置只作为音域框可框选的边界，
    标签使用标准音名（如 A0、C1），取自 get_note_name。
    """
    converter = MidiToKeysConverter()
    ladder = []
    for pitch in range(21, 109):
        if (pitch % 12) in _LADDER_BLACK_KEY_OFFSETS:
            continue
        label = converter.base_note_mapping.get(pitch)
        if label is None:
            label = converter.get_note_name(pitch)
        ladder.append((pitch, label))
    return ladder


def get_chromatic_key_ladder() -> List[Tuple[int, str]]:
    """
    返回钢琴全部 88 键（MIDI 21~108）范围内每一个半音（含黑键）的键位映射，
    按 MIDI 音高升序排列，供乐器音域框本身的拖动吸附/渲染使用——音域框代表
    歌曲实际音高内容，不受限于 28 个游戏实体按键，需要精确到任意半音。
    标签统一使用标准音名（如 C4、C#4），取自 get_note_name，与
    get_natural_key_ladder（供下拉框使用的 52 个自然音、游戏按键标签）是
    两套不同用途的阶梯，互不影响。
    """
    converter = MidiToKeysConverter()
    return [(pitch, converter.get_note_name(pitch)) for pitch in range(21, 109)]
