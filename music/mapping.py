"""音高到游戏按键的映射。"""

from typing import Dict, List, Optional, Tuple


class MappingMixin:
    def _log(self, message: str):
        """内部日志方法"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def transpose_note(self, midi_note: int, semitones: int) -> int:
        """移调音符"""
        return midi_note + semitones

    def midi_note_to_key_sequence(
        self, midi_note: int, current_state: dict = None
    ) -> Tuple[List[str], dict]:
        """
        将MIDI音符转换为按键序列（包含升降音处理和状态管理）
        current_state: 当前的升降状态 {'sharp': bool, 'flat': bool}
        返回: (按键序列, 新状态)
        """
        if current_state is None:
            current_state = {"sharp": False, "flat": False}

        new_state = current_state.copy()
        key_sequence = []

        # 首先检查是否为自然音符
        if midi_note in self.base_note_mapping:
            # 如果当前有升降状态，需要复原到自然状态
            if current_state["sharp"]:
                key_sequence.append("-")  # 复原升号
                new_state["sharp"] = False
            elif current_state["flat"]:
                key_sequence.append("+")  # 复原降号
                new_state["flat"] = False

            key_sequence.append(self.base_note_mapping[midi_note])
            return key_sequence, new_state

        # 检查是否为升号音符
        if midi_note in self.sharp_notes:
            base_note, is_sharp = self.sharp_notes[midi_note]
            base_key = self.base_note_mapping[base_note]

            # 如果当前不是升号状态，需要切换到升号状态
            if current_state["flat"]:
                key_sequence.append("+")  # 先复原降号
                key_sequence.append("+")  # 再切换到升号
                new_state["flat"] = False
                new_state["sharp"] = True
            elif not current_state["sharp"]:
                key_sequence.append("+")  # 切换到升号状态
                new_state["sharp"] = True

            key_sequence.append(base_key)
            return key_sequence, new_state

        # 检查是否为降号音符（通过查找高一个半音的音符）
        higher_note = midi_note + 1
        if higher_note in self.base_note_mapping:
            base_key = self.base_note_mapping[higher_note]

            # 如果当前不是降号状态，需要切换到降号状态
            if current_state["sharp"]:
                key_sequence.append("-")  # 先复原升号
                key_sequence.append("-")  # 再切换到降号
                new_state["sharp"] = False
                new_state["flat"] = True
            elif not current_state["flat"]:
                key_sequence.append("-")  # 切换到降号状态
                new_state["flat"] = True

            key_sequence.append(base_key)
            return key_sequence, new_state

        # 如果无法映射，返回空列表而不是None，保持兼容性
        return [], current_state

    def midi_note_to_key(self, midi_note: int) -> Optional[str]:
        """向后兼容的简单映射函数"""
        key_sequence, _ = self.midi_note_to_key_sequence(midi_note)
        if key_sequence and len(key_sequence) == 1:
            return key_sequence[0]
        return None

    def get_note_name(self, midi_note: int) -> str:
        """获取MIDI音符的名称用于调试"""
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        octave = midi_note // 12 - 1
        note = note_names[midi_note % 12]
        return f"{note}{octave}"
