"""命令行转换入口。"""

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import mido

from music.paths import ensure_directories_exist, get_midi_dir_path, get_play_code_dir_path


class CliMixin:
    def print_analysis_summary(
        self, analysis: dict, transpose: int = 0
    ) -> Dict[str, Any]:
        """
        打印并返回分析摘要信息（修改为支持GUI）
        返回摘要信息字典，便于GUI使用
        """
        if "error" in analysis:
            error_msg = f"错误: {analysis['error']}"
            self._log(error_msg)
            return {"error": analysis["error"]}

        summary = {
            "tracks": analysis["文件信息"]["音轨数量"],
            "duration": analysis["文件信息"]["总时长"],
            "ticks_per_beat": analysis["文件信息"]["时间分辨率"],
            "transpose": transpose,
            "active_tracks": [],
            "note_range": {
                "lowest": analysis["音域分析"]["最低音"],
                "highest": analysis["音域分析"]["最高音"],
                "lowest_name": self.get_note_name(analysis["音域分析"]["最低音"]),
                "highest_name": self.get_note_name(analysis["音域分析"]["最高音"]),
            },
            "coverage": 0,
        }

        self._log("=" * 60)
        self._log("📄 MIDI文件分析摘要")
        self._log("=" * 60)

        # 基本信息
        self._log(f"🎵 音轨数量: {summary['tracks']}")
        self._log(f"⏱️  总时长: {summary['duration']:.2f}秒")
        self._log(f"🎼 时间分辨率: {summary['ticks_per_beat']} ticks/beat")

        # 音轨信息
        self._log(f"\n🎹 有效音轨:")
        for track_info in analysis["音轨详情"]:
            if track_info["音符事件"] > 0:
                name = track_info["音轨名称"] or "未命名"
                track_summary = {
                    "index": track_info["音轨号"],
                    "note_count": track_info["音符事件"],
                    "name": name,
                }
                summary["active_tracks"].append(track_summary)
                self._log(
                    f"  音轨{track_info['音轨号']}: {track_info['音符事件']}个音符 ({name})"
                )

        # 音域信息
        self._log(f"\n🎼 音域范围:")
        self._log(f"  最低音: {summary['note_range']['lowest_name']}")
        self._log(f"  最高音: {summary['note_range']['highest_name']}")

        # 移调信息
        if transpose != 0:
            direction = "升调" if transpose > 0 else "降调"
            self._log(f"  建议移调: {direction}{abs(transpose)}半音")

        # 覆盖率信息
        total_notes = sum(analysis["音符统计"].values())
        mapped_notes = 0
        temp_state = {"sharp": False, "flat": False}
        for note, count in analysis["音符统计"].items():
            transposed = self.transpose_note(note, transpose)
            key_sequence, _ = self.midi_note_to_key_sequence(transposed, temp_state)
            if key_sequence:
                mapped_notes += count

        coverage = (mapped_notes / total_notes) * 100 if total_notes > 0 else 0
        summary["coverage"] = coverage
        self._log(f"\n📊 音符覆盖率: {coverage:.1f}%")

        if coverage < 70:
            self._log("⚠️  覆盖率较低，可能需要调整移调设置")

        self._log("=" * 60)
        return summary

    def convert_midi(
        self, midi_file_path: str, track_filter: List[int] = None, transpose: int = None
    ) -> Dict[str, Any]:
        """
        完整的MIDI转换流程（修改为返回结果信息）
        返回转换结果字典
        """
        self._log(f"🎵 正在转换: {midi_file_path}")
        self._log("")

        try:
            # 第一步：分析MIDI文件
            analysis = self.analyze_midi_file(midi_file_path)

            if "error" in analysis:
                error_msg = f"错误: {analysis['error']}"
                self._log(error_msg)
                return {"success": False, "error": analysis["error"]}

            # 第二步：确定最佳移调（如果未指定）
            if transpose is None:
                transpose = self.find_best_transpose(midi_file_path)

            # 第三步：确定要处理的音轨（如果未指定）
            if track_filter is None:
                best_tracks = []
                for i, track_info in enumerate(analysis["音轨详情"]):
                    if track_info["音符事件"] > 10:
                        best_tracks.append((i, track_info["音符事件"]))

                best_tracks.sort(key=lambda x: x[1], reverse=True)
                track_filter = [
                    track[0] for track in best_tracks[:2]
                ]  # 取前2个最佳音轨

            # 第四步：获取分析摘要
            summary = self.print_analysis_summary(analysis, transpose)

            # 第五步：生成播放文件
            if track_filter:
                base_name = os.path.basename(midi_file_path)
                base_name = base_name.replace(".mid", "").replace(".midi", "")
                output_file = os.path.join(
                    get_play_code_dir_path(), f"play_{base_name}_{transpose}.py"
                )

                self._log(f"\n正在生成播放文件...")
                code = self.generate_playback_code(
                    midi_file_path,
                    output_file,
                    track_filter=track_filter,
                    transpose=transpose,
                )

                self._log(f"✅ 转换完成!")
                self._log(f"📁 生成文件: {os.path.basename(output_file)}")
                self._log(f"🎼 处理音轨: {track_filter}")
                self._log(f"🎵 移调: {transpose}半音")

                return {
                    "success": True,
                    "output_file": output_file,
                    "track_filter": track_filter,
                    "transpose": transpose,
                    "summary": summary,
                    "analysis": analysis,
                }
            else:
                error_msg = "❌ 没有找到合适的音轨"
                self._log(error_msg)
                return {"success": False, "error": "没有找到合适的音轨"}

        except Exception as e:
            error_msg = f"❌ 转换失败: {e}"
            self._log(error_msg)
            import traceback

            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def convert_midi_file(
        self,
        midi_file_path: str,
        track_filter: List[int] = None,
        channel_filter: List[int] = None,
        transpose: int = 0,
    ) -> List[Tuple[float, List[str], dict]]:
        """
        转换MIDI文件为按键序列
        track_filter: 指定要处理的音轨列表，None表示处理所有音轨
        channel_filter: 指定要处理的MIDI通道列表，None表示处理所有通道
        transpose: 移调半音数（正数升调，负数降调）
        返回: [(时间戳, 按键序列, 调试信息), ...]
        """
        mid = mido.MidiFile(midi_file_path)
        events = []

        # 获取正确的tempo用于时间转换
        tempo = 500000  # 默认tempo (120 BPM)

        # 初始化状态管理
        current_state = {"sharp": False, "flat": False}

        for track_idx, track in enumerate(mid.tracks):
            if track_filter and track_idx not in track_filter:
                continue

            track_time = 0.0
            for msg in track:
                # 更新tempo
                if msg.type == "set_tempo":
                    tempo = msg.tempo

                # 更新时间
                track_time += mido.tick2second(msg.time, mid.ticks_per_beat, tempo)

                # 处理音符事件
                if msg.type == "note_on" and msg.velocity > 0:
                    if channel_filter and msg.channel not in channel_filter:
                        continue

                    # 应用移调
                    transposed_note = self.transpose_note(msg.note, transpose)

                    # 使用状态管理的音符转换
                    result = self.midi_note_to_key_sequence(
                        transposed_note, current_state
                    )
                    key_sequence, new_state = result
                    current_state = new_state

                    # 跳过无法映射的音符
                    if not key_sequence:
                        continue

                    debug_info = {
                        "track": track_idx,
                        "channel": msg.channel,
                        "note": msg.note,
                        "transposed_note": transposed_note,
                        "note_name": self.get_note_name(msg.note),
                        "transposed_name": self.get_note_name(transposed_note),
                        "velocity": msg.velocity,
                        "mapped": key_sequence is not None,
                        "transpose": transpose,
                        "action": "press",
                    }
                    events.append((track_time, key_sequence, debug_info))

        # 按时间排序
        events.sort(key=lambda x: x[0])
        return events
