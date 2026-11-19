# Comet Design Handoff

- Change: simple-mode-and-ui-polish
- Phase: design
- Mode: compact
- Context hash: fcbebf4ba4994cc12c8f365e29754d2f0daf3982ae5fb59e1de08893f3c0858d

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/simple-mode-and-ui-polish/proposal.md

- Source: docs/openspec/changes/simple-mode-and-ui-polish/proposal.md
- Lines: 1-25
- SHA256: 18ceed7457199f58fa956bf8d47e878575897d68e88ed497643e1bab442516ff

```md
# 控制面板重排、列表体验与简单模式

## Why

- 主题/置顶/向导按钮分散在标题行和按钮行，操作时视线来回跳；左侧面板偏窄，长歌名看不全。
- 铺面编辑对只想“选曲 → 一键播放”的用户过于复杂，需要一个隐藏编辑功能的简单模式。
- 亮色主题下两个大面板外框的框线仍然偏深，与浅色背景不协调。

## What Changes

- **控制面板按钮另起一行**：将「简单模式」「亮色 / 深色」「置顶」「向导」放到标题行下方的同一行。
- **左侧栏加宽 25%**：350 → 438 像素；播放列表行前复选框改为带勾选标记；鼠标悬停歌名时缓慢循环滚动。
- **简单模式**：
  - 工具栏按钮与主题/置顶/向导同排，可切换简单/正常模式。
  - 启动简单模式：铺面编辑标签页隐藏；不保存未保存修改并清空铺面数据；演奏最低/最高键位映射固定为 Z / 7，钢琴音域绝对最低/最高键固定为 C2 / B5。
  - 简单模式在「删除选中」旁显示「▶️ 播放」：加载原始 MIDI → 对全部音符执行曲谱优化 → 保存优化后的 MIDI 与 play_code JSON → 直接播放。
  - 切回正常模式：重新加载未经优化的原始 MIDI，恢复铺面编辑标签页与映射控件。
- **向导**：把「简单模式」与「正常模式」分成两节说明，并补充新增按钮与交互。
- **亮色框线**：两个大面板背后的背景与框线改为浅色主题下的淡灰色。

## 影响范围

- `app/main_window.py`、`app/ui/playlist_page.py`、`app/ui/piano_page.py`、`app/ui/guide.py`、`app/ui/theme.py`、`app/ui/widgets.py`（新增勾选框与滚动标签）。
- `piano_roll/`：新增“对全部音符执行曲谱优化”的入口。
- 播放、资产生成与撤销逻辑复用现有实现。

```

## docs/openspec/changes/simple-mode-and-ui-polish/design.md

- Source: docs/openspec/changes/simple-mode-and-ui-polish/design.md
- Lines: 1-70
- SHA256: 8e2d7de28cb7e97651c5f3f053466544ef852d35366ca64e875cbe4606c7474a

```md
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

```

## docs/openspec/changes/simple-mode-and-ui-polish/tasks.md

- Source: docs/openspec/changes/simple-mode-and-ui-polish/tasks.md
- Lines: 1-25
- SHA256: 607f71ffb99437bef6b248840d3ef3cfcb8df8aa308d594530f3bdef36b474f7

