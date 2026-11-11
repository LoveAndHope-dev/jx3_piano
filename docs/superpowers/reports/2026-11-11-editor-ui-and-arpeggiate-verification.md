# 验收记录：editor-ui-and-arpeggiate

## 环境

- Windows + Python 3.14 + PyQt5
- 测试命令：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 最近一次结果：`Ran 124 tests ... OK`（上一轮 114 + 本轮 10）

## 自动化覆盖

| 能力 | 覆盖测试 |
| --- | --- |
| 琶音：三音按音高展开、结束时间不变 | `test_arpeggiate.test_expands_chord_by_pitch`、`test_end_time_is_preserved` |
| 琶音：单音不变、未选中不动、两组独立 | `test_single_note_unchanged`、`test_unselected_untouched`、`test_groups_are_independent` |
| 琶音：过短钳制起点、输入不被修改、非法拍长 | `test_short_note_clamps_start`、`test_input_is_not_mutated`、`test_invalid_beat_returns_copies` |
| 工具栏按钮触发琶音 | `test_playlist_gui.test_arpeggiate_selected_notes` |
| 编辑模式禁用弹奏、演奏模式启用 | `test_playlist_gui.test_mode_toggle_locks_roll` |
| 默认映射 Z(36)/7(83)、黄框 C2～B2 | `test_default_mapping_and_range_box` |

## 独立审查后的修复

最终集成审查（review_mode: standard）覆盖 `51d5b84..49221ac`，结论「With fixes」。已修复项：

1. **Critical：播放列表每行控件被 QSS 内边距压到 13px，名称与 🗑 被裁切。** 行条目固定 `sizeHint` 48px、删除按钮固定 34×26 并去除按钮内边距；新增行高回归测试。
2. **Important：无曲目/解析失败时模式 UI 与只读失步。** `_set_range_controls_enabled` 末尾统一调用 `_sync_roll_mode()`；曲谱优化按钮同时要求已加载曲目。
3. **Important：极短音符的琶音会早于锚点。** 起点强制不早于组锚点；无法保持结束时间时以最小时长为准（spec 同步说明）。
4. **Minor：** 琶音无实际变化时不再标记未保存；`refresh_play_list` 用 `try/finally` 恢复信号；BPM 数值框隐藏上下箭头并增加 focus 边框；移除未用导入；画布 `arpeggiate_selected` 增加只读保护。

最近一次结果：`Ran 129 tests ... OK`。

## 仍需人工确认（真实窗口）

- 两个新文案与「钢琴音域绝对最低/最高键」的显示宽度。
- BPM 输入框与下拉框是否视觉一致（深色背景、边框、圆角）。
- 两行工具栏在 1000px 默认窗口下不重叠、换行位置符合预期。
- 每行末尾「🗑」的位置与命中区域；逐行删除的确认与刷新。
- 「🪄 曲谱优化」按钮的 tooltip 与执行后的听感。

## 结论

琶音算法、按钮接线、模式与弹奏联动、默认值均有自动化覆盖；剩余为真实窗口的视觉与手感确认。
