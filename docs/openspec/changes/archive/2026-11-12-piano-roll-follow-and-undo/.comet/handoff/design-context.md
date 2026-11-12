# Comet Design Handoff

- Change: piano-roll-follow-and-undo
- Phase: design
- Mode: compact
- Context hash: 6dbcca9fd7141ae21b273932fe7c030b856f14f2922834cf0571b59b30f2fdbc

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/piano-roll-follow-and-undo/proposal.md

- Source: docs/openspec/changes/piano-roll-follow-and-undo/proposal.md
- Lines: 1-19
- SHA256: fc1793b2dba8edcb9764e40449f232f8924550c0b48b135ba9d8e2c290feb680

```md
# 播放跟随与撤销/前进

## Why

播放时铺面不会自动滚动，长曲听到后半段就看不到辅助线；编辑时没有撤销，拖错一个音符或误删整段只能手动恢复，风险很高。

## What Changes

- **播放跟随**：播放进行中，钢琴窗按「翻页式」跟随播放辅助线——辅助线超过视口右侧 80% 时，横向滚动整页前移，让辅助线回到视口左侧约 20% 处；不播放时不自动滚动。
- **撤销 / 前进**：编辑模式下支持 Ctrl+Z 撤销、Ctrl+Shift+Z 前进，覆盖所有铺面内容变更（新增/删除/移动/改时长/粘贴/剪切/八度与半音移调/曲谱优化，以及 BPM 改变引起的音符缩放），保留最近 50 步。
- 撤销恢复音符、BPM、量化与标尺网格，并把播放辅助线恢复到该步记录的位置。
- 演奏模式与播放中禁用撤销/前进；回到编辑模式后历史仍可继续使用。
- 新操作会清空前进栈；撤销后不修改内容不算新操作。

## Impact

- `piano_roll.py`：历史快照与撤销/前进信号、播放跟随滚动、只读时的快捷键拦截。
- `gui.py`：历史管理（音符 + BPM + 拍号 + 播放辅助线）、BPM 变更入栈、应用快照后重建网格与按钮状态。
- 不改变播放数据、play_code 生成、播放列表与导出逻辑。

```

## docs/openspec/changes/piano-roll-follow-and-undo/design.md

- Source: docs/openspec/changes/piano-roll-follow-and-undo/design.md
- Lines: 1-67
- SHA256: 6eedccc064cd5b7ce1bb02d13514f7d9688debf3b79e72e05b6f3e69ce806a2a

```md
# Design

行为需求以 `specs/piano-roll-follow-and-undo/spec.md` 为准。

## Context

- 所有铺面内容变更最终都会触发 `_PianoRollCanvas.notesChanged`：新增/删除/拖动/调整时长/粘贴/剪切/八度/移调/曲谱优化/BPM 缩放。
- BPM 与拍号、量化网格保存在 `gui`，撤销需要同时恢复这些状态。
- 播放进度通过 `gui.on_play_progress → piano_roll.set_playhead` 驱动。
- 画布已有 `_read_only`（演奏模式/播放中）与横向滚动条。

## Decisions

### 1. 历史放在 GUI，快照包含音符 + BPM + 拍号 + 辅助线

`gui` 维护：

```python
self._undo_stack = []   # 每项: {"notes": [...], "bpm": float, "signature": (n,d), "playhead": float}
self._redo_stack = []
self._history_limit = 50
self._history_applying = False
```

- 初始加载完成后记录基线（同时保存初始快照用于判断“未修改”）。
- `on_piano_roll_notes_changed` 中：若非 `_history_applying`，把当前状态压入 undo（去重：与栈顶相同则跳过），清空 redo，并维护 50 步上限。
- BPM 变更（`on_bpm_changed`）先记录“变更前”快照？为避免遗漏，统一在变更后由 `notesChanged` 记录当前状态即可；但撤销需要一个“上一个状态”。因此栈中保存的是**每次变更后的状态**，另存一个 `_history_current`；撤销 = 把当前状态推入 redo，从 undo 弹出上一状态并应用。
- 应用快照：设置 `_history_applying=True`，`piano_roll.set_notes(snapshot["notes"])`、`current_bpm = snapshot["bpm"]`、更新 BPM 框与拍号网格/量化、`set_playhead_anchor(snapshot["playhead"])`，最后 `_history_applying=False`；`piano_roll_dirty` 按快照与基线是否相同重算。

### 2. 画布只负责转发快捷键与提示状态

- `_PianoRollCanvas.keyPressEvent`：Ctrl+Z（无 Shift）→ 发 `undoRequested`；Ctrl+Shift+Z → `redoRequested`；`_read_only` 时不处理。
- `PianoRollWidget` 透传两个信号；GUI 连接到自己处理器。
- 画布不保存历史，避免与 GUI 的 BPM 状态分裂。

### 3. 播放翻页跟随

- 画布新增 `follow_playhead()`：读取 `_playhead_display_seconds` 的视口 x；若 `x > viewport_width * 0.8`，把横向滚动值设为「辅助线时间对应像素 − viewport_width * 0.2」并夹紧到滚动范围。
- `set_playhead(seconds)` 在 `_read_only`（播放中）时调用 `follow_playhead()`；手动定位（标尺）不触发。
- 不改变 `ensureVisible` 用于非播放场景的行为。

### 4. 未保存标记与历史

- 维护 `_history_baseline`（导入时的快照）。
- 每次应用快照或记录后比较当前状态与基线：相同则 `piano_roll_dirty=False` 并禁用保存，否则为 True。

### 5. 快捷键冲突

- Ctrl+Z/Ctrl+Shift+Z 在画布有焦点时生效；不在 GUI 全局注册，避免影响日志/搜索输入框。
- 演奏模式与播放中由 `_read_only` 拦截。

## Risks / Trade-offs

- **快照内存**：每步复制全部音符；大曲目（数千音符）×50 可能占用较大。→ 50 步上限；后续可改为差量命令。
- **选择丢失**：撤销后不恢复选中集合，用户需重新选择。→ 避免在恢复时触发选中态不一致；规格未要求。
- **播放中禁用撤销**：避免音频与数据不同步。
- **滚动干扰**：翻页阈值 80% 与回位 20% 是经验值，规格已固定。

## Test Strategy

- 纯 UI（offscreen）：编辑后 Ctrl+Z 恢复、Ctrl+Shift+Z 重做、演奏模式忽略、50 步上限、新操作清空 redo、撤销恢复 BPM/辅助线/未保存标记。
- 播放跟随：模拟 set_playhead 超过 80% 阈值，断言滚动值变化；阈值内不变；停止后不跟随。
- 回归：现有 141 项测试。

## Open Questions

无。

```

