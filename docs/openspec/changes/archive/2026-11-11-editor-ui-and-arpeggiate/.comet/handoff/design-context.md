# Comet Design Handoff

- Change: editor-ui-and-arpeggiate
- Phase: design
- Mode: compact
- Context hash: f72953c0b1ae83e4211ed7154dfd4be40e0ed1abeef22e24c68db4b366953595

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/editor-ui-and-arpeggiate/proposal.md

- Source: docs/openspec/changes/editor-ui-and-arpeggiate/proposal.md
- Lines: 1-34
- SHA256: 4e6f265b019fce04e3a64e5fa0ff7b96e47267ed7107abd65afeb6c3075b14b7

```md
# 编辑工具栏体验、默认音域与曲谱优化

## Why

铺面编辑器的工具栏在实际使用中有几处不顺手：编辑模式下仍能点「弹奏」，容易误触；映射控件文案与实际含义不符；BPM 输入框样式与下拉框不一致、工具栏一行过挤；删除只能对整个列表操作，无法逐曲移除；默认映射与黄色框的音域与常用演奏习惯不符；另外缺少对和弦/琶音的批量整理手段。

## What Changes

- 编辑模式下禁用「弹奏」按钮；只有演奏模式下可播放（播放中仍显示「停止」）。
- 播放列表每行末尾增加「🗑」删除按钮，直接移除该行曲目（保留磁盘文件、清缓存逻辑不变）；移除列表右侧原来的删除按钮。
- 文案调整：「最低映射」→「演奏最低键位映射」；「最高映射」→「演奏最高键位映射」；「当前最低键」→「钢琴音域绝对最低键」；「当前最高键」→「钢琴音域绝对最高键」。
- BPM 输入框背景/边框样式与下拉框一致；「演奏最高键位映射」之后的控件换到工具栏第二行。
- 钢琴窗工具栏上方新增「曲谱优化」按钮：对当前选中音符执行琶音整理（脚本算法移植自 `release/谱子/arpeggiate.py`，并作为 `arpeggiate.py` 加入项目）。规则：把头部间距小于 1/32 拍的和弦音按音高从低到高、以 1/32 拍为间隔展开，结束时间保持不变，过短时补到最小时长。
- 默认值：「演奏最低键位映射」默认 Z，「演奏最高键位映射」默认 7；黄色映射框默认覆盖 C2～B2（MIDI 36～47）。
- 统一交互 UI：工具栏两行布局、控件高度与间距一致、输入框与下拉框同一深色风格、按钮 tooltip 与文案对齐。

## Capabilities

### New Capabilities

- `piano-roll-arpeggiate`：曲谱优化按钮与选中音符的琶音整理规则。
- `piano-roll-toolbar-layout`：工具栏两行布局、文案、样式、默认键位与默认映射框音域。

### Modified Capabilities

- `piano-roll-editing-modes`：编辑模式下「弹奏」按钮禁用。
- `playlist-management`：删除入口改为每行末尾的按钮。

## Impact

- `piano_roll.py`：默认映射框音域相关接口（若需要按音高直接设定范围）。
- `gui.py`：工具栏重排与文案、BPM 样式、弹奏按钮启用规则、播放列表逐行删除、曲谱优化按钮与调用。
- 新增 `arpeggiate.py`：可单测的琶音算法。
- 不改变播放、BPM 计算、MIDI 导出与文件导入逻辑。

```

## docs/openspec/changes/editor-ui-and-arpeggiate/design.md

- Source: docs/openspec/changes/editor-ui-and-arpeggiate/design.md
- Lines: 1-97
- SHA256: b2c7d92aa848e035ebbafef42d0088a14a7067fc6f0ffaf795f3b6caba0d5cd7

[TRUNCATED]

```md
---
comet_change: editor-ui-and-arpeggiate
role: technical-design
canonical_spec: openspec
---

# Design

行为需求以 `specs/piano-roll-arpeggiate`、`specs/piano-roll-toolbar-layout` 以及两份 MODIFIED spec 为准。

## Context

- 工具栏目前是单行 `QHBoxLayout`，控件拥挤；BPM 使用 `QDoubleSpinBox` 默认浅色样式。
- 播放列表使用 `QListWidget`，删除按钮在列表右侧；`refresh_play_list` 重建条目。
- 演奏/编辑模式由 `_sync_roll_mode()` 统一同步；`play_btn` 目前始终可用。
- 映射下拉框来自 `get_natural_key_ladder()`，标签含 Z/A/J/7；`_pitch_for_label` 找不到时回退到最低音高。
- 黄框范围由 `set_instrument_range(low, high)` 控制，当前默认取自映射下拉框。
- `release/谱子/arpeggiate.py` 是文件级 MIDI 琶音脚本，逻辑可直接移植为内存函数。

## Decisions

### 1. 新增 `arpeggiate.py`（内存版）

```python
MIN_NOTE_DURATION = 0.05

