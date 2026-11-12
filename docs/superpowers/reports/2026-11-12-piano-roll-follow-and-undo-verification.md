# 验收记录：piano-roll-follow-and-undo

## 环境

- Windows + Python 3.14 + PyQt5
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 149 tests ... OK`

## 覆盖

| 能力 | 覆盖测试 |
| --- | --- |
| 播放翻页：超过 80% 滚动 | `test_piano_roll_ui.test_follow_scrolls_page_when_playhead_passes_threshold` |
| 阈值内不滚动 | `test_follow_keeps_scroll_inside_threshold` |
| 非播放不跟随 | `test_no_follow_when_not_playing` |
| 撤销删除、前进恢复、未保存标记 | `test_playlist_gui.test_undo_restores_deleted_notes` |
| BPM 撤销与音符时间恢复 | `test_undo_restores_bpm` |
| 演奏模式忽略撤销 | `test_undo_ignored_in_play_mode` |
| 50 步上限 | `test_history_limit_is_fifty` |
| 撤销回初始状态清除未保存 | `test_undo_to_initial_state_clears_dirty` |

## 独立审查后的修复

- **Critical**：BPM 变更时 `current_bpm` 在 `rescale_times` 之后才更新，导致历史快照记录「新音符时间 + 旧 BPM」。已改为先更新 BPM 再缩放；新增「BPM 变更后重做」「BPM 变更后再编辑再撤销」回归测试。
- **跟随门控**：改为仅在播放中（`_playhead_locked`）跟随，演奏模式标尺拖动不再触发翻页；新增对应测试与 20% 落点/滚动上限断言。
- **剪贴板**：快照包含并恢复内部剪贴板；解析失败时清空历史。
- 补测：新操作清空 redo、撤销恢复辅助线、撤销自身不入栈、画布 Ctrl+Z/Ctrl+Shift+Z 信号与只读拦截。

最近一次结果：`Ran 157 tests ... OK`。

## 手动确认

- 长曲播放时辅助线超过右侧 80% 后整页前滚，停止后不再滚动。
- Ctrl+Z 撤销删除/移动/粘贴/曲谱优化/BPM；Ctrl+Shift+Z 前进；演奏模式快捷键无效。
- 撤销后 BPM 框、标尺、量化网格与辅助线同步恢复。

## 结论

两项能力均有 offscreen UI 测试覆盖，剩余为真实窗口观感与手感确认。
