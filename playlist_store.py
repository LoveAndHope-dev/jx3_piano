"""播放列表数据层。

只负责与磁盘打交道的可测试逻辑：隐藏记录、目录枚举、搜索过滤、排序、
唯一命名与空 MIDI 生成；GUI 只做展示与调用。
"""

import json
import os
from typing import List, Set, Tuple

import mido

HIDDEN_FILENAME = ".hidden_playlist.json"
MIDI_EXTENSIONS = (".mid", ".midi")

# (文件名, 绝对路径, 修改时间)
Entry = Tuple[str, str, float]


def load_hidden(midi_dir: str) -> Set[str]:
    """读取被移除曲目的文件名集合；文件缺失或损坏时返回空集合。"""
    path = os.path.join(midi_dir, HIDDEN_FILENAME)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return set()
    if not isinstance(data, list):
        return set()
    return {str(name) for name in data if isinstance(name, str)}


def save_hidden(midi_dir: str, names: Set[str]) -> None:
    """保存被移除曲目的文件名集合。"""
    os.makedirs(midi_dir, exist_ok=True)
    path = os.path.join(midi_dir, HIDDEN_FILENAME)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sorted(names), fh, ensure_ascii=False, indent=2)


def list_entries(midi_dir: str) -> List[Entry]:
    """列出目录下所有 MIDI 文件（不递归，忽略隐藏记录等非 MIDI 文件）。"""
    entries: List[Entry] = []
    if not os.path.isdir(midi_dir):
        return entries
    for name in os.listdir(midi_dir):
        if os.path.splitext(name)[1].lower() not in MIDI_EXTENSIONS:
            continue
        path = os.path.join(midi_dir, name)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        entries.append((name, path, mtime))
    return entries


def filter_entries(entries: List[Entry], query: str) -> List[Entry]:
    """按文件名子串过滤（不区分大小写）；空查询返回全部。"""
    needle = query.strip().lower()
    if not needle:
        return list(entries)
    return [entry for entry in entries if needle in entry[0].lower()]


def sort_entries(entries: List[Entry], mode: str) -> List[Entry]:
    """按名称升序（默认）或导入时间从新到旧排序；同时间用名称保证稳定。"""
    if mode == "mtime":
        return sorted(entries, key=lambda entry: (-entry[2], entry[0].lower()))
    return sorted(entries, key=lambda entry: entry[0].lower())


def unique_midi_name(midi_dir: str, base: str = "新建曲目") -> str:
    """返回不与现有文件冲突的 MIDI 文件名。"""
    candidate = f"{base}.mid"
    if not os.path.exists(os.path.join(midi_dir, candidate)):
        return candidate
    index = 2
    while os.path.exists(os.path.join(midi_dir, f"{base}_{index}.mid")):
        index += 1
    return f"{base}_{index}.mid"


def create_blank_midi(
    path: str, bpm: float = 120.0, time_signature: Tuple[int, int] = (4, 4)
) -> None:
    """生成一个空 MIDI：给定 BPM 与拍号、单个空音轨。"""
    if bpm <= 0:
        raise ValueError("BPM 必须大于 0")
    numerator, denominator = time_signature
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    track.append(
        mido.MetaMessage("set_tempo", tempo=int(round(60_000_000 / bpm)), time=0)
    )
    track.append(
        mido.MetaMessage(
            "time_signature", numerator=numerator, denominator=denominator, time=0
        )
    )
    track.append(mido.MetaMessage("end_of_track", time=0))
    mid.tracks.append(track)
    mid.save(path)
