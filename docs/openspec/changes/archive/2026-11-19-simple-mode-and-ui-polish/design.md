---
comet_change: simple-mode-and-ui-polish
role: technical-design
canonical_spec: openspec
archived-with: 2026-11-19-simple-mode-and-ui-polish
status: final
---

# Design

行为需求以 `specs/ui-grouping/spec.md`、`specs/simple-mode/spec.md`、`specs/usage-guide/spec.md` 为准。

## Context

- 控制面板标题行目前有主题与置顶，向导在导入/新建/刷新行；简单模式尚不存在。
- 左侧面板固定 350px；列表行是 `QCheckBox + QLabel`，勾选指示器由 QSS 实心填充；歌名不滚动。
- 主题令牌在 `app/ui/theme.py`；亮色下 `QFrame#leftPanel/rightPanel` 边框使用 `colorBorderSecondary`（很浅），主窗口背景由 `QMainWindow` 提供。
- 播放流程：`start_playing` 读取/按需重建 play_code；铺面优化入口在 `PianoRollCanvas.arpeggiate_selected`。

## Decisions

### 1. 控制按钮一行

- 标题行只保留「🎛️ 控制面板」。
- 新增 `panel_actions` 行：`[🧩 简单模式] [☀️ 亮色] [📌 置顶] [❓ 向导]`，全部小号按钮。
- 移除标题行的主题/置顶、按钮行的向导。

### 2. 左侧栏与列表

- 左面板固定宽度 438（350×1.25），splitter 初始比例 [438, 562]。
- 新增 `app/ui/widgets.py`：
  - `AntCheckBox`：自绘 14px 圆角方框与白色勾选折线，颜色读取 `theme.current_tokens()`；主题切换时统一 `update()`。
  - `MarqueeLabel`：文字宽度超出时，悬停启动 40ms 定时器，每步左移 1px；到末尾（宽度+40px 间隔）停顿 1s 后回到 0 循环；移出停止并复位到从头显示。
- 行控件改为 `AntCheckBox + MarqueeLabel`；行 `enterEvent/leaveEvent` 控制滚动。

### 3. 简单模式

- 字段：`self.simple_mode`、`self._piano_tab_widget`、`self._piano_tab_index`。
- 切换（`on_simple_mode_toggled`）：
  - 进入：停止播放；丢弃未保存标记（不保存）；`piano_roll.set_notes([])`、清空历史/基线；`right_tabs.removeTab(indexOf(piano_tab))`；映射下拉固定 Z/7、音域框 36–83 并禁用下拉；显示简单播放按钮；`self.simple_mode=True`。
  - 退出：隐藏简单播放按钮；在索引 0 重新插入铺面编辑页；`self.simple_mode=False`；`_set_range_controls_enabled` 恢复下拉；若 `current_midi_path` 存在则 `_load_piano_roll(current_midi_path)` 重新读取原始 MIDI（同时把未优化资产写回）。
- `_set_range_controls_enabled`：简单模式下始终保持 low/high 下拉禁用，其他控件按参数。
- 简单播放按钮放在列表操作行「删除选中」之后，仅简单模式可见；按钮连接 `on_simple_play_clicked`。
- `on_simple_play_clicked`：
  1. 正在播放则提示并返回；
  2. 解析当前曲目路径（列表当前项或 `current_midi_path`）；
  3. 用 `MidiToKeysConverter` 重新读取原始 MIDI 音符，`piano_roll.set_notes(notes)`；
  4. 固定 Z/7 映射与音域框；
  5. `piano_roll.arpeggiate_all(60/current_bpm)`（新增画布方法：临时全选调用现有优化逻辑后恢复选择）；
  6. `_save_current_play_assets()` 保存优化后的 edited MIDI 与 JSON；标记不脏、清历史基线；
  7. `start_playing()`。
- `PianoRollCanvas.arpeggiate_all` 复用 `arpeggiate_selected`，不复制算法。

### 4. 亮色框线

- `central_widget.setObjectName("centralWidget")`，QSS 为其设置 `colorBgBase` 背景，确保面板后方的窗口底色随主题变化。
- `QFrame#leftPanel/rightPanel`、`QGroupBox`、`QFrame#controlPanel` 边框统一改为 `colorBorder`（亮色 `#d9d9d9`、深色 `#424242`），使亮色下是淡灰色而非深色。
- `apply_theme` 后刷新所有 `AntCheckBox`。

### 5. 向导

- 增加「简单模式」与「正常模式」两个小节；补充控制面板按钮行、勾选/悬停滚动、简单播放说明。

## Risks

- 简单模式会丢弃未保存修改（用户已确认静默丢弃）。
- 简单播放在每次点击时重读原始 MIDI，长曲多一次解析开销。
- 自绘复选框需跟随主题更新；MarqueeLabel 使用定时器，需在移出/销毁时停止。
- 亮色边框颜色统一可能让深色主题下边框更明显，属可接受变化。

## Test Strategy

- 控制面板四按钮同一行；左面板宽度 438。
- 复选框勾选标记（自绘状态可断言 `isChecked` 与控件类型）；悬停滚动启动/停止（调用 `start/stop` 或定时器状态）。
- 简单模式：隐藏/恢复标签、清空铺面、固定映射、简单播放调用优化+保存+播放、重复点击幂等、退出重载原始 MIDI。
- 亮色：centralWidget 背景与面板边框颜色来自 `colorBorder`。
- 向导内容包含简单/正常小节。
- 既有 234 项回归。