## docs/openspec/changes/piano-roll-follow-and-undo/tasks.md

- Source: docs/openspec/changes/piano-roll-follow-and-undo/tasks.md
- Lines: 1-28
- SHA256: 5815201905051fad923dc767f427c213bcd814dc398e5909e8e47f24b8025f6d

```md
# Tasks

## 1. 画布信号与播放跟随

- [ ] 1.1 画布新增 `undoRequested` / `redoRequested` 信号，Ctrl+Z / Ctrl+Shift+Z 转发（只读时不处理）；`PianoRollWidget` 透传 <!-- comet-task:68285e47-58da-4c9d-a028-a4aadb1e933f -->
- [ ] 1.2 画布新增 `follow_playhead()`：辅助线超过视口 80% 时整页滚动到左侧 20%；`set_playhead` 在播放期间调用 <!-- comet-task:7932c213-5ec3-4288-8dbe-c34ca97f6f62 -->
- [ ] 1.3 UI 测试：阈值内不滚动、超过阈值滚动、停止后不跟随 <!-- comet-task:2d23051f-f5fc-4875-960c-0c585546ae80 -->

## 2. 历史管理

- [ ] 2.1 GUI 新增历史栈（音符/BPM/拍号/辅助线，50 步）与基线快照；`notesChanged` 记录步骤并清空 redo <!-- comet-task:1468bf7e-bed5-42dd-b98e-8a21440e7f22 -->
- [ ] 2.2 实现 `undo` / `redo`：应用快照、重建网格与 BPM 框、恢复辅助线、按基线重算未保存标记 <!-- comet-task:cf6265bb-cdd9-4e59-8b1b-8bd1934c15a0 -->
- [ ] 2.3 BPM 变更入栈，撤销后 BPM 与标尺/量化同步恢复 <!-- comet-task:7bd2571d-d34b-467a-933a-2a4bd0da58e0 -->

## 3. 快捷键与只读

- [ ] 3.1 GUI 连接画布信号；演奏模式/播放中忽略快捷键 <!-- comet-task:d7633237-774a-480a-afe4-8f5981990340 -->
- [ ] 3.2 手动验证：Ctrl+Z 撤销删除/移动/粘贴/曲谱优化/BPM，Ctrl+Shift+Z 重做 <!-- comet-task:c9c6be4d-ccb6-40af-ad94-11329987558e -->

## 4. 边界与历史上限

- [ ] 4.1 新操作清空前进栈；撤销不记录为新步骤；连续 60 次编辑最多撤销 50 步 <!-- comet-task:df9ea79b-eb70-40e3-9c9d-5285652a2adc -->
- [ ] 4.2 UI 测试覆盖上述边界与「撤销到初始状态后未保存标记消失」 <!-- comet-task:ba474501-5bc3-4ac5-86ac-cb2b3f6b3821 -->

## 5. 集成验证

- [ ] 5.1 `.venv\Scripts\python.exe -m unittest discover -s tests -v` 全部通过 <!-- comet-task:63bc5023-6a0b-42e9-b101-392b2af1c165 -->
- [ ] 5.2 手动：长曲播放观察翻页跟随；编辑多种操作后撤销/重做 <!-- comet-task:4a51c866-31b0-4b93-a418-dd3080310c4e -->

```

