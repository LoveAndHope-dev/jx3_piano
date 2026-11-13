"""MIDI 文件分析、速度/拍号与自动选轨。"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import mido


class AnalysisMixin:
    def analyze_midi_file(self, midi_file_path: str) -> dict:
        """分析MIDI文件的详细信息，用于调试"""
        try:
            mid = mido.MidiFile(midi_file_path)
        except Exception as e:
            return {"error": f"无法读取MIDI文件: {e}"}

        analysis = {
            "文件信息": {
                "音轨数量": len(mid.tracks),
                "时间分辨率": mid.ticks_per_beat,
                "文件类型": mid.type,
                "总时长": mid.length,
            },
            "音轨详情": [],
            "音符统计": defaultdict(int),
            "音域分析": {"最低音": 127, "最高音": 0, "未映射音符": set()},
        }

        for i, track in enumerate(mid.tracks):
            track_info = {
                "音轨号": i,
                "消息数量": len(track),
                "音符事件": 0,
                "程序变更": [],
                "音轨名称": None,
                "乐器名称": None,
            }

            for msg in track:
                if msg.type == "track_name":
                    track_info["音轨名称"] = msg.name
                elif msg.type == "program_change":
                    track_info["程序变更"].append(
                        f"通道{msg.channel}: 乐器{msg.program}"
                    )
                elif msg.type == "instrument_name":
                    track_info["乐器名称"] = msg.name
                elif msg.type == "note_on" and msg.velocity > 0:
                    track_info["音符事件"] += 1
                    analysis["音符统计"][msg.note] += 1
                    analysis["音域分析"]["最低音"] = min(
                        analysis["音域分析"]["最低音"], msg.note
                    )
                    analysis["音域分析"]["最高音"] = max(
                        analysis["音域分析"]["最高音"], msg.note
                    )
                    temp_state = {"sharp": False, "flat": False}
                    key_sequence, _ = self.midi_note_to_key_sequence(
                        msg.note, temp_state
                    )
                    if not key_sequence:
                        analysis["音域分析"]["未映射音符"].add(msg.note)

            analysis["音轨详情"].append(track_info)

        # 转换未映射音符为可读格式
        analysis["音域分析"]["未映射音符"] = [
            f"{note}({self.get_note_name(note)})"
            for note in sorted(analysis["音域分析"]["未映射音符"])
        ]

        return analysis

    def find_best_transpose(self, midi_file_path: str) -> int:
        """找到最佳的移调半音数，使更多音符能被映射"""
        analysis = self.analyze_midi_file(midi_file_path)
        if "error" in analysis:
            return 0

        note_counts = analysis["音符统计"]
        best_transpose = 0
        best_mapped_count = 0

        # 尝试±24半音的移调（±2个八度）
        for transpose in range(-24, 25):
            mapped_count = 0
            temp_state = {"sharp": False, "flat": False}
            for note, count in note_counts.items():
                transposed_note = self.transpose_note(note, transpose)
                key_sequence, _ = self.midi_note_to_key_sequence(
                    transposed_note, temp_state
                )
                if key_sequence:
                    mapped_count += count

            if mapped_count > best_mapped_count or (
                mapped_count == best_mapped_count
                and abs(transpose) < abs(best_transpose)
            ):
                best_mapped_count = mapped_count
                best_transpose = transpose

        return best_transpose

    def _scan_base_tempo(self, mid: "mido.MidiFile") -> int:
        """
        扫描整个文件（不受 track_filter 限制）找到第一个 set_tempo 事件的值，
        作为绝对时间换算的基准 tempo。很多 Type 1 MIDI 文件把 tempo 放在不含
        音符的第 0 音轨（常常不在 track_filter 内），如果只在被处理的音轨内查找
        tempo 会漏掉它，导致时间换算基于错误的默认 120bpm。
        """
        for track in mid.tracks:
            for msg in track:
                if msg.type == "set_tempo":
                    return msg.tempo
        return 500000

    def get_tempo_and_time_signature(self, midi_file_path: str) -> Tuple[float, int, int]:
        """
        返回 (BPM, 拍号分子, 拍号分母)，供铺面编辑的量化网格 / 小节线换算使用。
        BPM 复用与 `_scan_base_tempo` 相同的"整份文件第一个 set_tempo"口径；
        拍号取整份文件第一个 time_signature 元事件，不存在或解析失败时回退 4/4。
        """
        try:
            mid = mido.MidiFile(midi_file_path)
        except Exception:
            return 120.0, 4, 4

        tempo = self._scan_base_tempo(mid)
        bpm = 60000000.0 / tempo if tempo else 120.0

        numerator, denominator = 4, 4
        try:
            for track in mid.tracks:
                for msg in track:
                    if msg.type == "time_signature":
                        numerator = int(msg.numerator)
                        denominator = int(msg.denominator)
                        raise StopIteration
        except StopIteration:
            pass
        except Exception:
            numerator, denominator = 4, 4

        if numerator <= 0 or denominator <= 0:
            numerator, denominator = 4, 4

        return bpm, numerator, denominator

    def auto_select_tracks_and_transpose(
        self, midi_file_path: str
    ) -> Tuple[List[int], int]:
        """
        自动选择要处理的音轨（音符数最多的前两条）与最佳移调，逻辑与
        convert_midi 中的自动选择保持一致，但不生成/保存任何文件，供铺面
        在选中曲目时即时调用。
        """
        analysis = self.analyze_midi_file(midi_file_path)
        if "error" in analysis:
            return [], 0

        transpose = self.find_best_transpose(midi_file_path)

        best_tracks = []
        for i, track_info in enumerate(analysis["音轨详情"]):
            if track_info["音符事件"] > 10:
                best_tracks.append((i, track_info["音符事件"]))
        best_tracks.sort(key=lambda x: x[1], reverse=True)
        track_filter = [track[0] for track in best_tracks[:2]]

        return track_filter, transpose
