---
change: piano-roll-tempo-control
design-doc: docs/openspec/changes/piano-roll-tempo-control/design.md
base-ref: 4f33e1c6c88a958531cec3af11cce16387fdf646
archived-with: 2026-11-11-piano-roll-tempo-control
---

<!-- comet-task-authority: docs/openspec/changes/piano-roll-tempo-control/tasks.md -->

# BPM 显示与联动 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans to implement this plan task-by-task. 任务完成状态以 tasks.md 为准；本计划只通过 `comet-task-ref` 引用任务 ID，不维护第二份勾选清单。

**Goal:** 导入曲目时显示并允许修改 BPM；改 BPM 时按「拍位不变」重算音符时间，使播放速度、量化网格、顶部标尺与背景小节线同步更新，另存 MIDI 写回当前 BPM 且音符 tick 不变。

**Architecture:** 纯函数（缩放因子、tempo 微秒、音符时间缩放）放在 `piano_roll.py` 并由 unittest 覆盖；画布新增 `rescale_times` 负责数据缩放与重排；`gui.py` 增加 BPM 数值框并固定更新顺序；`build_music.write_notes_to_midi` 增加可选 `tempo_bpm` 负责写回 tempo。

**Tech Stack:** Python 3 + PyQt5 + mido；测试使用 `unittest`。

**Spec:** `docs/openspec/changes/piano-roll-tempo-control/design.md`（行为以 `specs/piano-roll-tempo-control/spec.md` 为准）

## Global Constraints

- 产物与注释语言：简体中文（zh-CN）。
- 不新增第三方依赖；不改播放线程、音高、按键映射与音域框筛选。
- 测试命令：`.venv\Scripts\python.exe -m unittest ...`。
- BPM 范围 20.0～300.0，一位小数，步进 1；缩放因子 `factor = 旧BPM / 新BPM`。
- 连续缩放允许 `1e-6` 秒级误差。
- 工作区已有 25 个与本 change 无关的未提交改动：只 `git add` 本计划涉及的文件，绝不用 `git add -A`。
- 上一次 change 的 51 项测试必须保持通过。

## Review Focus

- BPM 相同（含浮点相等）时不得触发任何重算，避免无意义的未保存标记（Task 7）。
- 播放中修改 BPM 必须完全无副作用（Task 5、Task 7）。
- 连续改 BPM 后音符拍位可逆，不累积漂移（Task 2、Task 4）。
- 导出 MIDI 时音符 tick 与改 BPM 前一致，未处理音轨字节等价（Task 9）。
- 切换曲目时 BPM 回填不得触发上一条曲目的缩放（Task 6）。

---

### Task 1: 缩放因子与 tempo 微秒

**Files:**
- Modify: `piano_roll.py`（纯函数区）
- Test: `tests/test_tempo.py`（新建）

**Interfaces:**
- Produces: `bpm_scale_factor(old_bpm: float, new_bpm: float) -> float`、`tempo_us_from_bpm(bpm: float) -> int`

<!-- comet-task-ref:2696a302-cadb-4871-b3b8-70d50e82978f -->

**Step 1: 写失败测试**

```python
import unittest

from piano_roll import bpm_scale_factor, tempo_us_from_bpm


class BpmFactorTest(unittest.TestCase):
    def test_slow_down(self):
        self.assertEqual(bpm_scale_factor(120.0, 60.0), 2.0)

    def test_speed_up(self):
        self.assertEqual(bpm_scale_factor(60.0, 120.0), 0.5)

    def test_same_bpm_is_one(self):
        self.assertEqual(bpm_scale_factor(120.0, 120.0), 1.0)

    def test_invalid_bpm_raises(self):
        with self.assertRaises(ValueError):
            bpm_scale_factor(120.0, 0.0)
        with self.assertRaises(ValueError):
            bpm_scale_factor(-1.0, 120.0)


class TempoUsTest(unittest.TestCase):
    def test_120_bpm(self):
        self.assertEqual(tempo_us_from_bpm(120.0), 500000)

    def test_90_bpm(self):
        self.assertEqual(tempo_us_from_bpm(90.0), 666667)

    def test_invalid_bpm_raises(self):
        with self.assertRaises(ValueError):
            tempo_us_from_bpm(0.0)
```

**Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m unittest tests.test_tempo -v`
Expected: FAIL — `ImportError: cannot import name 'bpm_scale_factor'`

**Step 3: 实现**

```python
def bpm_scale_factor(old_bpm: float, new_bpm: float) -> float:
    """旧/新 BPM 的时间缩放因子；任一 BPM 非正时抛 ValueError。"""
    if old_bpm <= 0 or new_bpm <= 0:
        raise ValueError("BPM 必须大于 0")
    return float(old_bpm) / float(new_bpm)


def tempo_us_from_bpm(bpm: float) -> int:
    """BPM → MIDI tempo（微秒/拍），四舍五入到整数。"""
    if bpm <= 0:
        raise ValueError("BPM 必须大于 0")
    return int(round(60_000_000 / float(bpm)))
```

**Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m unittest tests.test_tempo -v`
Expected: PASS（7 个用例）

**Step 5: 提交**

```bash
git add piano_roll.py tests/test_tempo.py
git commit -m "feat(piano-roll): add bpm scaling and tempo helpers"
```

### Task 2: 音符时间缩放纯函数

**Files:**
- Modify: `piano_roll.py`（紧跟 `tempo_us_from_bpm`）
- Test: `tests/test_tempo.py`（追加）

**Interfaces:**
- Produces: `scaled_note_times(notes: List[Dict], factor: float) -> List[Dict]`（深拷贝，`start`/`duration` 乘 factor）

<!-- comet-task-ref:69ff741b-153d-4819-ad13-aeb75eedf877 -->

**Step 1: 追加失败测试**

```python
from piano_roll import scaled_note_times


class ScaledNoteTimesTest(unittest.TestCase):
    def test_slow_down_scales_start_and_duration(self):
        notes = [{"start": 1.0, "duration": 0.5, "pitch": 60}]
        result = scaled_note_times(notes, 2.0)
        self.assertEqual(result[0]["start"], 2.0)
        self.assertEqual(result[0]["duration"], 1.0)
        self.assertEqual(result[0]["pitch"], 60)

    def test_speed_up(self):
        notes = [{"start": 2.0, "duration": 1.0}]
        self.assertEqual(scaled_note_times(notes, 0.5)[0]["start"], 1.0)

    def test_round_trip_within_tolerance(self):
        notes = [{"start": 1.234, "duration": 0.567}]
        scaled = scaled_note_times(notes, 0.75)
        restored = scaled_note_times(scaled, 1.25)
        self.assertAlmostEqual(restored[0]["start"], 1.234, delta=1e-6)
        self.assertAlmostEqual(restored[0]["duration"], 0.567, delta=1e-6)

    def test_does_not_mutate_input(self):
        notes = [{"start": 1.0, "duration": 0.5}]
        scaled_note_times(notes, 2.0)
        self.assertEqual(notes, [{"start": 1.0, "duration": 0.5}])
```

**Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m unittest tests.test_tempo -v`
Expected: FAIL — `ImportError: cannot import name 'scaled_note_times'`

**Step 3: 实现**

```python
def scaled_note_times(notes: List[Dict], factor: float) -> List[Dict]:
    """返回音符深拷贝，start 与 duration 乘以 factor；不修改输入。"""
    result: List[Dict] = []
    for note in notes:
        cloned = dict(note)
        cloned["start"] = float(note.get("start", 0.0)) * factor
        cloned["duration"] = float(note.get("duration", 0.0)) * factor
        result.append(cloned)
    return result
```

**Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m unittest tests.test_tempo -v`
Expected: PASS（11 个用例）

**Step 5: 提交**

```bash
git add piano_roll.py tests/test_tempo.py
git commit -m "feat(piano-roll): add note time scaling helper"
```

### Task 3: 画布时间缩放 `rescale_times`

**Files:**
- Modify: `piano_roll.py`（`_PianoRollCanvas` 公开接口区、`PianoRollWidget` 透传）
- Test: `tests/test_piano_roll_ui.py`

**Interfaces:**
- Consumes: `scaled_note_times`
- Produces: `rescale_times(factor: float) -> None`（画布与 `PianoRollWidget` 同名方法）

<!-- comet-task-ref:19d6d18f-9c09-4c8e-809a-f48bcc44094c -->

**Step 1: 写失败测试**

在 `tests/test_piano_roll_ui.py` 增加：

