---
change: piano-roll-follow-and-undo
design-doc: docs/openspec/changes/piano-roll-follow-and-undo/design.md
base-ref: 1329635
archived-with: 2026-11-12-piano-roll-follow-and-undo
---

<!-- comet-task-authority: docs/openspec/changes/piano-roll-follow-and-undo/tasks.md -->

# 播放跟随与撤销/前进 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans. 任务状态以 tasks.md 为准；本计划只用 `comet-task-ref` 引用任务 ID。

**Goal:** 播放时钢琴窗翻页跟随辅助线；为铺面内容变更提供 Ctrl+Z / Ctrl+Shift+Z 撤销与前进（50 步，含 BPM）。

**Architecture:** 画布只发 `undoRequested`/`redoRequested` 并实现 `follow_playhead`；GUI 维护快照历史 {notes,bpm,signature,playhead} 并在 `notesChanged` 时记录；应用快照时抑制记录并重建网格与未保存标记。

**Spec:** `docs/openspec/changes/piano-roll-follow-and-undo/design.md`

## Global Constraints

- 演奏模式与播放中禁用撤销/前进；新操作清空 redo；最多 50 步。
- 不改变播放数据、play_code、播放列表与导出。
- 既有 141 项测试保持通过。

## Review Focus

- 撤销后 BPM、标尺、量化、辅助线、未保存标记全部一致。
- 撤销/前进本身不能入栈或清空对方栈。
- 翻页只发生在播放期且不越过滚动边界。
- 输入框（搜索）中的 Ctrl+Z 不受影响（快捷键只在画布焦点时生效）。

---

### Task 1: 画布快捷键信号

**Files:** `piano_roll.py`（`_PianoRollCanvas` 类属性、`keyPressEvent`、`PianoRollWidget`）

**Interfaces:** `undoRequested = pyqtSignal()`、`redoRequested = pyqtSignal()`；widget 透传同名信号

<!-- comet-task-ref:68285e47-58da-4c9d-a028-a4aadb1e933f -->

**Step 1:** 类属性加两个信号；`keyPressEvent` 在只读判断之后、Ctrl+A 之前处理 Ctrl+Z / Ctrl+Shift+Z（`event.key()==Qt.Key_Z`，有 Ctrl；Shift 区分），`event.accept()`。

**Step 2:** `PianoRollWidget.__init__` 赋值 `self.undoRequested = self._canvas.undoRequested`、`self.redoRequested = self._canvas.redoRequested`。

**Step 3:** `py_compile` 后提交 `feat(piano-roll): emit undo/redo requests`。

### Task 2: 播放翻页跟随

**Files:** `piano_roll.py`

**Interfaces:** `follow_playhead() -> None`；在 `set_playhead` 播放期调用

<!-- comet-task-ref:7932c213-5ec3-4288-8dbe-c34ca97f6f62 -->

**Step 1:** 实现：

```python
def follow_playhead(self) -> None:
    width = float(self.viewport().width())
    if width <= 0:
        return
    x = self.viewport_x_for_time(self._playhead_display_seconds)
    if x <= width * 0.8:
        return
    scene_x = self._time_to_x(self._playhead_display_seconds)
    bar = self.horizontalScrollBar()
    target = int(round(scene_x - width * 0.2))
    bar.setValue(max(bar.minimum(), min(bar.maximum(), target)))
```

**Step 2:** `set_playhead` 末尾在 `if self._read_only: self.follow_playhead()`（播放期由 GUI 置只读）。

**Step 3:** 提交 `feat(piano-roll): page-follow the playhead during playback`。

### Task 3: 历史核心

**Files:** `gui.py`

**Interfaces:** `_snapshot_state()`、`_states_equal(a,b)`、`_record_history()`、`_apply_history_state(state)`

<!-- comet-task-ref:1468bf7e-bed5-42dd-b98e-8a21440e7f22 -->

