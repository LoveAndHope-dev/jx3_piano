# 验收记录：simple-mode-and-ui-polish

## 环境

- Windows + Python 3.14 + PyQt5
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 245 tests ... OK`

## 变更

### 控制面板与左侧栏

- 标题行只保留「🎛️ 控制面板」。
- 新增 `panel_actions` 行，依次放置「🧩 简单模式」「☀️ 亮色 / 🌙 深色」「📌 置顶」「❓ 向导」。
- 左面板固定宽度 350 → 438（+25%），splitter 初始比例 `[438, 562]`。
- 列表行改为 `AntCheckBox + MarqueeLabel`：勾选时绘制白色勾选折线；歌名超出宽度时悬停以 40ms/步缓慢向左循环，末尾停顿后回到开头，移出立即复位。
- 新增 `app/ui/widgets.py`（`AntCheckBox`、`MarqueeLabel`），颜色读取 `theme.current_tokens()`。

### 简单模式（懒人模式）

- `app/simple_mode.py` 新增 `SimpleModeMixin`：
  - 进入：停止播放、静默丢弃未保存修改并清空铺面、移除「铺面编辑」标签页、映射固定 Z / 7、音域框固定 C2–B5（36–83）、显示「▶️ 播放」。
  - 简单播放：重读原始 MIDI → 全量曲谱优化（`arpeggiate_all`）→ 保存 edited MIDI 与 play_code JSON → 读取 JSON 播放；每次从原始 MIDI 重新开始，重复点击不叠加；播放中再次点击只提示不重启。
  - 退出：恢复标签页与映射控件，重新加载未经优化的原始 MIDI。
- `piano_roll/canvas.py` 新增 `arpeggiate_all`（临时全选复用 `arpeggiate_selected`，`finally` 恢复原选择），`piano_roll/widget.py` 转发。
- `app/ui/piano_page.py` 保存 `_piano_tab_widget` / `_piano_tab_index`；简单模式下映射下拉禁用。

### 亮色主题

- `centralWidget` 设置 `colorBgBase` 背景。
- `QFrame#leftPanel/rightPanel/controlPanel` 与 `QGroupBox` 边框统一改为 `colorBorder`（亮色 `#d9d9d9`）。
- 主题切换后刷新所有 `AntCheckBox`。

### 向导

- 新增「🧩 简单模式 / 正常模式」独立小节，分别说明隐藏铺面编辑、固定键位与一键优化播放，以及完整编辑流程。
- 控制面板说明改为新按钮行；播放列表补充勾选、悬停滚动与批量删除说明。

## 覆盖

| 场景 | 测试 |
| --- | --- |
| 四个控制按钮同一行、标题行只剩标题 | `test_control_actions_share_one_row` |
| 左栏加宽到 438 | `test_left_panel_is_twenty_five_percent_wider` |
| 行使用自绘复选框与滚动标签 | `test_playlist_rows_use_painted_checkbox_and_marquee_label` |
| 超长文字才滚动，移出停止 | `test_marquee_label_scrolls_only_for_overflowing_text` |
| 进入简单模式隐藏标签、清空、固定 Z/7 与 C2/B5 | `test_simple_mode_hides_tab_and_fixes_mapping` |
| 退出简单模式恢复标签与映射 | `test_simple_mode_exit_restores_tab_and_range_controls` |
| 简单播放顺序：优化 → 保存 → 播放 | `test_simple_play_optimizes_saves_then_plays` |
| 每次重读原始 MIDI（不叠加） | `test_simple_play_reads_original_each_time` |
| 播放中不重启 | `test_simple_play_ignored_while_playing` |
| 全量优化并保留原选择 | `test_arpeggiate_all_spreads_every_note_and_keeps_selection` |
| 只读时全量优化不生效 | `test_arpeggiate_all_is_noop_when_read_only` |
| 亮色 central 背景与面板/分组框淡灰边框 | `test_light_theme_central_background_and_panel_borders` |
| 向导包含简单/正常模式与 C2/B5 | `test_guide_opens_and_covers_areas` |
| 其余回归 | 既有 232 项 |

## 备注

- 进入简单模式会静默丢弃未保存修改（用户已确认）。
- 简单播放每次多一次 MIDI 解析，换取不叠加优化。
- exe 已重新打包（`28622ab`），构建产物已清理。
- offscreen 截图核对了亮色框架、简单模式标签隐藏与「▶️ 播放」按钮位置。
