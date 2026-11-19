# 验收记录：out-of-range-play-prompt-and-guide

## 环境

- Windows + Python 3.14 + PyQt5
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 250 tests ... OK`

## 变更

### 播放前超范围确认

- `app/playback.py` 新增：
  - `_count_unplayable_notes(notes=None, pitch_range=None)`：按 `low-1 .. high+1` 统计映射框外音符。
  - `_confirm_play_out_of_range(...)`：数量大于 0 时弹窗说明数量，让用户选择继续播放或取消。
  - `start_playing(confirm_range=True)`：曲目校验后、生成播放资产前确认；取消时记录日志并返回。
- 正常模式的「演奏」/主按钮播放同样经过该确认。
- 简单模式在读取原始 MIDI 后、执行曲谱优化和保存之前调用确认；取消时不优化、不保存、不播放。

### 向导

- 保留「💾 数据位置」小节与 `midi/`、`midi/edited/`、`play_code/` 说明。
- 删除简单/正常模式小节中的内部流程术语（「重读原始 MIDI」「保存 play_code JSON」「铺面资产」）。
- 新增「🎻 乐器与移调」小节：朝晖琴、南音三弦等拨奏类乐器的移调建议在 **+5 到 -5** 之间。
- 简单模式小节新增：**MIDI 中的所有音符需要落在 C2 至 B5 之间**。
- 「铺面编辑工具栏」与「钢琴窗」改为正常模式下的子小节。

## 覆盖

| 场景 | 测试 |
| --- | --- |
| 统计框外音符（±1 半音边界） | `test_count_unplayable_notes_uses_box_plus_one_semitone` |
| 取消播放不生成资产、不开始 | `test_play_prompt_cancel_does_not_start` |
| 选择继续则继续后续流程 | `test_play_prompt_continue_proceeds` |
| 全部在范围内不弹窗 | `test_play_prompt_skipped_when_all_notes_in_range` |
| 简单模式取消时跳过优化/保存/播放 | `test_simple_play_cancel_on_out_of_range_skips_work` |
| 简单模式继续时只确认一次 | `test_simple_play_optimizes_saves_then_plays` |
| 向导含移调、C2–B5、数据位置，模式小节无内部术语 | `test_guide_opens_and_covers_areas` |
| 其余回归 | 既有 243 项 |

## 备注

- 弹窗默认按钮为「是」，可直接继续播放。
- 超范围判定与播放资产生成的过滤条件一致（框体 ±1 半音）。
- exe 已重新打包（`94bf198`），构建产物已清理。
