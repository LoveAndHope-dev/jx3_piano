# 验收记录：playlist-checkboxes-and-guide

## 环境

- Windows + Python 3.14 + PyQt5
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 234 tests ... OK`

## 变更

### 播放列表勾选框

- 每行左侧新增复选框；`_checked_play_paths` 独立记录勾选路径。
- 点击行只切换当前曲目（单选并加载），Ctrl/Shift 点击也不会多选。
- 「全选」勾选当前列表全部行；「删除选中」只处理勾选路径（未勾选只提示）。
- 刷新/搜索后按路径恢复勾选；删除曲目时从勾选集合移除。
- 保留 `on_delete_play_item` 单曲删除入口。

### 使用向导

- 控制面板新增「❓ 向导」按钮，打开非模态、可滚动说明窗口。
- 内容覆盖：控制面板、播放列表、铺面编辑三行工具栏、钢琴窗、操作日志、快捷键与数据目录。
- 主题补充 `QCheckBox` 与 `QTextBrowser` 样式。

## 覆盖

| 场景 | 测试 |
| --- | --- |
| 全选勾选所有行 | `test_select_all_selects_every_item` |
| 批量删除并清空当前铺面 | `test_delete_selected_play_items` |
| 未勾选不弹确认 | `test_delete_selected_without_selection_does_not_prompt` |
| Ctrl 点击仍为单选 | `test_ctrl_click_row_stays_single_selection` |
| 勾选不改变当前曲目 | `test_checkbox_toggles_without_changing_current` |
| 向导打开与内容覆盖 | `test_guide_opens_and_covers_areas` |
| 其余 228 项 | 既有回归 |

## 备注

- exe 已重新打包（`e3241e4`），构建产物已清理。
