"""调用项目内 `arpeggiate.py` 脚本，对铺面选中的音符做 1/32 拍琶音展开。

脚本以 MIDI tick 工作，因此这里把选中音符写成临时 MIDI（每个音符一条独立
音轨，便于逐条回读结果），原样调用脚本的 `main(src, dst)`，再把输出换算回秒。
"""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
from typing import Dict, Iterable, List, Tuple

import mido

import arpeggiate

# 与 arpeggiate.py 注释中的换算一致：1/32 拍 = ticks_per_beat / 32 = 12 tick
TICKS_PER_BEAT = 384
VELOCITY = 64


def arpeggiate_notes(
    notes: List[Dict], selected_ids: Iterable[int], seconds_per_beat: float
) -> List[Dict]:
    """返回新的音符列表：选中音符按脚本展开，未选中原样保留。

    被脚本去重的音符（同音高同起点）会从结果中移除；脚本抛出异常时异常向上传递，
    调用方据此保持铺面不变。
    """
    result = [dict(note) for note in notes]
    selected_set = set(selected_ids)
    if not selected_set or seconds_per_beat <= 0:
        return result

    selected = [n for n in result if n.get("id") in selected_set]
    if not selected:
        return result

    with tempfile.TemporaryDirectory(prefix="jx3_arpeggiate_") as temp_dir:
        src = os.path.join(temp_dir, "input.mid")
        dst = os.path.join(temp_dir, "output.mid")
        _write_input_midi(src, selected, seconds_per_beat)
        # windowed 打包下 sys.stdout / sys.stderr 为 None，脚本的 print 需要兜底
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            arpeggiate.main(src, dst)
        processed = _read_output_midi(dst, selected, seconds_per_beat)

    updated: List[Dict] = []
    for note in result:
        if note.get("id") not in selected_set:
            updated.append(note)
            continue
        replacement = processed.get(note["id"])
        if replacement is None:
            continue  # 被脚本去重移除
        note["start"], note["duration"] = replacement
        updated.append(note)
    return updated


def _write_input_midi(path: str, selected: List[Dict], seconds_per_beat: float) -> None:
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    for note in selected:
        start_tick = max(
            0, int(round(float(note["start"]) / seconds_per_beat * TICKS_PER_BEAT))
        )
        duration_tick = max(
            1, int(round(float(note["duration"]) / seconds_per_beat * TICKS_PER_BEAT))
        )
        track = mido.MidiTrack()
        track.append(
            mido.Message(
                "note_on", note=int(note["pitch"]), velocity=VELOCITY, time=start_tick
            )
        )
        track.append(
            mido.Message(
                "note_off", note=int(note["pitch"]), velocity=0, time=duration_tick
            )
        )
        midi.tracks.append(track)
    midi.save(path)


def _read_output_midi(
    path: str, selected: List[Dict], seconds_per_beat: float
) -> Dict[int, Tuple[float, float]]:
    midi = mido.MidiFile(path)
    if len(midi.tracks) != len(selected):
        raise ValueError(
            f"脚本输出音轨数量不匹配：{len(midi.tracks)} != {len(selected)}"
        )
    processed: Dict[int, Tuple[float, float]] = {}
    for note, track in zip(selected, midi.tracks):
        parsed, _events = arpeggiate.extract_notes(track)
        if not parsed:
            continue
        first = parsed[0]
        start = first["on"] / TICKS_PER_BEAT * seconds_per_beat
        duration = (first["off"] - first["on"]) / TICKS_PER_BEAT * seconds_per_beat
        processed[note["id"]] = (round(start, 6), round(max(duration, 0.0), 6))
    return processed