## docs/openspec/changes/piano-roll-follow-and-undo/.openspec.yaml

- Source: docs/openspec/changes/piano-roll-follow-and-undo/.openspec.yaml
- Lines: 1-2
- SHA256: 81efc95b309487579cc63ceff200744cbd9fab2401597cbbdcf38d0cb54bace8

```md
schema: spec-driven
created: 2026-11-12

```

## docs/openspec/changes/piano-roll-follow-and-undo/specs/piano-roll-follow-and-undo/spec.md

- Source: docs/openspec/changes/piano-roll-follow-and-undo/specs/piano-roll-follow-and-undo/spec.md
- Lines: 1-78
- SHA256: 78713375f76ab1d27e3e699dc7f55d2176960b3508bff5d2a70cfd0eb1cb5c18

```md
# Spec Delta

## Purpose

让钢琴窗在播放时自动跟随辅助线，并为铺面编辑提供撤销/前进。

## ADDED Requirements

### Requirement: 播放时翻页跟随辅助线

播放进行中，钢琴窗 SHALL 跟随播放辅助线横向滚动：当辅助线在视口中的横坐标超过视口宽度的 80% 时，横向滚动 MUST 整页前移，使辅助线回到视口左侧约 20% 的位置；未播放时 MUST NOT 自动滚动。用户手动滚动的权宜行为不作为本次要求。

#### Scenario: 辅助线超过右侧阈值

- **WHEN** 播放中辅助线移动到视口宽度的 80% 之后
- **THEN** 钢琴窗横向滚动一页，辅助线出现在视口左侧约 20% 处

#### Scenario: 辅助线在阈值内不滚动

- **WHEN** 播放中辅助线仍在视口 80% 以内
- **THEN** 横向滚动位置不变

#### Scenario: 停止播放后不再跟随

- **WHEN** 播放停止
- **THEN** 钢琴窗不再自动滚动

### Requirement: 撤销与前进快捷键

编辑模式下，Ctrl+Z SHALL 撤销最近一次内容变更，Ctrl+Shift+Z SHALL 前进（重做）最近一次被撤销的变更。演奏模式或播放进行中时，两个快捷键 MUST 被忽略且铺面不变。

#### Scenario: 撤销删除

- **WHEN** 删除选中的 3 个音符后按 Ctrl+Z
- **THEN** 3 个音符恢复到删除前的位置、音高与时长

#### Scenario: 前进恢复撤销

- **WHEN** 撤销一次移动后按 Ctrl+Shift+Z
- **THEN** 音符回到移动后的位置

#### Scenario: 演奏模式禁用

- **WHEN** 演奏模式下按 Ctrl+Z 或 Ctrl+Shift+Z
- **THEN** 铺面不发生变化

### Requirement: 撤销覆盖范围与步数

撤销历史 SHALL 覆盖所有铺面内容变更：新增、删除、移动、调整时长、粘贴、剪切、八度/半音移调、曲谱优化，以及 BPM 改变导致的音符时间缩放。历史 MUST 保留最近 50 步；产生新的内容变更时 MUST 清空前进栈。

#### Scenario: BPM 变更可撤销

- **WHEN** 把 BPM 从 120 改为 60 后按 Ctrl+Z
- **THEN** BPM 回到 120，音符时间与标尺网格恢复到修改前

#### Scenario: 新操作清空前进栈

- **WHEN** 撤销一步后执行新的编辑操作，再按 Ctrl+Shift+Z
- **THEN** 不恢复任何内容

#### Scenario: 超过 50 步只保留最近记录

- **WHEN** 连续执行 60 次编辑后连续撤销
- **THEN** 最多只能撤销最近 50 次，更早的状态不再可恢复

### Requirement: 撤销恢复状态完整性

撤销/前进应用快照时 SHALL 一并恢复音符、BPM、量化网格、标尺刻度与播放辅助线位置，并重新计算未保存标记（与初始加载状态相同则为未修改）。撤销本身 MUST NOT 被记录为新的历史步骤。

#### Scenario: 恢复播放辅助线

- **WHEN** 在辅助线位于 10 秒时执行一次编辑，然后把辅助线移到 20 秒并撤销该编辑
- **THEN** 音符恢复，辅助线回到 10 秒

#### Scenario: 撤销到初始状态

- **WHEN** 仅做了一次编辑并撤销
- **THEN** 铺面与刚导入时一致，未保存标记消失

```
