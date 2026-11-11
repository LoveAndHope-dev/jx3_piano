---
change: piano-roll-modes-and-daw-editing
design-doc: docs/openspec/changes/piano-roll-modes-and-daw-editing/design.md
base-ref: 515d96fd84cefe863c0e35848ae18a0e21e51015
archived-with: 2026-11-11-piano-roll-modes-and-daw-editing
---

<!-- comet-task-authority: docs/openspec/changes/piano-roll-modes-and-daw-editing/tasks.md -->

# 演奏/编辑模式与 DAW 编辑 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans. 任务状态以 tasks.md 为准；本计划只用 `comet-task-ref` 引用任务 ID。

**Goal:** 把「显示/隐藏映射」升级为演奏/编辑模式，并把钢琴窗基础编辑对齐主流 DAW（空白手势、左边缘、方向键、Ctrl+滚轮），同时统一按钮高度与页脚文案。

**Architecture:** 模式复用 `_read_only`；标尺定位新增 `_playhead_locked` 与播放解耦；`_PianoRollCanvas` 增加双击、左边缘 `resize-start`、方向键处理；`wheelEvent` 改用 Ctrl；`gui.py` 改按钮文案、模式切换与页脚/QSS。

**Tech Stack:** Python 3 + PyQt5；测试 `unittest`（offscreen Qt）。

**Spec:** `docs/openspec/changes/piano-roll-modes-and-daw-editing/design.md`

## Global Constraints

- 不改变播放、BPM、播放列表、音域框筛选与 MIDI 导出。
- 演奏模式禁止一切音符编辑；播放中任何模式都保持只读。
- 既有 99 项测试需通过；缩放测试改为 Ctrl。
- 只 `git add` 本计划涉及文件。

## Review Focus

- 演奏模式下键盘/鼠标任何入口都不能改数据，但标尺仍能定位。
- 播放中切模式不得解锁只读。
- 单击/双击/拖动三种空白手势互不干扰，且不产生多余音符。
- 左边缘拖动不能把音符拖成负时长或删除。
- Ctrl 缩放锚点不漂移；Shift 不再缩放。

---

### Task 1: 模式切换

**Files:** Modify `gui.py`（`on_range_toggle_clicked`）、`piano_roll.py`（`set_playhead_locked`）

<!-- comet-task-ref:b36f2527-04b8-4abd-95d6-18d32373370f -->
<!-- comet-task-ref:8f30ba86-b6fb-4f61-b01b-88d25f1d652c -->
<!-- comet-task-ref:0de529dd-54de-4bdf-b209-f45308dd571b -->

**Step 1:** `on_range_toggle_clicked` 改为：

```python
playing_mode = self.range_toggle_btn.isChecked()
self.range_toggle_btn.setText("✏️ 编辑模式" if playing_mode else "🎹 演奏模式")
self.piano_roll.set_instrument_range_visible(playing_mode)
self.piano_roll.set_read_only(playing_mode or self.is_playing)
```

初始文案设为「🎹 演奏模式」。

**Step 2:** 画布新增 `self._playhead_locked = False` 与 `set_playhead_locked(locked)`；标尺 `_should_ignore_mouse` 改用 `canvas.is_playhead_locked()`；`PianoRollWidget` 透传；`gui.start_playing` 置 True、`stop_playing`/`on_play_finished` 置 False。

**Step 3:** 手动验证：演奏模式不可编辑、标尺可定位；编辑模式恢复；播放中切模式仍只读。

**Step 4:** 提交 `feat(editor): add play/edit modes with playhead lock`

### Task 2: 空白区域手势

**Files:** Modify `piano_roll.py`（`mousePressEvent`、`mouseReleaseEvent`、新增 `mouseDoubleClickEvent`）；Test `tests/test_piano_roll_ui.py`

<!-- comet-task-ref:b30b7093-398c-4fc7-96cb-ded536578053 -->
<!-- comet-task-ref:7b45562d-5a98-43f3-9b42-b5e3bef4eeb1 -->

**Step 1: 写失败测试**

- 单击空白：音符数不变、选中集合为空。
- `QTest.mouseDClick` 空白：音符数 +1、新音符被选中。
- 拖动空白 → 框选：音符数不变、选中矩形内音符。

**Step 2: 实现**

- 按下空白：只记录 `_drag_start_scene`、`_drag_mode = "select-rect-or-create"`、`_select_rect_item = None`，不再设置 `_pending_create_note`。
- 松开且未拖动：`_set_selection(set())`。
- `mouseDoubleClickEvent`：`read_only` 直接返回；否则在位置新建音符（时长为 `_quantize_seconds or DEFAULT_NOTE_DURATION`），选中并 `notesChanged`。

