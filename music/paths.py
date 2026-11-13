"""运行目录解析：MIDI 工作目录与 play_code 目录。"""

import os
import sys

# MIDI 文件存放目录（相对基础目录）
MID_DIR_PATH = "midi/"
# 生成的播放代码存放目录（相对基础目录）
PLAY_CODE_DIR = "play_code/"


def get_base_directory():
    """程序基础目录（exe 或项目根目录）。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # music/paths.py → 项目根
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_midi_dir_path():
    return os.path.join(get_base_directory(), "midi")


def get_play_code_dir_path():
    return os.path.join(get_base_directory(), "play_code")


def ensure_directories_exist():
    """确保 midi/ 与 play_code/ 目录存在。"""
    try:
        current_dir = get_base_directory()
        directories = [
            os.path.join(current_dir, "midi"),
            os.path.join(current_dir, "play_code"),
        ]

        created_count = 0
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                print(f"已创建文件夹: {directory}")
                created_count += 1
            else:
                print(f"文件夹已存在: {directory}")

        if created_count > 0:
            print(f"成功创建了 {created_count} 个文件夹")
        else:
            print("所有必要的文件夹都已存在")

    except Exception as e:
        print(f"创建文件夹时出现错误: {e}")