def arpeggiate_notes(notes, selected_ids, seconds_per_beat):
    """对选中音符按 1/32 拍窗口与步长展开琶音，返回新列表。"""
```

- `window = step = seconds_per_beat / 32`。
- 选中音符按 `start` 排序；以组内第一个为锚点，`start < anchor + window` 归入同组；级联规则与脚本一致（`start < anchor + (count)*step`）。
- 组内按 `pitch` 升序，第 k 个音符 `start = anchor + k*step`。
- 时长保持不变：只修改起始时间，结束时间随之后移；不改音高。极短音符（<0.05s）同样只后移，不做时长补足。
- 未选中音符原样返回副本；不修改输入。

### 2. 画布接口与按钮

- `_PianoRollCanvas.arpeggiate_selected(seconds_per_beat)`：调用上述函数、替换 `_notes`、更新图元与场景宽度、`notesChanged`。
- `PianoRollWidget` 透传。
- GUI 在工具栏上方新增一行，放「🪄 曲谱优化」按钮；点击时若 `selected_ids` 为空则写日志提示并返回，否则按当前 `seconds_per_beat = (60/BPM)*(4/分母)` 调用。
- 按钮启用条件：编辑模式（非只读）；播放中自动禁用。每次点击后由 `notesChanged` 触发未保存标记。

### 3. 弹奏按钮与模式绑定

- `_sync_roll_mode()` 追加：`self.play_btn.setEnabled(play_mode or self.is_playing)`。
- 播放中保持可用（文本为「停止」）；停止后按当前模式恢复。

### 4. 播放列表逐行删除

- `refresh_play_list` 为每个条目 `setItemWidget(item, row_widget)`：`QLabel(名称)` + `QPushButton("🗑")`，按钮回调 `on_delete_play_item(item)`。
- 删除按钮改为接收条目参数；`on_delete_play_item` 不再读取 `currentItem`（保留兼容：无参数时取当前项）。
- 移除原列表右侧删除按钮；`play_delete_btn` 相关启用逻辑删除。
- 条目仍保存路径与原始文件名到 `Qt.UserRole`、`Qt.UserRole + 1`，选中恢复逻辑不变。

### 5. 工具栏两行与文案

- `_setup_piano_roll_tab` 改为 `QVBoxLayout`：
  - 顶部动作行：`🪄 曲谱优化`
  - 第一行：标题、未保存、弹奏、保存、模式、最低映射、最高映射
  - 第二行：绝对最低键、绝对最高键、量化、BPM
- 文案按 spec 更新；`QLabel("…:")` 的冒号统一为中文全角。

### 6. 样式

- 为 `QDoubleSpinBox` 增加与 `QComboBox` 相同的 `background/border/color/padding` 规则（含 `:focus`、`::up-button`、`::down-button` 的简化处理）。
- 统一按钮 `padding: 2px 10px`，保持上一轮高度。
- 新按钮加 tooltip：「对选中音符做琶音整理（1/32 拍展开）」。

### 7. 默认值

- `_populate_range_combos` 与 `_reset_instrument_range`：映射默认 Z（36）与 7（83）。
- 黄框默认范围：`set_instrument_range(36, 47)`（C2～B2），与映射下拉框解耦；切换曲目时同样重置为该范围。
- 保持 `_refresh_range_display` 显示当前框体的绝对键名。

## Risks / Trade-offs

- **琶音只能作用于选中**：未选中时按钮无效果并提示；符合需求但可能被误认为无响应。→ 日志提示明确。
- **逐行删除误触**：每行都有按钮，点错会隐藏该曲目；保留确认框，且磁盘文件不删、可一键恢复。
- **黄框默认与映射解耦**：播放时的音域筛选由黄色框（`get_instrument_range()`，默认 C2～B2）决定；映射下拉框只决定移调锚点与目标最低键。两者含义不同，文档与提示中需说明。

```

Full source: docs/openspec/changes/editor-ui-and-arpeggiate/design.md

## docs/openspec/changes/editor-ui-and-arpeggiate/tasks.md

- Source: docs/openspec/changes/editor-ui-and-arpeggiate/tasks.md
- Lines: 1-40
- SHA256: fe38c6ae977cced39c792186adbdcaedddd251f89bb88308c157848eef9350a6

