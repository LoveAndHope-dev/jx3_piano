# 验收记录：editor-toolbar-layout-and-arpeggiate-script

## 环境

- Windows + Python 3.14 + PyQt5 + mido 1.3.3
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 168 tests ... OK`

## 覆盖

| 能力 | 覆盖测试 |
| --- | --- |
| 两行工具栏贴左且只有行尾弹性空白 | `test_playlist_gui.test_piano_toolbar_rows_hug_left` |
| 窗口拉宽后控件位置与宽度不变 | `test_piano_toolbar_positions_stable_when_window_grows` |
| 置顶按钮在控制面板标题行、日志页无此按钮 | `test_topmost_button_lives_in_control_panel_header` |
| 置顶按钮文字与日志 | `test_topmost_toggle_updates_text_and_log` |
| 曲谱优化进入撤销历史 | `test_arpeggiate_is_undoable` |
| 脚本异常时铺面/图形/选择/历史/未保存标记不变 | `test_arpeggiate_script_failure_keeps_roll` |
| 去重移除音符时同步删除图形与选择并进入历史 | `test_arpeggiate_dedupe_removes_note_item_and_is_undoable` |
| 和弦按音高展开 | `test_arpeggiate.test_expands_chord_by_pitch` |
| 展开后时长不变、结束时间随起点后移 | `test_durations_are_preserved`、`test_ends_move_with_starts` |
| 未选中音符不变 | `test_unselected_untouched` |
| 同音高同起点去重（保留最长时值） | `test_duplicate_notes_are_deduped` |
| 非整 tick 的单音符不被挪动 | `test_off_grid_single_note_is_not_nudged` |
| 脚本结构/常量保留、旧实现移除 | `test_script_structure_is_preserved` 等 |

## 布局实测（offscreen）

窗口宽度 1400 / 1600 / 1800 / 2200 时，弹奏按钮 `x=384`、最高键位映射下拉 `x=1189`、BPM 框 `x=1030` 完全不变。窗口 1200 时右侧面板仅 847px，小于工具栏自然宽度 893px，控件按 Qt 规则压缩到接近最小宽度；这是可用空间不足，不是贴左逻辑漂移。

截图确认：控制面板标题「🎛️ 控制面板」在边框内左上，置顶按钮在同一行右侧；工具栏两行均从容器左边缘开始。

## 独立审查后的修复

- **Critical**：脚本去重删除音符时，画布只替换了 `_notes`，未移除对应图形与选择项，且删除单独发生时 `changed == 0` 导致不发 `notesChanged`（不标脏、不入历史），残留图元点击会抛 `TypeError`。现已同步移除图元与选择、把删除计入变更数，并补 `test_arpeggiate_dedupe_removes_note_item_and_is_undoable`。
- **Important**：①布局测试改为真实改变窗口宽度并比较控件坐标/宽度；②脚本失败测试改为 patch `arpeggiate.main`，验证模型、图元、选择、历史与未保存标记全部不变；③非整 tick 的单音符不再被无意义挪动（差异小于半个 tick 视为量化噪声）；④重新打包并提交 release exe。
- **Minor**：输出音轨校验为「每轨 1 个音符且音高匹配」；BPM 无效时在 `try` 内拒绝；新增置顶文字/日志测试。

## 手动确认

- 窗口拉宽后工具栏控件不再被推到右侧，也不再横向漂移。
- 置顶按钮现在位于控制面板标题行，操作日志页只剩「清空」。
- 选中和弦点击曲谱优化：按音高从低到高依次后移 1/32 拍，时长相较原位置不变，Ctrl+Z 可撤销。

## 结论

全部需求由 offscreen UI 测试、脚本往返单测与真实窗口宽度的几何对比覆盖；release exe 已用本次源码重新打包。
