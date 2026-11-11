---
change: editor-ui-and-arpeggiate
design-doc: docs/openspec/changes/editor-ui-and-arpeggiate/design.md
base-ref: 51d5b843e6d193b0df093866b02d694ea3347a2f
archived-with: 2026-11-11-editor-ui-and-arpeggiate
---

<!-- comet-task-authority: docs/openspec/changes/editor-ui-and-arpeggiate/tasks.md -->

# 工具栏体验与曲谱优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans. 任务状态以 tasks.md 为准；本计划只用 `comet-task-ref` 引用任务 ID。

**Goal:** 编辑模式禁用弹奏、播放列表逐行删除、工具栏文案/两行布局/BPM 样式/默认映射与黄框范围统一，并新增可单测的「曲谱优化」琶音功能。

**Architecture:** 新增内存版 `arpeggiate.py`（纯函数）；画布新增 `arpeggiate_selected` 并透传；GUI 重排工具栏、改用行控件显示删除按钮、在 `_sync_roll_mode` 中管理弹奏按钮。

**Tech Stack:** Python 3 + PyQt5；测试 `unittest`（offscreen Qt）。

## Global Constraints

- 不改变播放、BPM 计算、MIDI 导出与导入逻辑。
- 琶音只作用于选中音符；结束时间不变，过短钳制起点。
- 黄框默认 C2～B2，映射默认 Z/7，两者解耦。
- 既有 114 项测试通过；只 `git add` 本计划涉及文件。

## Review Focus

- 编辑/演奏/播放三种组合下弹奏按钮状态正确（播放中必须可用）。
- 逐行删除绑定的是该行曲目；取消、当前曲目、隐藏持久化都不回归。
- 琶音不修改未选中音符与输入对象；两组互不影响。
- 默认值只在加载/重置时生效，不覆盖用户手动选择。

---

### Task 1: 琶音算法

**Files:** Create `arpeggiate.py`; Test `tests/test_arpeggiate.py`

<!-- comet-task-ref:eadc5b36-ba7a-484e-92fa-53164fcd0e33 -->

**Step 1: 写失败测试**：三音和弦展开（锚点、+step、+2step，结束时间不变）；单音不变；两组独立；未选中不变；输入不被修改；过短钳制起点且时长 = 0.05。

**Step 2:** 实现 `arpeggiate_notes(notes, selected_ids, seconds_per_beat)`，窗口=步长=`seconds_per_beat/32`，组内按 pitch 升序，`start = anchor + k*step`，`end` 不变，`start = min(start, end-0.05)`。

**Step 3:** `.venv\Scripts\python.exe -m unittest tests.test_arpeggiate -v` 通过后提交 `feat(piano-roll): add arpeggiate helper`。

### Task 2: 曲谱优化入口

**Files:** Modify `piano_roll.py`、`gui.py`

<!-- comet-task-ref:827e3343-c915-4100-b031-3ccb1ef50a93 -->
<!-- comet-task-ref:caeb6de3-d649-4ea6-8ebf-7ea74d950f64 -->

**Step 1:** 画布 `arpeggiate_selected(seconds_per_beat)`：调用纯函数、替换 `_notes`、更新图元与场景、`notesChanged`；`PianoRollWidget` 透传。

**Step 2:** `_setup_piano_roll_tab` 顶部动作行加 `🪄 曲谱优化`（tooltip「对选中音符做琶音整理（1/32 拍展开）」）；点击：无选中写日志返回；否则按 `(60/current_bpm)*(4/denominator)` 调用。

**Step 3:** UI 测试：三音和弦经画布处理后起始按步长变化并发出信号。

**Step 4:** 提交 `feat(editor): add arpeggiate action`。

### Task 3: 弹奏按钮与模式

**Files:** Modify `gui.py` `_sync_roll_mode`

<!-- comet-task-ref:42758c54-40a2-4003-b6b5-b17f697bebfa -->

**Step 1:** `_sync_roll_mode` 末尾 `self.play_btn.setEnabled(play_mode or self.is_playing)`。

**Step 2:** GUI 测试：编辑模式 `play_btn.isEnabled()==False`；切换演奏模式为 True；播放中保持 True。

**Step 3:** 提交 `feat(editor): gate play button by mode`。

### Task 4: 播放列表逐行删除

**Files:** Modify `gui.py` `refresh_play_list` / `on_delete_play_item`

<!-- comet-task-ref:fb4a70cb-dee4-4f9b-bf29-9ec4ba98cf4e -->
<!-- comet-task-ref:d5db9f7f-2e68-464d-9660-966c13271a46 -->

**Step 1:** 每行 `QWidget(QLabel + 🗑)`，按钮 lambda 传入该条目；删除右侧旧按钮与启用逻辑；`on_delete_play_item(item=None)` 兼容无参取当前项。

**Step 2:** 更新既有 GUI 测试（通过按钮或直接调用逐行删除），验证删除未加载/当前、取消、刷新保持隐藏、恢复。

**Step 3:** 提交 `feat(gui): delete playlist rows inline`。

### Task 5: 文案、两行布局、BPM 样式、默认值

**Files:** Modify `gui.py`

<!-- comet-task-ref:6f18ef00-6814-4f90-9d4e-9ffb02afeacc -->
<!-- comet-task-ref:a7516f85-2992-4690-831d-1dca2f70107a -->
<!-- comet-task-ref:49702f21-e44b-4187-8ba7-141143bf7541 -->
<!-- comet-task-ref:e27f562d-415f-4a0c-b20f-0ed693d883d4 -->

**Step 1:** 文案替换四个标签。

**Step 2:** 工具栏改 `QVBoxLayout` 三行：动作行、第一行（到最高映射）、第二行（绝对键、量化、BPM）。

**Step 3:** QSS 增加 `QDoubleSpinBox` 与 `QComboBox` 相同背景/边框/文字/focus。

**Step 4:** `_populate_range_combos`/`_reset_instrument_range` 默认 Z(36)/7(83)；`set_instrument_range(36, 47)`。

**Step 5:** 手动验收后提交 `style(editor): two-row toolbar and defaults`。

### Task 6: 交互一致性

**Files:** Modify `gui.py`

<!-- comet-task-ref:36395a90-2c1f-494c-ad39-2025acbb794a -->
<!-- comet-task-ref:c34eac44-a038-47a1-9174-b80c706f7ad2 -->

**Step 1:** 统一按钮 padding、标签冒号、tooltip；检查两行不遮挡。

**Step 2:** 手动走查并提交 `style(gui): align editor controls`。

### Task 7: 集成验证

**Files:** 无新增

<!-- comet-task-ref:7c7aca3f-ffc5-433e-9d68-07318fec5e12 -->
<!-- comet-task-ref:82ead7d3-8484-41da-9ae1-f0aa552d6a06 -->

**Step 1:** 全量测试（114 + 新增）通过。

**Step 2:** 手动走查后写 `docs/superpowers/reports/2026-11-11-editor-ui-and-arpeggiate-verification.md` 并提交。

## Workflow follow-up

- `comet state complete-build` → `comet guard editor-ui-and-arpeggiate build --apply -- .venv\Scripts\python.exe -m unittest discover -s tests -v`。