```md
# Tasks

## 1. 琶音算法

- [x] 1.1 新增 `arpeggiate.py`：`arpeggiate_notes(notes, selected_ids, seconds_per_beat)`，窗口/步长 = 1/32 拍，组内按音高展开，结束时间不变、过短钳制；新增 `tests/test_arpeggiate.py` 覆盖和弦展开、单音、两组独立、未选中不变、输入不变 <!-- comet-task:eadc5b36-ba7a-484e-92fa-53164fcd0e33 -->

## 2. 曲谱优化入口

- [x] 2.1 `_PianoRollCanvas.arpeggiate_selected(seconds_per_beat)` + `PianoRollWidget` 透传：替换音符、重排图元、扩展场景、发出 `notesChanged` <!-- comet-task:827e3343-c915-4100-b031-3ccb1ef50a93 -->
- [x] 2.2 工具栏上方新增「🪄 曲谱优化」按钮（含 tooltip）：无选中时日志提示；有选中时按当前 BPM/拍号计算拍长并调用；编辑模式可用、播放中禁用 <!-- comet-task:caeb6de3-d649-4ea6-8ebf-7ea74d950f64 -->

## 3. 弹奏按钮与模式

- [x] 3.1 `_sync_roll_mode` 增加弹奏按钮启用规则：编辑模式禁用、演奏模式启用、播放中保持可用；验证切模式与播放开始/停止 <!-- comet-task:42758c54-40a2-4003-b6b5-b17f697bebfa -->

## 4. 播放列表逐行删除

- [x] 4.1 `refresh_play_list` 改为每行 `QLabel + 🗑` 的 item widget，删除按钮定位到该行曲目；移除列表右侧删除按钮及其启用逻辑 <!-- comet-task:fb4a70cb-dee4-4f9b-bf29-9ec4ba98cf4e -->
- [x] 4.2 验证逐行删除：删除未加载/当前曲目、取消、刷新后仍隐藏、恢复全部 <!-- comet-task:d5db9f7f-2e68-464d-9660-966c13271a46 -->

## 5. 工具栏文案、两行布局、样式与默认值

- [x] 5.1 文案改为「演奏最低键位映射 / 演奏最高键位映射 / 钢琴音域绝对最低键 / 钢琴音域绝对最高键」 <!-- comet-task:6f18ef00-6814-4f90-9d4e-9ffb02afeacc -->
- [x] 5.2 工具栏拆两行：第一行到「演奏最高键位映射」，第二行放绝对键、量化、BPM；统一间距与高度 <!-- comet-task:a7516f85-2992-4690-831d-1dca2f70107a -->
- [x] 5.3 `QDoubleSpinBox` 增加与下拉框一致的深色 QSS（背景、边框、圆角、文字、focus） <!-- comet-task:49702f21-e44b-4187-8ba7-141143bf7541 -->
- [x] 5.4 默认映射改为 Z（36）/7（83）；黄框默认范围改为 C2～B2（36～47），切换曲目时同样重置 <!-- comet-task:e27f562d-415f-4a0c-b20f-0ed693d883d4 -->

## 6. 交互 UI 统一

- [x] 6.1 检查按钮 padding、控件间距、标签冒号与 tooltip 一致性；新按钮不遮挡既有控件 <!-- comet-task:36395a90-2c1f-494c-ad39-2025acbb794a -->
- [x] 6.2 手动走查：两行布局、BPM 样式、默认映射与黄框、逐行删除、曲谱优化、编辑模式弹奏禁用 <!-- comet-task:c34eac44-a038-47a1-9174-b80c706f7ad2 -->

## 7. 集成验证

- [x] 7.1 `.venv\Scripts\python.exe -m unittest discover -s tests -v`：既有 114 项 + 新增全部通过 <!-- comet-task:7c7aca3f-ffc5-433e-9d68-07318fec5e12 -->
- [x] 7.2 记录验收结果到 `docs/superpowers/reports/2026-11-11-editor-ui-and-arpeggiate-verification.md` <!-- comet-task:82ead7d3-8484-41da-9ae1-f0aa552d6a06 -->

## Workflow follow-up

- 完成 Verify 后按 Comet 交付流程归档或交付，具体方式由用户确认。

```

## docs/openspec/changes/editor-ui-and-arpeggiate/.openspec.yaml

- Source: docs/openspec/changes/editor-ui-and-arpeggiate/.openspec.yaml
- Lines: 1-2
- SHA256: b8f20def63a86ae4075c5499ff9ed413265d8704692a8493712424dc3f28d8e3