```python
def test_rescale_times_scales_notes_and_playhead(self):
    self.widget.set_playhead_anchor(2.0)
    self.widget.rescale_times(2.0)
    starts = sorted(n["start"] for n in self.widget.get_notes())
    self.assertEqual(starts, [2.0, 6.0])
    self.assertEqual(self.widget.get_playhead_position(), 4.0)
    self.assertEqual(self.canvas._playhead_display_seconds, 4.0)

def test_rescale_times_emits_notes_changed(self):
    signals = []
    self.widget.notesChanged.connect(lambda: signals.append(1))
    self.widget.rescale_times(0.5)
    self.assertEqual(len(signals), 1)
```

**Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m unittest tests.test_piano_roll_ui -v`
Expected: FAIL — `AttributeError: 'PianoRollWidget' object has no attribute 'rescale_times'`

**Step 3: 实现**

```python
def rescale_times(self, factor: float) -> None:
    """按 factor 缩放全部音符时间与播放辅助线（BPM 变更使用）。"""
    if abs(factor - 1.0) < 1e-9:
        return
    self._notes = scaled_note_times(self._notes, factor)
    self._playhead_anchor_seconds = max(0.0, self._playhead_anchor_seconds * factor)
    self._playhead_display_seconds = max(0.0, self._playhead_display_seconds * factor)
    for note in self._notes:
        self._update_item_geometry(note)
    total = max((n["start"] + n["duration"] for n in self._notes), default=MIN_SCENE_SECONDS)
    self._ensure_scene_width(total)
    self._draw_playhead(focus=False)
    self.notesChanged.emit()
```

`PianoRollWidget` 增加同名透传。背景小节线与标尺由 GUI 随后用新 BPM 重设，不在本方法内改。

**Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m unittest tests.test_piano_roll_ui -v`
Expected: PASS（原 21 个 + 新增 2 个）

**Step 5: 提交**

```bash
git add piano_roll.py tests/test_piano_roll_ui.py
git commit -m "feat(piano-roll): rescale note times and playhead for BPM changes"
```

### Task 4: 连续缩放可逆性

**Files:**
- Test: `tests/test_piano_roll_ui.py`

**Interfaces:**
- Consumes: `rescale_times`

<!-- comet-task-ref:45bf94ad-b7cb-4be1-99fe-c50cb2a8fe2d -->

**Step 1: 写测试**

```python
def test_rescale_times_round_trip(self):
    before = sorted((n["start"], n["duration"]) for n in self.widget.get_notes())
    self.widget.rescale_times(0.75)
    self.widget.rescale_times(1.25)
    after = sorted((n["start"], n["duration"]) for n in self.widget.get_notes())
    for (s0, d0), (s1, d1) in zip(before, after):
        self.assertAlmostEqual(s0, s1, delta=1e-6)
        self.assertAlmostEqual(d0, d1, delta=1e-6)
```

**Step 2: 运行**

Run: `.venv\Scripts\python.exe -m unittest tests.test_piano_roll_ui -v`
Expected: PASS（新增 1 个）

**Step 3: 提交**

```bash
git add tests/test_piano_roll_ui.py
git commit -m "test(piano-roll): cover reversible time rescaling"
```

### Task 5: BPM 数值框与启用状态

**Files:**
- Modify: `gui.py:611-652`（工具栏）、`gui.py:983-989`（`_set_range_controls_enabled`）、`gui.py:252` 附近（`__init__` 增加 `_updating_bpm`）

**Interfaces:**
- Produces: `self.bpm_spin`、`self._updating_bpm: bool`

<!-- comet-task-ref:a9142c56-4d43-48ca-8137-8a5b2185fdee -->

**Step 1: 添加控件**

在量化下拉框之后：

```python
toolbar.addWidget(QLabel("BPM:"))
self.bpm_spin = QDoubleSpinBox()
self.bpm_spin.setRange(20.0, 300.0)
self.bpm_spin.setDecimals(1)
self.bpm_spin.setSingleStep(1.0)
self.bpm_spin.setKeyboardTracking(False)
self.bpm_spin.setEnabled(False)
self.bpm_spin.setValue(120.0)
toolbar.addWidget(self.bpm_spin)
```

导入 `QDoubleSpinBox`；`__init__` 增加 `self._updating_bpm = False`。

**Step 2: 接入启用状态**

`_set_range_controls_enabled` 增加：

```python
self.bpm_spin.setEnabled(enabled)
```

**Step 3: 验证**

Run: `.venv\Scripts\python.exe -m py_compile gui.py`
Expected: 无输出

手动：未选曲目时 BPM 框禁用；选中曲目后可编辑；播放中禁用。

**Step 4: 提交**

