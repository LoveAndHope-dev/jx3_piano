"""播放数据与播放代码生成。"""

import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import mido

from music.paths import get_play_code_dir_path


class PlaybackMixin:
    def convert_to_playback_data(
        self,
        midi_file_path: str,
        track_filter: List[int] = None,
        channel_filter: List[int] = None,
        transpose: int = 0,
    ) -> List:
        """
        将MIDI文件转换为播放数据格式
        返回格式: [key1, key2, ..., delay, key1, key2, ..., delay, ...]
        """
        events = self.convert_midi_file(
            midi_file_path, track_filter, channel_filter, transpose
        )

        if not events:
            return []

        playback_data = []
        last_time = 0.0

        # 按时间分组事件
        grouped_events = {}
        for timestamp, key_sequence, debug_info in events:
            if timestamp not in grouped_events:
                grouped_events[timestamp] = []
            grouped_events[timestamp].extend(key_sequence)

        # 按时间顺序处理
        sorted_times = sorted(grouped_events.keys())

        for timestamp in sorted_times:
            # 添加延迟（如果需要）
            delay = timestamp - last_time
            if delay > 0 and last_time > 0:  # 第一个事件前不需要延迟
                playback_data.append(round(delay, 3))

            # 添加该时间点的所有按键
            playback_data.extend(grouped_events[timestamp])
            last_time = timestamp

        return playback_data

    def generate_playback_code(
        self,
        midi_file_path: str,
        output_file: str = None,
        track_filter: List[int] = None,
        channel_filter: List[int] = None,
        transpose: int = 0,
    ) -> str:
        """
        生成可直接运行的播放代码（新格式，支持GUI日志）
        """
        playback_data = self.convert_to_playback_data(
            midi_file_path, track_filter, channel_filter, transpose
        )

        if not playback_data:
            playback_data = []

        # 生成日志文件名（基于输出文件名）
        if output_file:
            log_file = output_file.replace(".py", "_log.txt")
        else:
            log_file = "play_log.txt"

        code_lines = []
        code_lines.append("import time")
        code_lines.append("import sys")
        code_lines.append("import os")
        code_lines.append("from datetime import datetime")
        code_lines.append("")
        code_lines.append("# 添加父目录到路径，以便导入pydd模块")
        code_lines.append(
            "sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))"
        )
        code_lines.append("")

        # 日志文件路径
        code_lines.append(f"LOG_FILE = '{log_file}'")
        code_lines.append("")

        # 日志函数
        code_lines.append("def log_message(msg):")
        code_lines.append('    """写入日志到文件，供GUI读取"""')
        code_lines.append("    timestamp = datetime.now().strftime('%H:%M:%S')")
        code_lines.append("    log_entry = f'[{timestamp}] {msg}\\n'")
        code_lines.append("    try:")
        code_lines.append("        with open(LOG_FILE, 'a', encoding='utf-8') as f:")
        code_lines.append("            f.write(log_entry)")
        code_lines.append("        print(log_entry.strip())  # 同时输出到控制台")
        code_lines.append("    except:")
        code_lines.append(
            "        print(log_entry.strip())  # 如果文件写入失败，至少输出到控制台"
        )
        code_lines.append("")

        code_lines.append("# 清空日志文件")
        code_lines.append("try:")
        code_lines.append("    with open(LOG_FILE, 'w', encoding='utf-8') as f:")
        code_lines.append("        f.write('')")
        code_lines.append("except:")
        code_lines.append("    pass")
        code_lines.append("")

        code_lines.append("try:")
        code_lines.append("    # 在打包环境中，pydd模块应该已经可用")
        code_lines.append("    from pydd import PyDD")
        code_lines.append("except ImportError:")
        code_lines.append("    try:")
        code_lines.append("        # 尝试从父目录导入")
        code_lines.append("        import pydd")
        code_lines.append("        from pydd import PyDD")
        code_lines.append("    except ImportError:")
        code_lines.append("        log_message('❌ 错误: 找不到pydd模块')")
        code_lines.append("        log_message('💡 请确保pydd.py文件在项目根目录中')")
        code_lines.append("        sys.exit(1)")
        code_lines.append("")
        code_lines.append("try:")
        code_lines.append("    import keyboard")
        code_lines.append("    keyboard_available = True")
        code_lines.append("    log_message('✅ 键盘监听模块加载成功，按ESC可停止播放')")
        code_lines.append("except ImportError:")
        code_lines.append("    keyboard_available = False")
        code_lines.append(
            "    log_message('⚠️ 警告: 找不到keyboard模块，无法使用ESC停止功能')"
        )
        code_lines.append("    # 定义一个虚拟的keyboard模块")
        code_lines.append("    class DummyKeyboard:")
        code_lines.append("        @staticmethod")
        code_lines.append("        def is_pressed(key):")
        code_lines.append("            return False")
        code_lines.append("    keyboard = DummyKeyboard()")
        code_lines.append("")

        code_lines.append("try:")
        code_lines.append("    # 在打包环境中，DLL应该在exe同目录或临时目录")
        code_lines.append("    import sys")
        code_lines.append("    if getattr(sys, 'frozen', False):")
        code_lines.append("        # 打包环境，DLL在临时目录")
        code_lines.append(
            "        dll_path = os.path.join(sys._MEIPASS, 'DD.dll')"
        )
        code_lines.append("    else:")
        code_lines.append("        # 开发环境")
        code_lines.append("        dll_path = './DD.dll'")
        code_lines.append("    dd = PyDD(dll_path)")
        code_lines.append("    log_message('✅ 按键模拟模块加载成功')")
        code_lines.append("except Exception as e:")
        code_lines.append("    log_message(f'❌ 按键模拟模块加载失败: {e}')")
        code_lines.append("    sys.exit(1)")
        code_lines.append("")

        code_lines.append("# 按键映射说明:")
        code_lines.append("# 高音1234567=1234567, 中音1234567=QWERTYU")
        code_lines.append("# 低音1234567=ASDFGHJ, 倍低音1234567=ZXCVBNM")
        code_lines.append("# 升半音=+, 降半音=- (状态管理，只在需要时切换)")
        code_lines.append("# 按ESC键可随时停止播放")
        if transpose != 0:
            direction = "升调" if transpose > 0 else "降调"
            code_lines.append(f"# 移调: {direction}{abs(transpose)}半音")
        if track_filter:
            code_lines.append(f"# 处理音轨: {track_filter}")
        code_lines.append("")

        # 生成播放数据
        code_lines.append("# 播放数据: 按键和延迟的混合列表")
        code_lines.append("# 数字代表延迟时间(秒)，字符串代表按键")
        code_lines.append("playback_data = [")

        # 将数据分组输出，方便阅读
        line_items = []
        for item in playback_data:
            if isinstance(item, (int, float)):
                if line_items:
                    code_lines.append(
                        "    "
                        + ", ".join(
                            f"'{i}'" if isinstance(i, str) else str(i)
                            for i in line_items
                        )
                        + ","
                    )
                    line_items = []
                line_items.append(item)
            else:
                line_items.append(item)

        if line_items:
            code_lines.append(
                "    "
                + ", ".join(
                    f"'{i}'" if isinstance(i, str) else str(i) for i in line_items
                )
            )

        code_lines.append("]")
        code_lines.append("")

        code_lines.append("def countdown():")
        code_lines.append('    """3秒倒计时"""')
        code_lines.append("    log_message('🎵 准备开始播放...')")
        code_lines.append("    log_message('💡 按ESC键可随时停止播放')")
        code_lines.append("    log_message('')")
        code_lines.append("    ")
        code_lines.append("    for i in range(3, 0, -1):")
        code_lines.append("        if keyboard.is_pressed('esc'):")
        code_lines.append(
            "            log_message('🛑 倒计时期间检测到ESC键，取消播放!')"
        )
        code_lines.append("            return False")
        code_lines.append("        log_message(f'⏰ {i}秒后开始播放...')")
        code_lines.append("        time.sleep(1)")
        code_lines.append("    ")
        code_lines.append("    log_message('🎶 开始播放!')")
        code_lines.append("    log_message('')")
        code_lines.append("    return True")
        code_lines.append("")
        code_lines.append("def play():")
        code_lines.append('    """播放MIDI转换后的按键序列"""')
        code_lines.append("    # 先进行3秒倒计时")
        code_lines.append("    if not countdown():")
        code_lines.append("        return")
        code_lines.append("    ")
        code_lines.append("    total_items = len(playback_data)")
        code_lines.append("    key_count = 0")
        code_lines.append("    delay_count = 0")
        code_lines.append("    ")
        code_lines.append("    # 统计按键和延迟数量")
        code_lines.append("    for item in playback_data:")
        code_lines.append("        if isinstance(item, (int, float)):")
        code_lines.append("            delay_count += 1")
        code_lines.append("        else:")
        code_lines.append("            key_count += 1")
        code_lines.append("    ")
        code_lines.append(
            "    log_message(f'📊 播放数据统计: {key_count}个按键, {delay_count}个延迟')"
        )
        code_lines.append("    log_message('')")
        code_lines.append("    ")
        code_lines.append("    start_time = time.time()")
        code_lines.append("    i = 0")
        code_lines.append(
            "    progress_step = max(1, total_items // 20)  # 显示20个进度点"
        )
        code_lines.append("    ")
        code_lines.append("    while i < len(playback_data):")
        code_lines.append("        if keyboard.is_pressed('esc'):")
        code_lines.append("            log_message('🛑 检测到ESC键，停止播放!')")
        code_lines.append("            elapsed = time.time() - start_time")
        code_lines.append("            log_message(f'⏱️ 播放时长: {elapsed:.1f}秒')")
        code_lines.append("            return")
        code_lines.append("        ")
        code_lines.append("        item = playback_data[i]")
        code_lines.append("        ")
        code_lines.append("        # 显示进度")
        code_lines.append("        if i % progress_step == 0:")
        code_lines.append("            progress = (i / total_items) * 100")
        code_lines.append("            log_message(f'🎼 播放进度: {progress:.1f}%')")
        code_lines.append("        ")
        code_lines.append("        # 如果是数字，则延迟")
        code_lines.append("        if isinstance(item, (int, float)):")
        code_lines.append("            time.sleep(item)")
        code_lines.append("        # 如果是字符串，则按键")
        code_lines.append("        else:")
        code_lines.append("            try:")
        code_lines.append("                # 状态切换按键需要额外延迟确保稳定")
        code_lines.append("                if item in ['+', '-']:")
        code_lines.append("                    dd.key_press(item, 0.03)")
        code_lines.append("                else:")
        code_lines.append("                    # 普通按键")
        code_lines.append("                    dd.key_press(item)")
        code_lines.append("            except Exception as e:")
        code_lines.append("                log_message(f'⚠️ 按键 {item} 执行失败: {e}')")
        code_lines.append("        ")
        code_lines.append("        i += 1")
        code_lines.append("")
        code_lines.append("    # 播放完成")
        code_lines.append("    elapsed = time.time() - start_time")
        code_lines.append("    log_message('✅ 播放完成')")
        code_lines.append("    log_message(f'⏱️ 总播放时长: {elapsed:.1f}秒')")
        code_lines.append("    log_message(f'🎹 共执行 {key_count} 个按键操作')")
        code_lines.append("")
        code_lines.append("if __name__ == '__main__':")
        code_lines.append("    try:")
        code_lines.append("        play()")
        code_lines.append("    except KeyboardInterrupt:")
        code_lines.append("        log_message('🛑 程序被中断')")
        code_lines.append("    except Exception as e:")
        code_lines.append("        log_message(f'❌ 播放出错: {e}')")
        code_lines.append("        import traceback")
        code_lines.append("        log_message(f'详细错误: {traceback.format_exc()}')")

        result = "\n".join(code_lines)

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result)

        return result

    def regenerate_playback_from_notes(
        self,
        notes: List[Dict[str, Any]],
        pitch_range: Optional[Tuple[int, int]] = None,
        transpose: int = 0,
    ) -> Dict[str, Any]:
        """
        由（可能已被铺面编辑器修改的）结构化音符列表重新生成播放数据与统计信息。
        复用 midi_note_to_key_sequence 状态机，按音符起始时间排序后统一走一遍
        状态机，再按相同时间戳分组，逻辑上等价于 convert_to_playback_data。

        pitch_range: 可选的 (框体当前低边界音高, 框体当前高边界音高) 闭区间
        （未扩展半音，源端筛选窗口）。传入时会在闭区间基础上向下/向上各扩展
        1 个半音，只保留原始音高落在扩展区间内的音符（乐器音域框功能使用）；
        为 None 时不做范围过滤，保持原有（复用全部 28 个键位映射系统）行为不变。

        transpose: 对筛选后音符统一施加的半音移调量（播放音高 = 原始音高 +
        transpose），保持音符间原有音程关系不变，不做拉伸/压缩；为 0 时行为
        与不移调完全一致。

        返回: {"playback_data", "note_statistics", "statistics"}
        """
        sorted_notes = sorted(notes, key=lambda n: (n.get("start", 0.0), n.get("track", 0)))

        range_low = pitch_range[0] - 1 if pitch_range else None
        range_high = pitch_range[1] + 1 if pitch_range else None

        current_state = {"sharp": False, "flat": False}
        grouped: Dict[float, List[str]] = {}
        note_statistics: Dict[int, int] = defaultdict(int)

        for note in sorted_notes:
            pitch = int(note["pitch"])
            note_statistics[pitch] += 1

            if pitch_range is not None and not (range_low <= pitch <= range_high):
                continue

            key_sequence, current_state = self.midi_note_to_key_sequence(
                pitch + transpose, current_state
            )
            if not key_sequence:
                continue

            start = round(float(note.get("start", 0.0)), 3)
            grouped.setdefault(start, []).extend(key_sequence)

        playback_data: List[Any] = []
        last_time = 0.0
        is_first_group = True
        for t in sorted(grouped.keys()):
            if not is_first_group:
                delay = t - last_time
                if delay > 0:
                    playback_data.append(round(delay, 3))
            playback_data.extend(grouped[t])
            last_time = t
            is_first_group = False

        total_duration = max(
            (
                float(n.get("start", 0.0)) + float(n.get("duration", 0.0))
                for n in notes
            ),
            default=0.0,
        )

        statistics = {
            "total_tracks": len({n.get("track", 0) for n in notes}),
            "total_duration": total_duration,
            "note_count": len(notes),
            "operation_count": len(playback_data),
            "key_count": sum(1 for item in playback_data if isinstance(item, str)),
            "delay_count": sum(
                1 for item in playback_data if isinstance(item, (int, float))
            ),
        }

        return {
            "playback_data": playback_data,
            "note_statistics": dict(note_statistics),
            "statistics": statistics,
        }

    def generate_complete_data_file(
        self,
        midi_file_path: str,
        output_file: str = None,
        track_filter: List[int] = None,
        channel_filter: List[int] = None,
        transpose: int = 0,
    ) -> Dict[str, Any]:
        """
        生成完整的播放数据文件（包含所有信息）

        Args:
            midi_file_path: MIDI文件路径
            output_file: 输出文件路径（可选，默认为MIDI同名JSON文件）
            track_filter: 音轨过滤器
            channel_filter: 通道过滤器
            transpose: 移调半音数

        Returns:
            Dict: 包含文件路径和处理结果的字典
        """
        # 分析MIDI文件
        analysis = self.analyze_midi_file(midi_file_path)
        if "error" in analysis:
            return {"error": analysis["error"], "success": False}

        # 转换为播放数据
        playback_data = self.convert_to_playback_data(
            midi_file_path, track_filter, channel_filter, transpose
        )

        if not playback_data:
            playback_data = []

        # 解析结构化音符列表（供铺面编辑器使用）
        notes = self.extract_notes(
            midi_file_path, track_filter, channel_filter, transpose
        )

        # 准备文件名
        base_name = (
            os.path.basename(midi_file_path).replace(".mid", "").replace(".midi", "")
        )

        # 如果没有指定输出文件路径，使用MIDI同名的JSON文件
        if not output_file:
            output_file = os.path.join(get_play_code_dir_path(), f"{base_name}.json")

        # 准备完整数据结构
        complete_data = {
            "version": "2.0",
            "type": "jx3_piano_complete",
            # 文件基本信息
            "filename": base_name,
            "midi_file": midi_file_path,
            "generation_time": datetime.now().isoformat(),
            # 处理参数
            "transpose": transpose,
            "processed_tracks": track_filter or [],
            "processed_channels": channel_filter or [],
            # MIDI文件分析信息
            "file_info": analysis["文件信息"],
            "track_details": analysis["音轨详情"],
            "note_statistics": analysis["音符统计"],
            # 播放数据
            "playback_data": playback_data,
            # 结构化音符列表（铺面编辑用；音高已应用移调）
            "notes": notes,
            # 统计信息
            "statistics": {
                "total_tracks": len(analysis["音轨详情"]),
                "total_duration": analysis["文件信息"]["总时长"],
                "note_count": sum(analysis["音符统计"].values()),
                "operation_count": len(playback_data),
                "key_count": sum(1 for item in playback_data if isinstance(item, str)),
                "delay_count": sum(
                    1 for item in playback_data if isinstance(item, (int, float))
                ),
            },
            # 按键映射说明
            "key_mapping": {
                "description": "剑网三钢琴按键映射",
                "high_notes": "1234567 -> 1234567",
                "mid_notes": "1234567 -> QWERTYU",
                "low_notes": "1234567 -> ASDFGHJ",
                "extra_low_notes": "1234567 -> ZXCVBNM",
                "sharp": "+ (升半音)",
                "flat": "- (降半音)",
            },
        }

        # 保存文件
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(complete_data, f, ensure_ascii=False, indent=2)

            if self.log_callback:
                self.log_callback(f"✅ 完整数据文件已生成: {output_file}")

            return {
                "output_file": output_file,
                "data": complete_data,
                "success": True,
            }

        except Exception as e:
            if self.log_callback:
                self.log_callback(f"❌ 保存文件失败: {e}")
            return {"error": str(e), "success": False}
