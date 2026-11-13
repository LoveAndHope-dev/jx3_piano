"""MIDI 音符读写。"""

import os
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import mido


class MidiIoMixin:
    def write_notes_to_midi(
        self,
        source_midi_path: str,
        notes: List[Dict[str, Any]],
        processed_tracks: List[int],
        output_path: str,
        tempo_bpm: Optional[float] = None,
    ) -> None:
        """
        把（可能已被铺面编辑器修改的）音符列表另存为一个新的 MIDI 文件。
        只重写 processed_tracks 涉及的音轨的音符内容，该音轨内原有的非
        note_on/note_off 事件（音轨名、乐器、原有 tempo 等）原样保留在新
        音轨开头；未被处理的其他音轨与文件级 ticks_per_beat 完全不变。

        tempo_bpm: 传入时把文件中所有 tempo 事件统一改为该 BPM（缺失则在 0 号
        音轨插入），并用新 tempo 把音符秒数换算成 tick，使音符拍位保持不变；
        为 None 时沿用源文件的基础 tempo。

        注：这里直接按 BPM 换算 tempo 微秒，而没有复用 piano_roll 的同名函数，
        因为 piano_roll 已导入本模块，反向导入会形成循环依赖。
        """
        mid = mido.MidiFile(source_midi_path)

        if tempo_bpm is not None:
            tempo = tempo_us_from_bpm(tempo_bpm)
            replaced = False
            for track in mid.tracks:
                for msg in track:
                    if msg.type == "set_tempo":
                        msg.tempo = tempo
                        replaced = True
            if not replaced:
                mid.tracks[0].insert(
                    0, mido.MetaMessage("set_tempo", tempo=tempo, time=0)
                )
        else:
            tempo = self._scan_base_tempo(mid)

        processed_set = set(processed_tracks)
        fallback_track = processed_tracks[0] if processed_tracks else 0

        notes_by_track: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for note in notes:
            track_idx = int(note.get("track", 0))
            # 音符所在音轨不在本次处理范围内（例如铺面新增音符时取到了过期的默认音轨）
            # 时归入第一个已处理音轨，避免静默丢弃
            if track_idx not in processed_set:
                track_idx = fallback_track
            notes_by_track[track_idx].append(note)

        for track_idx in processed_tracks:
            if track_idx >= len(mid.tracks):
                continue

            original_track = mid.tracks[track_idx]
            meta_messages = [
                msg
                for msg in original_track
                if msg.type not in ("note_on", "note_off", "end_of_track")
            ]

            new_track = mido.MidiTrack()
            for msg in meta_messages:
                new_track.append(msg.copy(time=0))

            events: List[Tuple[int, Any]] = []
            for note in sorted(
                notes_by_track.get(track_idx, []), key=lambda n: n.get("start", 0.0)
            ):
                pitch = int(note["pitch"])
                channel = int(note.get("channel", 0))
                velocity = max(1, min(127, int(note.get("velocity", 100))))
                start_seconds = float(note.get("start", 0.0))
                duration_seconds = max(float(note.get("duration", 0.05)), 0.02)

                start_tick = int(
                    round(mido.second2tick(start_seconds, mid.ticks_per_beat, tempo))
                )
                end_tick = int(
                    round(
                        mido.second2tick(
                            start_seconds + duration_seconds, mid.ticks_per_beat, tempo
                        )
                    )
                )
                events.append(
                    (start_tick, mido.Message("note_on", note=pitch, velocity=velocity, channel=channel))
                )
                events.append(
                    (end_tick, mido.Message("note_off", note=pitch, velocity=0, channel=channel))
                )

            events.sort(key=lambda e: e[0])
            last_tick = 0
            for tick, msg in events:
                delta = max(0, tick - last_tick)
                new_track.append(msg.copy(time=delta))
                last_tick = tick

            new_track.append(mido.MetaMessage("end_of_track", time=0))
            mid.tracks[track_idx] = new_track

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        mid.save(output_path)

    def extract_notes(
        self,
        midi_file_path: str,
        track_filter: List[int] = None,
        channel_filter: List[int] = None,
        transpose: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        从MIDI文件直接解析出结构化音符列表（用于铺面编辑），保留独立的
        音高/起始时间/时长信息，而不是像 convert_to_playback_data 那样
        压缩成按键+延迟序列。

        返回: [{"id", "track", "channel", "pitch", "start", "duration",
                "velocity", "mapped"}, ...]，按 start 时间升序排列。
        """
        mid = mido.MidiFile(midi_file_path)
        notes: List[Dict[str, Any]] = []
        tempo = self._scan_base_tempo(mid)

        for track_idx, track in enumerate(mid.tracks):
            if track_filter and track_idx not in track_filter:
                continue

            track_time = 0.0
            active: Dict[Tuple[int, int], Tuple[float, int]] = {}

            for msg in track:
                if msg.type == "set_tempo":
                    tempo = msg.tempo

                track_time += mido.tick2second(msg.time, mid.ticks_per_beat, tempo)

                if msg.type == "note_on" and msg.velocity > 0:
                    if channel_filter and msg.channel not in channel_filter:
                        continue
                    active[(msg.channel, msg.note)] = (track_time, msg.velocity)
                elif msg.type == "note_off" or (
                    msg.type == "note_on" and msg.velocity == 0
                ):
                    if channel_filter and msg.channel not in channel_filter:
                        continue
                    key = (msg.channel, msg.note)
                    if key in active:
                        start_time, velocity = active.pop(key)
                        notes.append(
                            self._build_note_entry(
                                track_idx,
                                msg.channel,
                                msg.note,
                                start_time,
                                track_time,
                                velocity,
                                transpose,
                            )
                        )

            # 轨道结束时仍未收到 note_off 的音符，以轨道末尾时间作为结束
            for (channel, note), (start_time, velocity) in active.items():
                notes.append(
                    self._build_note_entry(
                        track_idx,
                        channel,
                        note,
                        start_time,
                        track_time,
                        velocity,
                        transpose,
                    )
                )

        notes.sort(key=lambda n: (n["start"], n["track"]))
        for i, note in enumerate(notes):
            note["id"] = i

        return notes

    def _build_note_entry(
        self,
        track_idx: int,
        channel: int,
        note: int,
        start_time: float,
        end_time: float,
        velocity: int,
        transpose: int,
    ) -> Dict[str, Any]:
        """构造单个音符条目（内部辅助方法）"""
        duration = max(end_time - start_time, 0.02)
        transposed_note = self.transpose_note(note, transpose)
        temp_state = {"sharp": False, "flat": False}
        key_sequence, _ = self.midi_note_to_key_sequence(transposed_note, temp_state)
        return {
            "id": 0,  # 由调用方在排序后重新分配
            "track": track_idx,
            "channel": channel,
            "pitch": transposed_note,
            "start": round(start_time, 3),
            "duration": round(duration, 3),
            "velocity": velocity,
            "mapped": bool(key_sequence),
        }


def tempo_us_from_bpm(bpm: float) -> int:
    """BPM → MIDI tempo（微秒/拍），四舍五入到整数。"""
    if bpm <= 0:
        raise ValueError("BPM 必须大于 0")
    return int(round(60_000_000 / float(bpm)))
