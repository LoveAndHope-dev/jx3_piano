---
comet_change: piano-roll-follow-and-undo
role: technical-design
canonical_spec: openspec
archived-with: 2026-11-12-piano-roll-follow-and-undo
status: final
---

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