```md
# Tasks

## 1. 控制面板与左侧栏

- [ ] 1.1 标题行只留标题，新增「简单模式/主题/置顶/向导」一行 <!-- comet-task:7a05b8ce-5135-41fe-825c-e39637ecb20b -->
- [ ] 1.2 左面板 350 → 438，splitter 比例同步 <!-- comet-task:6917d2af-d646-4fc6-89c7-f9f7fe9c9987 -->
- [ ] 1.3 新增 AntCheckBox（勾选标记）与 MarqueeLabel（悬停循环滚动），列表行接入 <!-- comet-task:210b611f-fb1c-4b70-b40f-2d3bcf32cd25 -->
- [ ] 1.4 亮色主题：centralWidget 背景与面板/分组框边框改为淡灰色 <!-- comet-task:f70d78eb-a304-4baf-b13b-81e0d6acbbd8 -->

## 2. 简单模式

- [ ] 2.1 简单模式切换：隐藏标签、丢弃修改并清空铺面、固定 Z/7、显示简单播放按钮 <!-- comet-task:3e90928c-0be4-4c74-9ad6-2e6f1787fc2d -->
- [ ] 2.2 画布新增 arpeggiate_all（全量优化） <!-- comet-task:1944219f-8bc3-4b1c-ad06-d14961a10aee -->
- [ ] 2.3 简单播放：重读原始 MIDI → 全量优化 → 保存资产 → 播放 <!-- comet-task:07a4b290-5940-43ea-90ba-074923eb2a37 -->
- [ ] 2.4 退出简单模式：恢复标签、恢复映射、重新加载原始 MIDI <!-- comet-task:802c37ed-6a63-488c-be56-53ee169bb64f -->

## 3. 向导

- [ ] 3.1 增加「简单模式」「正常模式」两个小节并更新新增按钮/交互说明 <!-- comet-task:77e55179-493b-4851-b40c-2eb7e6bc29de -->

## 4. 验证

- [ ] 4.1 测试：按钮行、侧栏宽度、勾选/滚动、简单模式全流程、亮色边框、向导内容 <!-- comet-task:4b52897f-931e-47ae-afae-a0fcf02a63d7 -->
- [ ] 4.2 完整测试通过 <!-- comet-task:5bf80e54-d77f-4938-ae3b-69fe77944eb5 -->
- [ ] 4.3 offscreen 截图核对简单模式与亮色主题；重新打包 exe <!-- comet-task:fec11f8d-9569-485e-9cb9-4604d0759b08 -->

```

## docs/openspec/changes/simple-mode-and-ui-polish/.openspec.yaml

- Source: docs/openspec/changes/simple-mode-and-ui-polish/.openspec.yaml
- Lines: 1-2
- SHA256: 4c809c0a23df2b5d2324425b77ae5ff9b6d93d0a0f8c42e9dc20695839cf2478

```md
schema: spec-driven
created: 2026-11-19

```

## docs/openspec/changes/simple-mode-and-ui-polish/specs/simple-mode/spec.md

- Source: docs/openspec/changes/simple-mode-and-ui-polish/specs/simple-mode/spec.md
- Lines: 1-49
- SHA256: 7a08faa1cb5f8a7e7913a1b21feb9a7c144d7eb0f2ee7d958025a791e5361329

```md
# Spec Delta：简单模式

## Purpose

为只想选曲播放的用户提供隐藏编辑功能的精简界面，并在播放前自动完成曲谱优化。

## ADDED Requirements

### Requirement: 简单模式切换

控制面板 SHALL 提供「简单模式」切换按钮。进入简单模式时：

- 「铺面编辑」标签页 MUST 从标签栏移除；
- 未保存的铺面修改 MUST 被静默丢弃，铺面数据 MUST 清空；
- 演奏最低/最高键位映射 MUST 固定为 Z / 7，钢琴音域的绝对最低/最高键 MUST 固定为 C2 / B5（对应黄色框 36–83），且不可修改；
- 播放列表「删除选中」旁 MUST 显示「▶️ 播放」按钮。

退出简单模式时：铺面编辑标签页 MUST 恢复，映射控件恢复可用，并重新加载未经优化的原始 MIDI。

#### Scenario: 进入简单模式

- **WHEN** 点击「简单模式」
- **THEN** 铺面编辑标签消失、铺面数据清空、键位映射显示 Z / 7 且不可改

#### Scenario: 切回正常模式

- **WHEN** 再次点击该按钮
- **THEN** 铺面编辑标签恢复，并加载原始 MIDI（不含简单模式下的优化结果）

### Requirement: 简单模式一键播放

简单模式的「▶️ 播放」SHALL 依次执行：

1. 从当前曲目的原始 MIDI 重新读取音符；
2. 对全部音符执行曲谱优化（1/32 拍琶音展开）；
3. 保存优化后的工作 MIDI 与 play_code JSON；
4. 读取 JSON 开始播放。

每次点击都从原始 MIDI 重新开始，重复点击不会叠加优化；播放过程中再次点击 MUST 不重启。

#### Scenario: 一键播放

- **WHEN** 选中曲目后在简单模式点击「▶️ 播放」
- **THEN** 先优化并保存，再开始播放，日志记录优化与保存

#### Scenario: 重复播放

- **WHEN** 播放结束后再次点击「▶️ 播放」
- **THEN** 从原始 MIDI 重新优化一次，结果与第一次相同

```

