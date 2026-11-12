---
change: editor-toolbar-layout-and-arpeggiate-script
design-doc: docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/design.md
base-ref: 9a11548
archived-with: 2026-11-12-editor-toolbar-layout-and-arpeggiate-script
---

<!-- comet-task-authority: docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/tasks.md -->

# 工具栏贴左、置顶移位与曲谱优化脚本 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans. 任务状态以 tasks.md 为准；本计划只用 `comet-task-ref` 引用任务 ID。

**Goal:** 铺面编辑两行工具栏全部贴左；置顶按钮移到控制面板标题行；曲谱优化改为对选中音符执行项目内的 `arpeggiate.py`（仅修正时长为不变）。

**Architecture:** 工具栏用行尾 stretch 保持贴左；控制面板由 QGroupBox 改为 QFrame 标题行；新增 `arpeggiate_runner.py` 做临时 MIDI 往返，铺面只换算法来源。

**Spec:** `docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/design.md`

## Global Constraints

- 不改播放、play_code、播放列表、撤销与导出逻辑。
- 曲谱优化仍必须触发 `notesChanged`（进入撤销历史）。
- 脚本仅改展开时的时长语义；结构、常量、辅助函数、`main` 保留。
- 现有 157 项测试保持通过（`tests/test_arpeggiate.py` 按新语义重写）。

## Review Focus

- 窗口变宽后两行控件不漂移、不被拉伸。
- 置顶按钮真的在标题行，日志页没有重复入口。
- 临时 MIDI 往返的轨道索引映射、去重导致的音符移除、stdout 重定向、临时目录清理。
- 脚本异常时铺面完全不变。

---

### Task 1: 工具栏贴左

**Files:** `gui.py`

<!-- comet-task-ref:47f60a2a-54f0-4e45-82a9-83c3eb18ae70 -->
<!-- comet-task-ref:0e84764a-986f-4f22-a9d7-7758d559e321 -->

**Step 1:** 删除 `toolbar` 在「曲谱优化」后的 `addStretch()`，在「演奏最高键位映射」下拉框之后追加 `toolbar.addStretch()`。

**Step 2:** 确认第二行仍以末尾 `toolbar_row2.addStretch()` 收尾。

**Step 3:** 手动/offscreen 检查窗口拉宽后控件相对左边距不变。

### Task 2: 置顶按钮移位

**Files:** `gui.py`

<!-- comet-task-ref:d1c7375a-d80d-4eaf-a130-2c02ed1a08d7 -->
<!-- comet-task-ref:914d18d3-bcd2-409c-83f6-90bba6adbfbc -->

**Step 1:** `control_group` 改为 `QFrame`（objectName `controlPanel`），内部：标题行（`QLabel("🎛️ 控制面板")` objectName `panelTitle` + stretch + `topmost_btn`）、按钮行、作者信息。

**Step 2:** QSS 增加 `QFrame#controlPanel`（2px #34495E 边框、10px 圆角）与 `QLabel#panelTitle`（渐变底、白字、圆角、内边距）。

**Step 3:** 从 `_setup_log_tab` 删除置顶按钮创建与添加；`toggle_topmost` 不变。

### Task 3: 脚本移入与上报

**Files:** `arpeggiate.py`、`release/谱子/arpeggiate.py`

<!-- comet-task-ref:fb50a81d-aaa9-4438-8190-508c75db0adc -->
<!-- comet-task-ref:b82aa085-8fc9-4688-8152-46f52e130cd4 -->

**Step 1:** 用 `release/谱子/arpeggiate.py` 的内容覆盖项目根 `arpeggiate.py`，删除原件。

**Step 2:** `arpeggiate()` 内改为：

```python
delta = anchor + k * step - n['on']
n['on'] += delta
n['off'] += delta
if n['off'] - n['on'] < MIN_DUR_TICKS:
    n['off'] = n['on'] + MIN_DUR_TICKS
```

其余保持原样。

### Task 4: 执行器与接线

**Files:** `arpeggiate_runner.py`、`piano_roll.py`、`gui.py`

<!-- comet-task-ref:d71c4007-074f-4982-bc5b-56ba3e4e1ef3 -->
<!-- comet-task-ref:3c3815cf-c8a0-4b9d-a523-5440cace36a8 -->
<!-- comet-task-ref:a532832f-753b-4724-b858-92c56e5b3654 -->

**Step 1:** 新增 `arpeggiate_runner.arpeggiate_notes(notes, selected_ids, seconds_per_beat)`：
- `TICKS_PER_BEAT = 384`；每个选中音符一条音轨；`redirect_stdout/redirect_stderr`；调用 `arpeggiate.main(src, dst)`；用 `arpeggiate.extract_notes` 回读；空轨删音符；`TemporaryDirectory` 自动清理。

**Step 2:** `piano_roll.py` 的 `arpeggiate_selected` 改调 runner。

**Step 3:** `gui.on_arpeggiate_clicked` 用 `60.0 / current_bpm`，`try/except` 记日志且不改铺面。

### Task 5: 测试

**Files:** `tests/test_arpeggiate.py`、`tests/test_playlist_gui.py`、`tests/test_piano_roll_ui.py`

<!-- comet-task-ref:d75bce6b-12f2-478c-bfca-c9502b7bd7f4 -->
<!-- comet-task-ref:4e0a0d7b-4157-4719-be39-1ed715f50b1b -->
<!-- comet-task-ref:370c67e2-27db-4a12-958f-0c6aa9770fc5 -->

**Step 1:** 重写 `test_arpeggiate.py`：和弦展开、时长不变、未选中不变、去重、无效拍长、脚本结构断言。

**Step 2:** GUI 测试：置顶按钮父级为控制面板标题行、日志页无置顶按钮；曲谱优化进入撤销历史。

**Step 3:** 布局测试：两行首个控件 x() 贴左、行尾存在弹性空白。

### Task 6: 集成验证

<!-- comet-task-ref:fec3a52f-1e16-4409-b459-71c98af298fc -->
<!-- comet-task-ref:8500d5bd-e3a6-4378-9a2d-9eba86390c9b -->

**Step 1:** `.venv\Scripts\python.exe -m unittest discover -s tests -v` 全部通过。
**Step 2:** 记录验收报告。

## Workflow follow-up

- `comet state complete-build` → `comet guard editor-toolbar-layout-and-arpeggiate-script build --apply -- .venv\Scripts\python.exe -m unittest discover -s tests -v`。
