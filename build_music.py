"""兼容门面：音乐处理实现位于 music/ 包。"""

import os
import sys
from typing import List, Optional, Tuple

from music.converter import (
    MidiToKeysConverter,
    get_chromatic_key_ladder,
    get_natural_key_ladder,
)
from music.midi_io import tempo_us_from_bpm
from music.paths import (
    MID_DIR_PATH,
    PLAY_CODE_DIR,
    ensure_directories_exist,
    get_base_directory,
    get_midi_dir_path,
    get_play_code_dir_path,
)

# 主逻辑（保持向后兼容）
def build_music(
    midi_file_path: str,
    track_nums: List[int] = None,
    transpose: int = None,
    log_callback=None,
) -> Optional[str]:
    """
    快速转换MIDI文件

    参数:
    midi_file_path: MIDI文件路径
    track_nums: 要处理的音轨编号列表，None为自动选择
    transpose: 移调半音数，None为自动选择
    log_callback: 日志回调函数（用于GUI）

    返回:
    转换成功时返回输出文件路径，失败时返回None
    """
    converter = MidiToKeysConverter(log_callback)
    ensure_directories_exist()
    result = converter.convert_midi(midi_file_path, track_nums, transpose)

    if result["success"]:
        return result["output_file"]
    else:
        return None


if __name__ == "__main__":
    # 检查并创建必要的文件夹
    ensure_directories_exist()

    # 测试代码
    midi_file = "我的祖国.mid"  # 替换为你的MIDI文件路径
    file_path = os.path.join(get_midi_dir_path(), midi_file)
    build_music(file_path, track_nums=[0, 1], transpose=None)
