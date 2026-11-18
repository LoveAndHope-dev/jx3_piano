# Design

- `piano_roll/geometry.py`：`MIN_PITCH=0`、`MAX_PITCH=127`、`PITCH_COUNT=128`；`octave_shift_pitches` 边界随之更新。
- `piano_roll/canvas.py`、`canvas_input.py`、`canvas_paint.py`、`ruler.py` 已统一使用常量，无需逐处改；场景高度/键盘行数自动变为 128 行。
- `music/mapping.py`：`get_natural_key_ladder` 与 `get_chromatic_key_ladder` 的循环范围改为 0..127，标签由 `get_note_name` 生成（C-1 ～ G9）。
- `music/analysis.py::find_best_transpose`：候选移调需满足 `min(note)+t >= 0` 且 `max(note)+t <= 127`，否则跳过该候选。
- `music/midi_io.py`：
  - `_build_note_entry` 对 `transpose_note` 结果做 `max(0, min(127, pitch))`。
  - `write_notes_to_midi` 跳过 `pitch < 0 or pitch > 127` 的音符，并通过 `self._log` 提示跳过数量。
- `app/ui/piano_page.py::_build_mapped_pitch_set` 循环 0..127（映射集合本身仍只包含 28 键可映射音高）。

## 验证

- 复现脚本：混合文件导入 + 写回不再抛 `data byte must be in range 0..127`。
- 渲染：0、12、21、108、120、127 各自 y 坐标不同。
- 移调：126/127 整组不动；单独 126 可上移到 127；0 不可下移。
- 既有测试更新边界断言，完整回归。