```md
schema: spec-driven
created: 2026-11-11

```

## docs/openspec/changes/editor-ui-and-arpeggiate/specs/piano-roll-arpeggiate/spec.md

- Source: docs/openspec/changes/editor-ui-and-arpeggiate/specs/piano-roll-arpeggiate/spec.md
- Lines: 1-45
- SHA256: 5217af2eba5a5370c59d82c6f494170b7a7fc380ef5de9a739ec40aa61b01d58

```md
# Spec Delta

## Purpose

在演奏模式下才允许播放；把「曲谱优化」做成对选中音符的琶音整理动作。

## ADDED Requirements

### Requirement: 曲谱优化按钮

钢琴窗工具栏上方 SHALL 提供「曲谱优化」按钮。点击后 MUST 对当前选中的全部音符执行琶音整理；无选中音符时按钮禁用或给出提示且不修改铺面；执行后 SHOULD 标记铺面为未保存。

#### Scenario: 对和弦执行优化

- **WHEN** 选中一组起始时间相同或接近的音符并点击「曲谱优化」
- **THEN** 这些音符按音高从低到高被展开成等间隔琶音，未选中的音符保持不变，铺面显示未保存

#### Scenario: 没有选中音符

- **WHEN** 没有选中任何音符时点击「曲谱优化」
- **THEN** 铺面不发生变化

### Requirement: 琶音整理规则

琶音整理 SHALL 以「1/32 拍」为判定窗口与步长（拍长由当前 BPM 与拍号决定）：把起始时间相差小于该窗口的选中音符视为同一组（若展开后的组尾与后续音符重叠，MUST 继续并入该组），按音高从低到高依次把起始时间设为 `锚点 + k × 步长`；每个音符的时长 MUST 保持不变（结束时间随起始时间一同后移），音高不变。组与组之间互不影响。

#### Scenario: 三个和弦音展开

- **WHEN** 选中 3 个同时起始、时长相同的音符（低、中、高）且拍长为 1 秒
- **THEN** 起始时间依次为锚点、锚点 + 1/32 秒、锚点 + 2/32 秒，时长与音高不变

#### Scenario: 极短音符同样只后移

- **WHEN** 选中的和弦音时长只有 0.03 秒
- **THEN** 起始时间仍按 1/32 拍依次后移，时长保持 0.03 秒

#### Scenario: 单音符不处理

- **WHEN** 只选中 1 个音符并执行优化
- **THEN** 该音符不发生变化

#### Scenario: 分组相互独立

- **WHEN** 有两组相距较远的和弦同时被选中
- **THEN** 两组各自以自身锚点展开，互不影响

```

## docs/openspec/changes/editor-ui-and-arpeggiate/specs/piano-roll-editing-modes/spec.md

- Source: docs/openspec/changes/editor-ui-and-arpeggiate/specs/piano-roll-editing-modes/spec.md
- Lines: 1-17
- SHA256: 308a32ed2a0591a515bc45e68ca9823cb3cf39e98c423403b6a51178bc271ac8

```md
# Spec Delta

## MODIFIED Requirements

### Requirement: 演奏模式与编辑模式切换

工具栏 SHALL 提供「🎹 演奏模式 / ✏️ 编辑模式」切换按钮。演奏模式 MUST 显示黄色映射框、把铺面切换为只读，并启用「弹奏」按钮；编辑模式 MUST 隐藏映射框、恢复编辑，并禁用「弹奏」按钮。按钮文案 MUST 反映「点击后会进入的模式」（编辑中显示「🎹 演奏模式」，演奏中显示「✏️ 编辑模式」）。

#### Scenario: 切到演奏模式

- **WHEN** 编辑模式下点击「🎹 演奏模式」
- **THEN** 黄色映射框出现，铺面进入只读，按钮文案变为「✏️ 编辑模式」，「弹奏」按钮变为可用

#### Scenario: 切回编辑模式

- **WHEN** 演奏模式下点击「✏️ 编辑模式」
- **THEN** 黄色映射框隐藏，铺面恢复可编辑，按钮文案变为「🎹 演奏模式」，「弹奏」按钮变为禁用

```

## docs/openspec/changes/editor-ui-and-arpeggiate/specs/piano-roll-toolbar-layout/spec.md

- Source: docs/openspec/changes/editor-ui-and-arpeggiate/specs/piano-roll-toolbar-layout/spec.md
- Lines: 1-57
- SHA256: edbd8a595f2aafedf2c83b66096bce7bb095758ee0bd898c213bac2880ae5632

