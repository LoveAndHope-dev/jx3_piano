# 验收记录：piano-toolbar-zoom-and-theme-modes

## 环境

- Windows + Python 3.14 + PyQt5
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 214 tests ... OK`

## 工具栏

| 行 | 内容 |
| --- | --- |
| 第一行 | `🎼 铺面编辑`（16px/600）靠左；`🎹 演奏模式 / ✏️ 编辑模式` 固定右侧 |
| 第二行 | `💾 保存 / ▶️ 演奏 / ⏹️ 停止`（合并主按钮）、曲谱优化、未保存标记靠左；量化、BPM 靠右 |
| 第三行 | 演奏最低键位映射、演奏最高键位映射、钢琴音域绝对最低键、绝对最高键，全部靠左 |

- 合并按钮：编辑模式只保存（未修改时禁用）；切到演奏模式后点击开始播放，播放中显示停止。
- 内部引用 `piano_save_btn` 全部改为 `_update_primary_btn()`，播放/停止/完成/撤销/加载/删除后状态一致。

## 钢琴窗

- `Shift + 滚轮`：行高 6–24px、1.25 倍步长，以鼠标所在音高为锚点；不触发 `notesChanged`。
- 播放开始（`set_playhead_locked(True)`）时黄色音域框纵向中心滚到视口中心，只执行一次。
- 左侧键盘在水平滚动时几何不变（新增回归测试）。

## 主题

- `DARK_TOKENS` / `LIGHT_TOKENS`；控制面板标题行新增 `☀️ 亮色 / 🌙 深色` 切换按钮。
- 浅色令牌：页面 `#f5f5f5`、容器 `#ffffff`、边框 `#d9d9d9`、文字 `rgba(0,0,0,0.88)`；主色与间距/圆角/字号不变。
- 仅会话内记忆，重启回到深色。
- 新增 `primaryBtn`、`pageTitle` 样式；两套主题共用状态派生。

## 覆盖

| 能力 | 测试 |
| --- | --- |
| 三行结构与左右分组 | `test_piano_toolbar_three_rows` |
| 窗口变宽时左侧稳定、右侧贴边 | `test_piano_toolbar_positions_stable_when_window_grows` |
| 编辑模式保存 / 演奏模式播放 | `test_primary_button_saves_in_edit_mode`、`test_primary_button_plays_in_play_mode` |
| 未保存标记与播放状态控制按钮 | `test_primary_button_is_dirty_aware_in_edit_mode`、`test_primary_button_shows_stop_while_playing` |
| 模式切换锁定与按钮文案 | `test_mode_toggle_locks_roll` |
| 行高夹紧、Shift 缩放与锚点 | `test_row_height_zoom_clamps`、`test_shift_wheel_zooms_rows_with_pitch_anchor` |
| 播放纵向居中 | `test_playhead_lock_centers_instrument_range` |
| 键盘水平固定 | `test_keyboard_stays_pinned_when_scrolling_horizontally` |
| 亮暗主题切换 | `test_theme_toggle_switches_stylesheet`、`test_antd_light_palette` |
| 既有行为 | 其余 200 项 |

## 独立审查后的修复

- **Critical**：播放中切回编辑模式（或切曲）会丢失唯一的「停止」入口。现改为播放状态优先：只要 `is_playing`，主按钮始终显示「⏹️ 停止」且可用，点击执行停止；新增回归测试。
- **Important/Minor**：①纵向聚焦只在 `未锁定 → 锁定` 时执行，播放中重新加载曲目不再打断手动滚动；②停止按钮与主按钮同宽，播放开始/停止不再挤动第二行；③浅色模式禁用主按钮改用 antd 的 `#f5f5f5/#d9d9d9`，避免「看不见」；④主题按钮使用独立选择器（悬停主色而非危险红）；⑤第三行两个映射下拉固定宽度，避免绝对音域字段随窗口宽度横移；⑥移除已废弃的 `#playBtn` 样式、修正注释与文档、用显式 `unpolish/polish` 代替空样式重刷。
- **测试**：新增「播放中退出演奏模式仍可停止」、隐藏音域不聚焦、滚动边界夹紧、浅色禁用可见性、`primaryBtn` 状态选择器；键盘固定测试改用真正可横向滚动的曲目；缩放锚点断言收紧到 1.5px。
- 复验结果：`Ran 214 tests ... OK`；exe 已重新打包。

## 手动确认

- 深/浅两套界面截图核对：布局一致，浅色下按钮、边框、卡片可读。
- 编辑模式点主按钮只保存；演奏模式点主按钮开始播放，再点停止。
- `Shift + 滚轮` 缩放后鼠标附近音高不跳；播放开始时黄框居中。

## 结论

三项需求与 antd 细化均完成；214 项测试通过，exe 重新打包并启动冒烟。