```bash
git add gui.py
git commit -m "feat(gui): add disabled-by-default BPM spin box"
```

### Task 6: 导入时回填 BPM

**Files:**
- Modify: `gui.py:952-963`（`_load_piano_roll`）

**Interfaces:**
- Consumes: `self.bpm_spin`、`self._updating_bpm`、`converter.get_tempo_and_time_signature`

<!-- comet-task-ref:b158f98c-f99e-4745-94ac-2ee7f3c6f1a0 -->

**Step 1: 回填**

在 `self.current_bpm = bpm` 之后：

```python
self._updating_bpm = True
self.bpm_spin.setValue(float(bpm))
self._updating_bpm = False
```

**Step 2: 验证**

Run: `.venv\Scripts\python.exe -m py_compile gui.py`
Expected: 无输出

手动：切换 120 BPM 与 140 BPM 两首曲目时数值框分别显示 120.0 / 140.0，且不触发缩放（音符位置不变、不出现「● 未保存」）。

**Step 3: 提交**

```bash
git add gui.py
git commit -m "feat(gui): fill BPM from imported track"
```

### Task 7: BPM 变更处理

**Files:**
- Modify: `gui.py`（新增 `on_bpm_changed`，连接 `bpm_spin.valueChanged`）、`gui.py:952-967`（保存 `seconds_per_beat` 所需状态）

**Interfaces:**
- Consumes: `rescale_times`、`set_measure_grid`、`set_beat_grid`、`_apply_quantize_grid`
- Produces: `on_bpm_changed(self, value: float) -> None`

<!-- comet-task-ref:fb81e917-d556-44c9-8aa2-7108b9193713 -->

**Step 1: 实现**

```python
def on_bpm_changed(self, value: float) -> None:
    if self._updating_bpm or not self.current_midi_path:
        return
    if self.is_playing:
        self._updating_bpm = True
        self.bpm_spin.setValue(self.current_bpm)
        self._updating_bpm = False
        return
    new_bpm = float(value)
    if abs(new_bpm - self.current_bpm) < 1e-9:
        return
    factor = bpm_scale_factor(self.current_bpm, new_bpm)
    self.piano_roll.rescale_times(factor)
    seconds_per_beat = 60.0 / new_bpm
    numerator = self.current_time_signature[0]
    denominator = self.current_time_signature[1]
    beat_seconds = seconds_per_beat * (4.0 / denominator)
    self.piano_roll.set_measure_grid(beat_seconds * numerator)
    self.piano_roll.set_beat_grid(beat_seconds, numerator)
    self.current_bpm = new_bpm
    self._apply_quantize_grid()
    self.on_piano_roll_notes_changed()
```

`__init__` 中连接：`self.bpm_spin.valueChanged.connect(self.on_bpm_changed)`。

**Step 2: 验证**

Run: `.venv\Scripts\python.exe -m py_compile gui.py && .venv\Scripts\python.exe -m unittest discover -s tests`
Expected: 编译无输出，测试全部通过

手动：120→60 时音符变宽、播放变慢、小节线每 4 秒；播回 120 后恢复；播放中修改被拒绝并复位显示。

**Step 3: 提交**

```bash
git add gui.py
git commit -m "feat(gui): apply BPM changes to notes, grid and quantize"
```

### Task 8: 标尺、小节线与量化一致性

**Files:** 无新增；与 Task 7 同一路径的验证

**Interfaces:**
- Consumes: Task 7 的更新顺序

<!-- comet-task-ref:161103a5-afc0-4053-934b-6a038c836017 -->
<!-- comet-task-ref:b8c61abf-783b-4f56-84ba-432045e5d7f3 -->

**Step 1: 手动验收**

- 4/4、120 BPM 曲目改为 60：小节线每 4 秒一条，标尺小节序号与小节线在同一条竖线上。
- 量化 1/4 下改 BPM 后拖动音符：吸附点落在 60/BPM 秒的整数倍。
- 缩放（Shift+滚轮）与横向滚动后重新检查上述对齐。

**Step 2: 记录**

把结果写入 `docs/superpowers/reports/` 下的验证报告（Verify 阶段复用）；不通过则回到 Task 7 修复。

**Step 3: 提交**

```bash
git add docs/superpowers/reports
git commit -m "test: record BPM grid alignment checks"
```

### Task 9: MIDI 导出写回 BPM