**Step 1:** `__init__` 增加 `_undo_stack=[]`、`_redo_stack=[]`、`_history_applying=False`、`_history_limit=50`、`_history_baseline=None`。

**Step 2:** 快照/比较/记录：
- snapshot: notes、bpm、signature、playhead
- equal: notes 列表相等 + bpm 差 <1e-9 + signature 相等
- record: applying 时返回；与 `_undo_stack[-1]` 相等则返回；append、裁剪到 50、清空 redo

**Step 3:** `_load_piano_roll` 成功后重置：`_undo_stack=[snapshot]`、`_redo_stack=[]`、`_history_baseline=snapshot`。

**Step 4:** `on_piano_roll_notes_changed` 末尾调用 `_record_history()`。

**Step 5:** 提交 `feat(gui): track undo history snapshots`。

### Task 4: 撤销/前进应用

**Files:** `gui.py`

**Interfaces:** `undo_last_edit()`、`redo_last_edit()`

<!-- comet-task-ref:cf6265bb-cdd9-4e59-8b1b-8bd1934c15a0 -->
<!-- comet-task-ref:7bd2571d-d34b-467a-933a-2a4bd0da58e0 -->

**Step 1:** undo：只读或 `len(_undo_stack)<=1` 返回；`cur=_undo_stack.pop()` 入 redo；apply(top)。redo：只读或 redo 空返回；state=redo.pop() 入 undo；apply(state)。

**Step 2:** apply：`_history_applying=True`；`piano_roll.set_notes(state["notes"])`；`current_bpm=state["bpm"]`；BPM 框回填（`_updating_bpm`）；`current_time_signature=state["signature"]`；`_reset` 网格用 `grid_seconds_for_bpm` → `set_measure_grid`/`set_beat_grid`；`_apply_quantize_grid`；`set_playhead_anchor(state["playhead"])`；`piano_roll_dirty = not equal(state, baseline)`；更新保存按钮与标记；`_history_applying=False`。

**Step 3:** 连接 `piano_roll.undoRequested/redoRequested` 到上述方法。

**Step 4:** 提交 `feat(gui): apply undo and redo states`。

### Task 5: 边界与测试

**Files:** `tests/test_piano_roll_ui.py`、`tests/test_playlist_gui.py`

<!-- comet-task-ref:2d23051f-f5fc-4875-960c-0c585546ae80 -->
<!-- comet-task-ref:d7633237-774a-480a-afe4-8f5981990340 -->
<!-- comet-task-ref:c9c6be4d-ccb6-40af-ad94-11329987558e -->
<!-- comet-task-ref:df9ea79b-eb70-40e3-9c9d-5285652a2adc -->
<!-- comet-task-ref:ba474501-5bc3-4ac5-86ac-cb2b3f6b3821 -->

**Step 1:** 画布测试：阈值内不滚动、超过阈值滚动到 20%、`read_only=False` 时不跟随。

**Step 2:** GUI 测试：删除后 Ctrl+Z 恢复、Ctrl+Shift+Z 重做、演奏模式忽略、新操作清空 redo、60 次编辑只保留 50 步、撤销到初始后 dirty=False、撤销恢复 BPM 与辅助线。

**Step 3:** 提交 `test: cover follow scroll and undo history`。

### Task 6: 集成验证

**Files:** 无新增

<!-- comet-task-ref:63bc5023-6a0b-42e9-b101-392b2af1c165 -->
<!-- comet-task-ref:4a51c866-31b0-4b93-a418-dd3080310c4e -->

**Step 1:** `.venv\Scripts\python.exe -m unittest discover -s tests -v` 全部通过。
**Step 2:** 手动：长曲播放观察翻页；多操作撤销/重做；演奏模式验证快捷键无效。
**Step 3:** 记录验收报告。

## Workflow follow-up

- `comet state complete-build` → `comet guard piano-roll-follow-and-undo build --apply -- .venv\Scripts\python.exe -m unittest discover -s tests -v`。
