# 验收记录：fix-midi-range-and-pitch-edges

## 环境

- Windows + Python 3.14 + mido
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 224 tests ... OK`

## 缺陷复现

**导入报错（修复前）**
构造含 24–71 与一个 120 的 MIDI：自动移调选择 `+11`，120 变成 131；写回 `edited/<曲目>.mid` 时抛出
`ValueError: data byte must be in range 0..127`。

**音高边界（修复前）**
铺面只覆盖 21–108。0/12/21 全部渲染在 y=870，108/120/127 全部在 y=0；拖动被夹在 21/108。

## 修复

- `find_best_transpose`：候选移调必须满足整体仍在 0–127，否则跳过。
- `_build_note_entry`：移调结果防御性钳制到 0–127。
- `write_notes_to_midi`：跳过仍越界的音符并记录「跳过 N 个音高越界的音符」。
- 铺面音高范围改为 0–127（`PITCH_COUNT=128`）；键盘、行高、音域框阶梯、拖动/移调边界同步扩展。
- `_build_mapped_pitch_set` 扫描 0–127；游戏键位映射仍只覆盖原有 28 键。

## 修复后实测

- 同一混合文件：移调选 `+7`，音高范围 31–127，写回成功。
- 音高 0/12/21/108/120/127 分别位于 y=1270/1150/1060/190/70/0，互不重叠，可单独选中移动。

## 覆盖

| 场景 | 测试 |
| --- | --- |
| 自动移调不越界 | `test_auto_transpose_stays_inside_midi_range` |
| 导入 + 写回不报错 | `test_import_and_write_back_do_not_raise` |
| 越界音符写回时跳过 | `test_write_skips_out_of_range_notes` |
| 移调结果钳制 | `test_transposed_entry_is_clamped` |
| 边界音高各自成行 | `test_edge_pitches_occupy_distinct_rows` |
| 边界音符可向内移动、不可越界 | `test_edge_pitch_can_move_inward_but_not_outward` |
| 整组越界不移动 | `test_transpose_skips_whole_group_at_boundary` |
| 八度移调边界 | `test_octave_shift_skips_notes_out_of_range` 等 |

## 备注

- 超出游戏 28 键映射范围的音符仍会标记为未映射，播放时跳过并提示，这是原有行为。
- exe 已重新打包（`372693f`），随后清理了构建产物。
- 打包体积问题（>30MB）按之前决定未处理。