**Files:**
- Modify: `build_music.py:833-914`（`write_notes_to_midi`）
- Test: `tests/test_midi_tempo_export.py`（新建）

**Interfaces:**
- Consumes: `tempo_us_from_bpm`
- Produces: `write_notes_to_midi(..., tempo_bpm: Optional[float] = None)`

<!-- comet-task-ref:19590cb1-6e7b-46d6-abee-9adb87b1fda8 -->

**Step 1: 写失败测试**

用 mido 造 120 BPM、两音轨（track0 仅 tempo，track1 两个音符）的临时文件；调用 `write_notes_to_midi(src, notes, [1], out, tempo_bpm=90.0)` 后断言：

```python
mid = mido.MidiFile(out)
tempos = [msg.tempo for track in mid.tracks for msg in track if msg.type == "set_tempo"]
self.assertTrue(all(abs(t - 666667) <= 1 for t in tempos))
# 处理音轨的 note_on tick 与源文件一致
```

并断言未处理音轨（track0 除 tempo 外）事件类型与 tick 不变。

**Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m unittest tests.test_midi_tempo_export -v`
Expected: FAIL — tempo 仍为 500000（或签名不接受 `tempo_bpm`）

**Step 3: 实现**

```python
def write_notes_to_midi(..., tempo_bpm: Optional[float] = None) -> None:
    mid = mido.MidiFile(source_midi_path)
    if tempo_bpm is not None:
        tempo = tempo_us_from_bpm(tempo_bpm)
        replaced = False
        for track in mid.tracks:
            for msg in track:
                if msg.type == "set_tempo":
                    msg.tempo = tempo
                    replaced = True
        if not replaced:
            mid.tracks[0].insert(0, mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    else:
        tempo = self._scan_base_tempo(mid)
    # 后续秒→tick 换算使用 tempo
```

注意：`msg.copy(time=0)` 复制 meta 时使用已改写的 tempo；`tempo_us_from_bpm` 从 `piano_roll` 导入。

**Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m unittest tests.test_midi_tempo_export -v`
Expected: PASS

**Step 5: 提交**

```bash
git add build_music.py tests/test_midi_tempo_export.py
git commit -m "feat(midi): write current BPM when exporting notes"
```

### Task 10: 另存 MIDI 传入当前 BPM

**Files:**
- Modify: `gui.py:1057-1082`（`save_piano_roll`）

**Interfaces:**
- Consumes: `write_notes_to_midi(..., tempo_bpm=...)`

<!-- comet-task-ref:bc2fee92-a541-4a55-b53b-8264336bbd5e -->

**Step 1: 传参**

```python
converter.write_notes_to_midi(
    self.current_midi_path,
    notes,
    self.current_processed_tracks,
    output_path,
    tempo_bpm=self.current_bpm,
)
```

**Step 2: 验证**

Run: `.venv\Scripts\python.exe -m py_compile gui.py` 与 `.venv\Scripts\python.exe -m unittest tests.test_midi_tempo_export -v`
Expected: 编译无输出；导出测试通过

手动：把 120 BPM 曲目改为 90 后另存，重新导入该文件，BPM 框显示 90.0 且音符位置与编辑时一致。

**Step 3: 提交**

```bash
git add gui.py
git commit -m "feat(gui): export MIDI with current BPM"
```

### Task 11: 集成验证

**Files:** 无新增

**Interfaces:**
- Consumes: 前 10 个任务

<!-- comet-task-ref:18093b5c-1e59-4b3c-aa5b-2048d7de33f8 -->
<!-- comet-task-ref:d3bed8ba-4811-448e-88f2-ae5b2aff946b -->

**Step 1: 全量测试**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: 上一轮 51 项 + 本轮新增全部 PASS

**Step 2: 手动走查**

导入显示 BPM → 改 60 后播放变慢、音符变宽、标尺对齐 → 连续改回 120 恢复 → 播放中禁用 → 另存 MIDI 速度为当前 BPM。

**Step 3: 记录结果**

写入 `docs/superpowers/reports/2026-11-11-piano-roll-tempo-control-verification.md`（Verify 阶段复用）。

**Step 4: 提交**

```bash
git add docs/superpowers/reports
git commit -m "test: record BPM tempo acceptance results"
```

## Workflow follow-up

- 完成后运行 `comet state complete-build`，再以 `comet guard piano-roll-tempo-control build --apply -- .venv\Scripts\python.exe -m unittest discover -s tests -v` 提交检查收据，随后进入 Verify。