**Step 3:** 通过后提交 `feat(piano-roll): DAW-style empty area gestures`

### Task 3: 左边缘调整起始时间

**Files:** Modify `piano_roll.py`（命中判定、`mouseMoveEvent`）；Test `tests/test_piano_roll_ui.py`

<!-- comet-task-ref:5896f990-0f22-448c-96ea-fd304b4f2de9 -->
<!-- comet-task-ref:9ea42864-bdb8-4402-ac73-a718b83ce065 -->

**Step 1: 写失败测试**

- 拖左边缘向右：start 增加、end 不变、duration 减少。
- 拖过结尾：start == end − MIN_NOTE_DURATION，音符仍存在。

**Step 2: 实现**

- 命中：`near_right_edge` 优先；否则 `near_left_edge`（`scene_pos.x() - rect.left() <= RESIZE_MARGIN`）。
- `_drag_mode = "resize-start"`；拖动时 `raw_start = start + dx/pps`，`snapped = _snap_time(raw_start)`，`max_start = end - MIN_NOTE_DURATION`，`new_start = min(max(0, snapped), max_start)`，`duration = end - new_start`。

**Step 3:** 提交 `feat(piano-roll): drag left edge to trim note start`

### Task 4: 方向键微调

**Files:** Modify `piano_roll.py`（`keyPressEvent`、新增 `_nudge_selected(delta_seconds)` / `_transpose_selected(semitones)`）；Test `tests/test_piano_roll_ui.py`

<!-- comet-task-ref:fe8ee5e7-1230-4113-8dd3-1e8416af0c9d -->
<!-- comet-task-ref:730e6150-fbd6-4f72-af86-e8896206bb7e -->

**Step 1: 写失败测试**

- 量化 1/8（0.25s）按 →：start +0.25s。
- 按 ↑：音高 +1；Shift+↑：+12。
- 无选中：无变化、无信号。

**Step 2: 实现**

- `DEFAULT_NUDGE_SECONDS = 0.1`；步长 `self._quantize_seconds or DEFAULT_NUDGE_SECONDS`。
- ←/→：组内所有音符 `start = max(0, start ± step)`（保持相对时距：先算 min_start，若为 0 则不动）。
- ↑/↓：新增 `semitones` 版移调函数（复用 `octave_shift_pitches` 逻辑改为 delta 参数），越界跳过。

**Step 3:** 提交 `feat(piano-roll): nudge and transpose with arrow keys`

### Task 5: Ctrl+滚轮

**Files:** Modify `piano_roll.py`（`wheelEvent`）；Test `tests/test_piano_roll_ui.py`（更新既有缩放测试）

<!-- comet-task-ref:84210419-5582-4e9f-9ee6-98880309274b -->
<!-- comet-task-ref:5bba82b8-7882-4a16-92ef-44b7b07342b4 -->

**Step 1:** 把 `wheelEvent` 的修饰键判断改为 `ControlModifier`。

**Step 2:** 既有测试 `_wheel(..., shift=True)` 改为 `ctrl=True`；新增「Shift+滚轮不缩放」。

**Step 3:** 提交 `feat(piano-roll): zoom with ctrl+wheel`

### Task 6: 按钮高度与页脚

**Files:** Modify `gui.py`（全局 QSS、`credit_label`）

<!-- comet-task-ref:6634e911-8a74-4a7e-80b1-b7b7d21c3afc -->
<!-- comet-task-ref:0fa73f88-5cf8-438f-9d79-5b772d45a01c -->

**Step 1:** 全局样式表追加 `QPushButton { min-height: 26px; max-height: 26px; }`（若已有 QSS 则追加规则）。

**Step 2:** 页脚文案改为 `created by 66maer updated by Loveanope_Dev`。

**Step 3:** 提交 `style(gui): align button heights and update credit`

### Task 7: 集成验证

**Files:** 无新增

<!-- comet-task-ref:4691400d-86f8-49c6-afd4-4deb02ebf5ba -->
<!-- comet-task-ref:ffe4dbd3-9d09-4407-b1c1-2a7ab7e75bed -->

**Step 1:** `.venv\Scripts\python.exe -m unittest discover -s tests -v` → 99 项 + 新增全部 PASS。

**Step 2:** 手动走查模式切换、空白手势、左右边缘、方向键、Ctrl/Shift+滚轮、按钮高度与页脚。

**Step 3:** 记录到 `docs/superpowers/reports/2026-11-11-piano-roll-modes-and-daw-editing-verification.md`。

**Step 4:** 提交 `test: record editor modes and daw editing acceptance`

## Workflow follow-up

- 完成后 `comet state complete-build`，再 `comet guard piano-roll-modes-and-daw-editing build --apply -- .venv\Scripts\python.exe -m unittest discover -s tests -v`。