## docs/openspec/changes/simple-mode-and-ui-polish/specs/ui-grouping/spec.md

- Source: docs/openspec/changes/simple-mode-and-ui-polish/specs/ui-grouping/spec.md
- Lines: 1-39
- SHA256: a238486bb0ef60c05dc316760ba3ca1a12aa93fdf1c1cd49681d15b7ac201d5e

```md
# Spec Delta：控制面板与播放列表布局

## Purpose

把次要操作集中到一行，改善窄面板下的可读性与批量操作反馈。

## ADDED Requirements

### Requirement: 控制按钮集中一行

控制面板 SHALL 在标题行下方单独一行依次放置「简单模式」「亮色/深色」「置顶」「向导」按钮；这些按钮 MUST NOT 再出现在标题行或导入/新建/刷新按钮行。

#### Scenario: 按钮位置

- **WHEN** 打开主窗口
- **THEN** 标题行只有「🎛️ 控制面板」，下一行是简单模式/主题/置顶/向导四个按钮

### Requirement: 左侧栏与列表可读性

左侧面板宽度 SHALL 比原来的 350px 增加约 25%（438px）。播放列表行前复选框 SHALL 在勾选时显示勾选标记。歌名长度超过行宽时，鼠标悬停 SHALL 让歌名缓慢向左循环滚动；移出后 MUST 恢复静止。

#### Scenario: 勾选标记

- **WHEN** 勾选某一行
- **THEN** 复选框内显示勾选标记

#### Scenario: 悬停长歌名

- **WHEN** 鼠标停在超长歌名所在行
- **THEN** 歌名缓慢向左滚动，到末尾停顿后从头循环；移出后停止

### Requirement: 亮色主题框线

亮色主题下，两个大面板背后的背景 SHALL 使用浅色页面底色，面板与分组框的框线 MUST 使用淡灰色，而非深色。

#### Scenario: 切换到亮色

- **WHEN** 点击「亮色」
- **THEN** 面板外背景为浅色、框线为淡灰色，不再出现深色描边

```

## docs/openspec/changes/simple-mode-and-ui-polish/specs/usage-guide/spec.md

- Source: docs/openspec/changes/simple-mode-and-ui-polish/specs/usage-guide/spec.md
- Lines: 1-34
- SHA256: 7aef85d8d115250c8347a24047a9c07e96314199314ba684dbb5aa19c227e4dd

```md
# Spec Delta：使用向导

## Purpose

让向导同时覆盖简单模式与正常模式，并说明新增按钮与列表交互。

## MODIFIED Requirements

### Requirement: 使用向导入口与内容

控制面板 SHALL 提供「❓ 向导」按钮，点击后打开非模态说明窗口，窗口 MUST 可滚动并覆盖：

- 控制面板各按钮（含简单模式、主题、置顶、向导同排）
- 播放列表的选择/勾选/全选/删除/搜索排序与悬停滚动
- 铺面编辑三行工具栏
- 钢琴窗的编辑、缩放、播放辅助线与音域框
- 操作日志与常用快捷键

向导 MUST 将「简单模式」与「正常模式」分成独立小节：简单模式说明隐藏铺面编辑、固定键位与一键优化播放；正常模式说明完整的编辑与播放流程。

#### Scenario: 打开向导

- **WHEN** 点击控制面板「❓ 向导」
- **THEN** 打开说明窗口并显示上述分区内容，可滚动阅读

#### Scenario: 简单/正常模式分开说明

- **WHEN** 阅读向导
- **THEN** 能看到独立的「简单模式」与「正常模式」小节，各自说明可用功能

#### Scenario: 关闭向导

- **WHEN** 点击窗口内「关闭」
- **THEN** 说明窗口关闭，主界面保持不变

```