```md
# Spec Delta

## Purpose

统一铺面工具栏的文案、布局、样式与默认值，使习惯演奏的键位映射与映射框范围开箱即用。

## ADDED Requirements

### Requirement: 工具栏文案

工具栏 SHALL 使用以下文案：「演奏最低键位映射」「演奏最高键位映射」「钢琴音域绝对最低键」「钢琴音域绝对最高键」。其余控件（量化、BPM、弹奏、保存、演奏/编辑模式）文案保持不变。

#### Scenario: 文案展示

- **WHEN** 打开铺面编辑页
- **THEN** 四个映射相关标签显示为新文案，不再出现「最低映射 / 最高映射 / 当前最低键 / 当前最高键」

### Requirement: 工具栏两行布局

工具栏 SHALL 分为两行：第一行包含标题、未保存标记、弹奏、保存、演奏/编辑模式、演奏最低键位映射与演奏最高键位映射；「演奏最高键位映射」之后的控件（钢琴音域绝对最低键、钢琴音域绝对最高键、量化、BPM）MUST 换到第二行，并保持左对齐与统一间距。

#### Scenario: 控件换行

- **WHEN** 打开铺面编辑页
- **THEN** 「钢琴音域绝对最低键」及其后的控件位于第二行，第一行在「演奏最高键位映射」后结束

### Requirement: BPM 输入框样式一致

BPM 数值框的背景、边框、圆角与文字颜色 SHALL 与量化/排序等下拉框保持一致，不再使用系统默认浅色样式。

#### Scenario: 样式一致

- **WHEN** 打开铺面编辑页
- **THEN** BPM 数值框与相邻下拉框呈现同一深色背景与边框风格

### Requirement: 默认键位映射与映射框音域

「演奏最低键位映射」默认 SHALL 为 Z（MIDI 36），「演奏最高键位映射」默认 SHALL 为 7（MIDI 83）。黄色映射框的默认可见范围 MUST 为 C2～B2（MIDI 36～47）；在未做任何手动调整时，框体应覆盖该音域。

#### Scenario: 默认映射

- **WHEN** 首次加载曲目且未修改映射
- **THEN** 最低键位下拉框为 Z、最高键位下拉框为 7

#### Scenario: 默认映射框范围

- **WHEN** 首次切换到演奏模式
- **THEN** 黄色框覆盖 C2 到 B2 之间的音高行

### Requirement: 交互界面一致性

工具栏控件 SHALL 保持统一高度与间距；新按钮 MUST 提供 tooltip 说明用途；新增控件不得遮挡或挤压既有控件，窗口缩小时允许换行。

#### Scenario: 新按钮提示

- **WHEN** 鼠标悬停在「曲谱优化」按钮上
- **THEN** 显示该按钮用途的提示

```

## docs/openspec/changes/editor-ui-and-arpeggiate/specs/playlist-management/spec.md

- Source: docs/openspec/changes/editor-ui-and-arpeggiate/specs/playlist-management/spec.md
- Lines: 1-27
- SHA256: 07e043a7131df3486640074867834f39ed95d36dd9938a1c4798ff68cddd2099

```md
# Spec Delta

## MODIFIED Requirements

### Requirement: 从列表移除曲目并清理缓存

播放列表的每一行曲目末尾 SHALL 提供「🗑」删除按钮（不再使用列表外侧的统一删除按钮）；点击该行按钮后 MUST 先从列表移除该曲目并写入持久化隐藏记录（磁盘 MIDI 文件保留），再判断它是否为当前加载曲目：是则清空铺面音符、播放辅助线、BPM 与播放相关缓存并停止播放。移除 MUST 有确认步骤，取消时不改变任何状态。

#### Scenario: 移除未加载的曲目

- **WHEN** 点击某个未加载曲目行末的「🗑」并确认
- **THEN** 该曲目从列表消失，磁盘文件仍在，当前铺面与播放状态不变

#### Scenario: 移除当前加载的曲目

- **WHEN** 点击当前正在编辑曲目行末的「🗑」并确认
- **THEN** 列表移除该曲目，铺面清空、播放辅助线回到 0、BPM 重置、未保存标记清除、保存按钮禁用

#### Scenario: 取消删除

- **WHEN** 在确认框中点击取消
- **THEN** 列表、缓存与磁盘文件都不发生变化

#### Scenario: 刷新或重启后仍移除

- **WHEN** 删除后刷新列表或重启程序
- **THEN** 被移除的曲目不再出现

```
