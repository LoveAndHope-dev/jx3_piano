"""铺面资源文件：工作 MIDI 副本与 play_code JSON 的生成/读取。

播放改为从 JSON 直接取按键序列，避免每次点击「弹奏」都重新做一遍
音符→按键映射；同时保证生成的按键覆盖全部可映射音域，不再按黄色
映射框裁剪音符（这正是之前「吞音」的来源）。
"""

import json
import os
from typing import Dict, List, Optional

PLAYBACK_TYPE = "jx3_piano_complete"


def base_name(midi_path: str) -> str:
    return os.path.splitext(os.path.basename(midi_path))[0]


def edited_midi_path(midi_dir: str, name: str) -> str:
    return os.path.join(midi_dir, "edited", f"{name}.mid")


def play_code_path(play_code_dir: str, name: str) -> str:
    return os.path.join(play_code_dir, f"{name}.json")


def _first_playable_start(converter, notes: List[Dict], pitch_range, transpose: int):
    """返回第一个可发声音符的绝对起点；没有可发声音符时返回 None。"""
    low = pitch_range[0] - 1 if pitch_range else None
    high = pitch_range[1] + 1 if pitch_range else None
    for note in sorted(notes, key=lambda n: float(n.get("start", 0.0))):
        pitch = int(note["pitch"])
        if low is not None and not (low <= pitch <= high):
            continue
        sequence, _ = converter.midi_note_to_key_sequence(
            pitch + transpose, {"sharp": False, "flat": False}
        )
        if sequence:
            return float(note.get("start", 0.0))
    return None


def build_play_code_data(
    converter,
    notes: List[Dict],
    bpm: float,
    filename: str,
    pitch_range=None,
    transpose: int = 0,
) -> Dict:
    """由铺面音符生成 play_code 数据（按黄色框范围与移调生成）。

    playback_data 使用从 0 秒开始的绝对时间轴：若第一个可发音符不在 0 秒，
    先补一段前导延迟，保证按播放辅助线裁剪时不会多跳。
    """
    result = converter.regenerate_playback_from_notes(
        notes, pitch_range=pitch_range, transpose=transpose
    )
    playback_data = list(result["playback_data"])
    lead = _first_playable_start(converter, notes, pitch_range, transpose)
    if lead and lead > 0 and playback_data:
        playback_data = [round(lead, 3)] + playback_data
    return {
        "type": PLAYBACK_TYPE,
        "version": "2.0",
        "filename": filename,
        "bpm": float(bpm),
        "transpose": int(transpose),
        "timeline_offset": 0.0,
        "playback_data": playback_data,
        "notes": [dict(n) for n in notes],
        "statistics": result["statistics"],
    }


def write_play_code(path: str, data: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    os.replace(tmp, path)


def read_play_code(path: str) -> Optional[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("playback_data"), list):
        return None
    return data


def split_playback_at(playback_data: List, start_at: float) -> List:
    """裁掉 start_at 之前的按键与延时，返回从该位置播放的剩余序列。

    播放数据是没有时间戳的 [按键/延时, ...]；若起播点落在某个延时内部，
    把该延时未走完的剩余部分放回序列开头，避免后续按键提前于辅助线触发。
    """
    if start_at <= 0:
        return list(playback_data)
    elapsed = 0.0
    index = 0
    length = len(playback_data)
    while index < length:
        item = playback_data[index]
        if isinstance(item, (int, float)):
            duration = float(item)
            if elapsed >= start_at:
                break  # 该延时完整保留
            if elapsed + duration > start_at:
                remaining = round(elapsed + duration - start_at, 6)
                rest = list(playback_data[index + 1 :])
                return ([remaining] if remaining > 0 else []) + rest
            elapsed += duration
        elif elapsed >= start_at:
            break  # 按键正好落在起点或之后
        index += 1
    return list(playback_data[index:])
