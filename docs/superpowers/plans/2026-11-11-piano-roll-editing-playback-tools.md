---
change: piano-roll-editing-playback-tools
design-doc: docs/openspec/changes/piano-roll-editing-playback-tools/design.md
base-ref: 5c2774d2a0cd80c5dc9a34b5ff65eea5f19a6de8
archived-with: 2026-11-11-piano-roll-editing-playback-tools
---

<!-- comet-task-authority: docs/openspec/changes/piano-roll-editing-playback-tools/tasks.md -->

# 铺面编辑与播放控制 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. 任务完成状态以 tasks.md 为准；本计划只通过 `comet-task-ref` 引用任务 ID，不维护第二份勾选清单。

**Goal:** 为铺面编辑器补齐复制/剪切/粘贴、Shift+↑/↓ 八度移动、顶部拍数标尺与常驻播放辅助线、Shift+滚轮横向缩放，并把「播放」按钮改名为「弹奏」，播放从播放辅助线位置开始。

**Architecture:** 可测试的纯逻辑（粘贴时间、八度越界、播放起点过滤、缩放锚点）放在 `piano_roll.py` 模块级函数中并由 unittest 覆盖；UI 行为落在 `_PianoRollCanvas`（实例级缩放、剪贴板、键盘、滚轮、播放辅助线）与新增的 `_TimeRulerWidget`（顶部标尺）；`gui.py` 负责传拍长、播放起点过滤与按钮文案。

**Tech Stack:** Python 3 + PyQt5，测试使用标准库 `unittest`，无第三方测试依赖。

**Spec:** `docs/openspec/changes/piano-roll-editing-playback-tools/design.md`（行为以 `specs/` 下三份 delta spec 为准）

## Global Constraints

- 产物与注释语言：简体中文（zh-CN）。
- 不新增第三方依赖；不修改 `player.py`、`build_music.py` 的播放数据格式与按键执行逻辑。
- 测试命令统一用 `.venv\Scripts\python.exe -m unittest ...`（项目没有 pytest）。
- 缩放比例夹紧到 `10.0`～`600.0` px/s，默认 `70.0`；每格滚轮缩放因子 `1.25`。
- 播放起点过滤容差 `1e-6`；音高范围 `MIN_PITCH=21`（A0）～`MAX_PITCH=108`（C8）。
- `ROW_HEIGHT`、纵向滚动、音域框筛选、按键映射、MIDI 另存为语义保持不变。
- 按钮 `objectName` 保持 `playBtn` / `stopBtn`，样式不失效。
- 工作区已有与本 change 无关的删除（`docs/comet/**`、`docs/openspec/changes/piano-roll-toolbar-range-readout/**`）与 `.comet/config.yaml` 改动：提交时只 `git add` 本计划涉及的文件，绝不用 `git add -A`。

## Review Focus

- 播放辅助线恰好落在某个音符的 `start` 上时，该音符必须参与播放（Task 3 的边界测试）。
- 剪贴板为空时 Ctrl+V 必须完全无副作用；粘贴到 0s 时必须从 0 开始而不是被负偏移（Task 1、Task 5）。
- 越界八度移动（如 pitch 100 升八度到 112）必须保持原音高，其余音符照常（Task 2）。
- 缩放到上限 600 后继续放大、缩到下限 10 后继续缩小，锚点时间仍不能漂移（Task 4）。
- 播放进行中点击顶部标尺不得改变播放位置或中断播放（Task 8、Task 11 的手动验收）。

---

### Task 1: 粘贴时间纯函数

**Files:**
- Modify: `piano_roll.py`（常量区之后、`_is_black_key` 之前）
- Test: `tests/test_note_clipboard.py`（新建）

**Interfaces:**
- Consumes: 无
- Produces: `pasted_starts(clipboard: List[Dict], anchor: float) -> List[float]`

<!-- comet-task-ref:5795b48f-f846-4064-b3ab-249ec7003b8e -->

**Step 1: 写失败测试**

```python
import unittest

from piano_roll import pasted_starts


class PastedStartsTest(unittest.TestCase):
    def test_preserves_relative_spacing(self):
        clipboard = [{"start": 1.0}, {"start": 3.0}]
        self.assertEqual(pasted_starts(clipboard, 10.0), [10.0, 12.0])

    def test_single_note_lands_on_anchor(self):
        self.assertEqual(pasted_starts([{"start": 4.5}], 2.0), [2.0])

    def test_zero_based_clipboard(self):
        self.assertEqual(pasted_starts([{"start": 0.0}, {"start": 0.5}], 5.0), [5.0, 5.5])

    def test_does_not_mutate_input(self):
        clipboard = [{"start": 1.0, "pitch": 60}, {"start": 3.0, "pitch": 64}]
        pasted_starts(clipboard, 10.0)
        self.assertEqual(clipboard, [{"start": 1.0, "pitch": 60}, {"start": 3.0, "pitch": 64}])

    def test_empty_clipboard(self):
        self.assertEqual(pasted_starts([], 10.0), [])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m unittest tests.test_note_clipboard -v`
Expected: FAIL — `ImportError: cannot import name 'pasted_starts'`

**Step 3: 实现 `pasted_starts`**

```python
def pasted_starts(clipboard: List[Dict], anchor: float) -> List[float]:
    """剪贴板音符按最早 start 对齐 anchor（秒）后的起始时间列表；不修改输入。"""
    if not clipboard:
        return []
    base = min(float(n.get("start", 0.0)) for n in clipboard)
    return [max(0.0, float(anchor) + float(n.get("start", 0.0)) - base) for n in clipboard]
```

**Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m unittest tests.test_note_clipboard -v`
Expected: PASS（5 个用例）

**Step 5: 提交**

```bash
git add piano_roll.py tests/test_note_clipboard.py
git commit -m "feat(piano-roll): add clipboard paste offset helper"
```

### Task 2: 八度移动纯函数

**Files:**
- Modify: `piano_roll.py`（紧接 `pasted_starts` 之后）
- Test: `tests/test_note_clipboard.py`（追加）

**Interfaces:**
- Consumes: `MIN_PITCH`、`MAX_PITCH`（模块常量 21/108）
- Produces: `octave_shift_pitches(notes: List[Dict], selected_ids: Set[int], delta: int) -> Dict[int, int]`，返回 `{note_id: 目标音高}`；越界音符映射为原音高

<!-- comet-task-ref:7e371289-6682-4fa4-92bc-8a4b423a1b75 -->

**Step 1: 追加失败测试**

```python
from piano_roll import octave_shift_pitches


class OctaveShiftTest(unittest.TestCase):
    def test_shift_up_all_notes(self):
        notes = [{"id": 1, "pitch": 60}, {"id": 2, "pitch": 64}]
        self.assertEqual(octave_shift_pitches(notes, {1, 2}, 12), {1: 72, 2: 76})

    def test_shift_down_all_notes(self):
        notes = [{"id": 1, "pitch": 60}]
        self.assertEqual(octave_shift_pitches(notes, {1}, -12), {1: 48})

    def test_out_of_range_note_keeps_pitch(self):
        notes = [{"id": 1, "pitch": 100}, {"id": 2, "pitch": 60}]
        self.assertEqual(octave_shift_pitches(notes, {1, 2}, 12), {1: 100, 2: 72})

    def test_all_out_of_range_returns_original_pitches(self):
        notes = [{"id": 1, "pitch": 21}]
        self.assertEqual(octave_shift_pitches(notes, {1}, -12), {1: 21})

    def test_unselected_notes_are_ignored(self):
        notes = [{"id": 1, "pitch": 60}, {"id": 2, "pitch": 64}]
        self.assertEqual(octave_shift_pitches(notes, {2}, 12), {2: 76})
```

**Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m unittest tests.test_note_clipboard -v`
Expected: FAIL — `ImportError: cannot import name 'octave_shift_pitches'`

**Step 3: 实现**

```python
def octave_shift_pitches(
    notes: List[Dict], selected_ids: Set[int], delta: int
) -> Dict[int, int]:
    """按 delta 半音整体移动选中音符；新音高超出 A0～C8 的音符保持原音高。"""
    targets: Dict[int, int] = {}
    for note in notes:
        note_id = note.get("id")
        if note_id not in selected_ids:
            continue
        pitch = int(note["pitch"])
        target = pitch + delta
        targets[note_id] = target if MIN_PITCH <= target <= MAX_PITCH else pitch
    return targets
```

**Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m unittest tests.test_note_clipboard -v`
Expected: PASS（10 个用例）

**Step 5: 提交**

```bash
git add piano_roll.py tests/test_note_clipboard.py
git commit -m "feat(piano-roll): add octave shift helper with range guard"
```

### Task 3: 播放起点过滤纯函数

**Files:**
- Modify: `piano_roll.py`（紧接 `octave_shift_pitches` 之后）
- Test: `tests/test_playback_start.py`（新建）

**Interfaces:**
- Consumes: `PLAYHEAD_EPSILON = 1e-6`（新增模块常量）
- Produces: `playback_notes_from_position(notes: List[Dict], playhead: float) -> List[Dict]`，返回深拷贝且 `start` 已平移为相对时间

<!-- comet-task-ref:a4f189ce-7475-491a-aed6-89793b964b69 -->

**Step 1: 写失败测试**

```python
import unittest

from piano_roll import playback_notes_from_position


class PlaybackNotesFromPositionTest(unittest.TestCase):
    def test_excludes_notes_starting_before_playhead(self):
        notes = [{"start": 1.0, "pitch": 60}, {"start": 10.0, "pitch": 62}]
        result = playback_notes_from_position(notes, 5.0)
        self.assertEqual([n["pitch"] for n in result], [62])

    def test_note_exactly_on_playhead_is_kept(self):
        notes = [{"start": 5.0, "pitch": 60}]
        result = playback_notes_from_position(notes, 5.0)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]["start"], 0.0)

    def test_note_ending_after_playhead_is_not_retriggered(self):
        notes = [{"start": 8.0, "duration": 4.0, "pitch": 60}, {"start": 11.0, "pitch": 62}]
        result = playback_notes_from_position(notes, 10.0)
        self.assertEqual([n["pitch"] for n in result], [62])

    def test_starts_are_shifted_to_relative_time(self):
        notes = [{"start": 10.0, "pitch": 60}, {"start": 12.5, "pitch": 62}]
        starts = [n["start"] for n in playback_notes_from_position(notes, 10.0)]
        self.assertEqual(starts, [0.0, 2.5])

    def test_empty_when_no_note_after_playhead(self):
        self.assertEqual(playback_notes_from_position([{"start": 1.0}], 5.0), [])

    def test_does_not_mutate_input(self):
        notes = [{"start": 10.0, "pitch": 60}]
        playback_notes_from_position(notes, 4.0)
        self.assertEqual(notes, [{"start": 10.0, "pitch": 60}])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m unittest tests.test_playback_start -v`
Expected: FAIL — `ImportError: cannot import name 'playback_notes_from_position'`

**Step 3: 实现**

```python
def playback_notes_from_position(notes: List[Dict], playhead: float) -> List[Dict]:
    """只保留起始时间不早于 playhead 的音符，并把 start 平移到相对时间。"""
    result: List[Dict] = []
    for note in notes:
        start = float(note.get("start", 0.0))
        if start >= playhead - PLAYHEAD_EPSILON:
            cloned = dict(note)
            cloned["start"] = max(0.0, start - playhead)
            result.append(cloned)
    return result
```

**Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m unittest tests.test_playback_start -v`
Expected: PASS（6 个用例）

**Step 5: 提交**

```bash
git add piano_roll.py tests/test_playback_start.py
git commit -m "feat(piano-roll): filter playback notes from playhead position"
```

### Task 4: 缩放纯函数

**Files:**
- Modify: `piano_roll.py`（常量区新增缩放常量，函数紧跟 `playback_notes_from_position`）
- Test: `tests/test_zoom_math.py`（新建）

**Interfaces:**
- Produces: `clamp_pixels_per_second(value: float) -> float`、`anchored_scroll_value(anchor_time: float, screen_x: float, pixels_per_second: float) -> float`
- 常量：`MIN_PIXELS_PER_SECOND = 10.0`、`MAX_PIXELS_PER_SECOND = 600.0`、`ZOOM_STEP_FACTOR = 1.25`

<!-- comet-task-ref:81b1efb9-0e8a-437a-86e3-9d2a2d185881 -->

**Step 1: 写失败测试**

```python
import unittest

from piano_roll import (
    MAX_PIXELS_PER_SECOND,
    MIN_PIXELS_PER_SECOND,
    anchored_scroll_value,
    clamp_pixels_per_second,
)


class ZoomMathTest(unittest.TestCase):
    def test_clamps_low_and_high(self):
        self.assertEqual(clamp_pixels_per_second(1.0), MIN_PIXELS_PER_SECOND)
        self.assertEqual(clamp_pixels_per_second(9999.0), MAX_PIXELS_PER_SECOND)

    def test_keeps_value_inside_range(self):
        self.assertEqual(clamp_pixels_per_second(70.0), 70.0)

    def test_anchor_time_survives_zoom_in(self):
        anchor_time, screen_x, pps = 5.0, 120.0, 87.5
        value = anchored_scroll_value(anchor_time, screen_x, pps)
        self.assertAlmostEqual((value + screen_x) / pps, anchor_time)

    def test_anchor_time_survives_zoom_out(self):
        anchor_time, screen_x, pps = 12.0, 40.0, 56.0
        value = anchored_scroll_value(anchor_time, screen_x, pps)
        self.assertAlmostEqual((value + screen_x) / pps, anchor_time)

    def test_never_returns_negative_scroll(self):
        self.assertEqual(anchored_scroll_value(0.5, 300.0, 70.0), 0.0)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m unittest tests.test_zoom_math -v`
Expected: FAIL — `ImportError: cannot import name 'clamp_pixels_per_second'`

**Step 3: 实现**

```python
def clamp_pixels_per_second(value: float) -> float:
    return max(MIN_PIXELS_PER_SECOND, min(MAX_PIXELS_PER_SECOND, float(value)))


def anchored_scroll_value(anchor_time: float, screen_x: float, pixels_per_second: float) -> float:
    """缩放后应设置的横向滚动值（像素），使 anchor_time 仍落在屏幕 screen_x 处。"""
    return max(0.0, float(anchor_time) * float(pixels_per_second) - float(screen_x))
```

**Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m unittest tests.test_zoom_math -v`
Expected: PASS（5 个用例）

**Step 5: 提交**

```bash
git add piano_roll.py tests/test_zoom_math.py
git commit -m "feat(piano-roll): add zoom clamping and anchor scroll helpers"
```

### Task 5: 画布剪贴板（复制 / 剪切 / 粘贴）

**Files:**
- Modify: `piano_roll.py:121-165`（`_PianoRollCanvas.__init__` 增加 `self._clipboard: List[Dict] = []` 与 `self._playhead_anchor_seconds = 0.0`）
- Modify: `piano_roll.py:746-761`（`keyPressEvent` 分支）
- 新增方法：`_copy_selected`、`_paste_clipboard`

**Interfaces:**
- Consumes: `pasted_starts`、`_selected_ids`、`_delete_selected`、`_playhead_anchor_seconds`（Task 10 提供；在此之前用 `self._playhead_anchor_seconds` 初始化为 `0.0`）、`_add_note_item`、`_set_selection`、`_ensure_scene_width`
- Produces: `_clipboard` 与 Ctrl+C / Ctrl+X / Ctrl+V 行为

<!-- comet-task-ref:6e3710d1-7234-425b-9e2a-a05c0892e75c -->
<!-- comet-task-ref:48602a6e-f25e-4c5e-92f1-5daa8336255f -->

**Step 1: 实现复制**

在 `_delete_selected` 之后新增：

```python
def _copy_selected(self) -> None:
    """把当前选中音符深拷贝进内部剪贴板；无选中时保持原剪贴板。"""
    self._clipboard = [dict(n) for n in self._notes if n["id"] in self._selected_ids]
```

**Step 2: 实现粘贴**

```python
def _paste_clipboard(self) -> None:
    if not self._clipboard:
        return
    anchor = float(self._playhead_anchor_seconds)
    starts = pasted_starts(self._clipboard, anchor)
    pasted: List[Dict] = []
    for source, start in zip(self._clipboard, starts):
        note = dict(source)
        note["id"] = self._next_id
        self._next_id += 1
        note["start"] = start
        note["mapped"] = int(note["pitch"]) in self._mapped_pitches
        self._notes.append(note)
        self._add_note_item(note)
        pasted.append(note)
    self._set_selection({n["id"] for n in pasted})
    max_end = max(n["start"] + n["duration"] for n in pasted)
    self._ensure_scene_width(max_end)
    self.notesChanged.emit()
```

**Step 3: 接入键盘**

在 `keyPressEvent` 的 Ctrl+A 分支之后、Delete 分支之前插入：

```python
if event.key() == Qt.Key_C and bool(event.modifiers() & Qt.ControlModifier):
    self._copy_selected()
    event.accept()
    return

if event.key() == Qt.Key_X and bool(event.modifiers() & Qt.ControlModifier):
    self._copy_selected()
    self._delete_selected()
    event.accept()
    return

if event.key() == Qt.Key_V and bool(event.modifiers() & Qt.ControlModifier):
    self._paste_clipboard()
    event.accept()
    return
```

**Step 4: 静态检查 + 手动验收**

Run: `.venv\Scripts\python.exe -c "import piano_roll"`
Expected: 无输出（导入成功）

手动验收（`python gui.py`，选中曲目后）：
1. 框选 2 个音符 → Ctrl+C → 用鼠标拖走其中一个原音符 → 在标尺点击到 5s → Ctrl+V：5s 处出现 2 个音符、相对时距保持、新音符为选中色。
2. 再次 Ctrl+V 到 15s：产生第二组独立音符，原组不变。
3. Ctrl+X：原音符消失并显示「● 未保存」，Ctrl+V 可粘贴回来。
4. 剪贴板为空时（重开程序）Ctrl+V：铺面无变化。

**Step 5: 提交**

```bash
git add piano_roll.py
git commit -m "feat(piano-roll): add copy/cut/paste on playhead anchor"
```

### Task 6: Shift+↑/↓ 八度移动与模块说明

**Files:**
- Modify: `piano_roll.py:746-761`（`keyPressEvent`）
- Modify: `piano_roll.py:1-11`（模块 docstring）
- 新增方法：`_shift_selected_octave`

**Interfaces:**
- Consumes: `octave_shift_pitches`、`_update_item_geometry`、`_ensure_scene_width`
- Produces: `_shift_selected_octave(delta: int) -> None`；Shift+↑ 传 `12`，Shift+↓ 传 `-12`

<!-- comet-task-ref:6b51f8a7-8093-46f9-be5b-2b7df08e7385 -->
<!-- comet-task-ref:e5a372a1-c0d1-43d8-85a3-2f75efa67f1e -->

**Step 1: 实现八度移动**

在 `_paste_clipboard` 之后新增：

```python
def _shift_selected_octave(self, delta: int) -> None:
    if not self._selected_ids:
        return
    targets = octave_shift_pitches(self._notes, self._selected_ids, delta)
    changed = False
    for note in self._notes:
        target = targets.get(note["id"])
        if target is None or target == note["pitch"]:
            continue
        note["pitch"] = target
        note["mapped"] = target in self._mapped_pitches
        self._update_item_geometry(note)
        changed = True
    if changed:
        self.notesChanged.emit()
```

**Step 2: 接入 Shift 方向键**

在 `keyPressEvent` 的 Ctrl+V 分支之后插入：

```python
if event.modifiers() & Qt.ShiftModifier and event.key() in (Qt.Key_Up, Qt.Key_Down):
    self._shift_selected_octave(12 if event.key() == Qt.Key_Up else -12)
    event.accept()
    return
```

**Step 3: 更新模块说明**

在文件头 docstring 的能力列表中补两行：

```
- 支持 Ctrl+C / Ctrl+X / Ctrl+V 在播放辅助线处复制、剪切与粘贴选中音符
- 支持 Shift+↑ / Shift+↓ 把选中音符整体上移 / 下移一个八度（越界音符保持原音高）
```

**Step 4: 验证**

Run: `.venv\Scripts\python.exe -m unittest tests.test_note_clipboard -v`
Expected: PASS（10 个用例）

手动验收：选中 3 个音符按 Shift+↑ → 音高各 +12、起止时间不变、显示「● 未保存」；选中接近 C8 的音符（如 pitch 100）按 Shift+↑ → 该音符不动、其余音符仍移动；Shift+↓ 对称；无选中时不报错且无变化。

**Step 5: 提交**

```bash
git add piano_roll.py
git commit -m "feat(piano-roll): shift selected notes by octave with range guard"
```

### Task 7: 实例级缩放与 Shift+滚轮

**Files:**
- Modify: `piano_roll.py:38`（保留 `PIXELS_PER_SECOND = 70` 作为默认值）
- Modify: `piano_roll.py:169-181`（坐标换算）
- Modify: `piano_roll.py:451-461`（`_update_item_geometry` 宽度）
- 新增：`wheelEvent`、`pixels_per_second()`、`set_pixels_per_second()`
- 新增信号：`zoomChanged = pyqtSignal()`（类属性）

**Interfaces:**
- Produces: `self._pixels_per_second: float`（默认 70）、`self.zoomChanged` 信号、`pixels_per_second() -> float`
- 其他所有 `PIXELS_PER_SECOND` 的像素换算（拖动、调整时长、背景、音域框）一律改用 `self._pixels_per_second`

<!-- comet-task-ref:25419ee0-14a1-48cf-994d-1b83f8808001 -->
<!-- comet-task-ref:6438bc9c-6776-467e-af59-d4d31929a544 -->

**Step 1: 用 grep 找出全部使用点**

Run: `rg -n "PIXELS_PER_SECOND" piano_roll.py`
Expected: 至少命中 `_time_to_x`、`_x_to_time`、`_update_item_geometry`、`mouseMoveEvent`（拖动/调整时长）；逐个改为 `self._pixels_per_second`，只保留常量定义本身与 `__init__` 默认值。

**Step 2: 初始化实例缩放与信号**

在 `_PianoRollCanvas.__init__` 的量化/小节网格之前加：

```python
self._pixels_per_second = float(PIXELS_PER_SECOND)
```

在类属性区加：

```python
zoomChanged = pyqtSignal()
```

**Step 3: 实现缩放与访问器**

```python
def pixels_per_second(self) -> float:
    return self._pixels_per_second

def set_pixels_per_second(self, value: float) -> None:
    """设置横向像素/秒比例（自动夹紧），并重绘全部依赖该比例的内容。"""
    new_value = clamp_pixels_per_second(value)
    if abs(new_value - self._pixels_per_second) < 1e-9:
        return
    self._pixels_per_second = new_value
    self._rebuild_after_zoom()

def wheelEvent(self, event):
    if not (event.modifiers() & Qt.ShiftModifier):
        super().wheelEvent(event)
        return
    viewport_x = float(event.pos().x())
    anchor_time = self.time_at_viewport_x(viewport_x)
    factor = ZOOM_STEP_FACTOR if event.angleDelta().y() > 0 else 1.0 / ZOOM_STEP_FACTOR
    new_pps = clamp_pixels_per_second(self._pixels_per_second * factor)
    if abs(new_pps - self._pixels_per_second) > 1e-9:
        self._pixels_per_second = new_pps
        self.horizontalScrollBar().setValue(
            int(round(anchored_scroll_value(anchor_time, viewport_x, new_pps)))
        )
        self._rebuild_after_zoom()
    event.accept()
```

**Step 4: 实现视口↔时间换算与重排**

```python
def viewport_x_for_time(self, seconds: float) -> float:
    return self._time_to_x(seconds) - self.horizontalScrollBar().value()

def time_at_viewport_x(self, x: float) -> float:
    return max(0.0, (float(x) + self.horizontalScrollBar().value()) / self._pixels_per_second)

def _rebuild_after_zoom(self) -> None:
    """缩放后重建背景、重排全部音符与音域框，并通知标尺刷新。"""
    self._build_background(self._current_total_seconds)
    for note in self._notes:
        self._update_item_geometry(note)
    self._update_range_item_geometry()
    if self._playhead_item is not None:
        self._draw_playhead()
    self.zoomChanged.emit()
    self.viewport().update()
```

> `_draw_playhead()` 在 Task 10 完整实现；本任务先把 `set_playhead` 的绘制部分抽成无参方法 `_draw_playhead()`，用 `self._playhead_display_seconds`（本任务在 `__init__` 初始化为 `0.0`）计算 x，保证缩放时可复用。

**Step 5: 验证**

Run: `.venv\Scripts\python.exe -m unittest tests.test_zoom_math -v`
Expected: PASS（5 个用例）

手动验收：Shift+滚轮向上，鼠标下的时间点屏幕位置不动、时间轴变宽；向下缩小同理；不按 Shift 时仍为纵向滚动；缩放后拖动音符、调整时长、开启量化后的吸附结果与缩放前一致。

**Step 6: 提交**

```bash
git add piano_roll.py
git commit -m "feat(piano-roll): instance-level horizontal zoom with shift+wheel"
```

### Task 8: 顶部拍数标尺

**Files:**
- Modify: `piano_roll.py`（新增 `_TimeRulerWidget` 类，位于 `_PianoRollCanvas` 之前）
- Modify: `piano_roll.py` 导入区（`QVBoxLayout`）
- Modify: `piano_roll.py:771-785`（`PianoRollWidget` 布局改为纵向：标尺 + 原横向容器）

**Interfaces:**
- Consumes: `canvas.viewport_x_for_time`、`canvas.time_at_viewport_x`、`canvas.pixels_per_second()`（Task 7 提供）
- Produces: `_TimeRulerWidget`，信号 `playheadRequested = pyqtSignal(float)`；`_TimeRulerWidget.set_beat_grid(seconds_per_beat, beats_per_measure)`；`_PianoRollCanvas.is_read_only() -> bool`（本任务补充）；`PianoRollWidget.set_beat_grid(...)`

<!-- comet-task-ref:f5d05313-6b44-433f-9e1f-861ddc36dd44 -->
<!-- comet-task-ref:6698d655-5b9e-45ad-87d7-3da758136a7c -->

**Step 1: 实现标尺控件**

先在 `QtWidgets` 导入列表中加入 `QVBoxLayout`（`QPainter`、`QColor`、`QPen` 已在导入列表中）。

```python
RULER_HEIGHT = 28


class _TimeRulerWidget(QWidget):
    """钢琴窗顶部的固定拍数标尺：显示小节/拍刻度，点击或拖动定位播放辅助线。"""

    playheadRequested = pyqtSignal(float)

    def __init__(self, canvas: "_PianoRollCanvas", parent=None):
        super().__init__(parent)
        self._canvas = canvas
        self._seconds_per_beat: Optional[float] = None
        self._beats_per_measure = 4
        self.setFixedHeight(RULER_HEIGHT)
        self.setMouseTracking(True)
        canvas.zoomChanged.connect(self.update)
        canvas.horizontalScrollBar().valueChanged.connect(lambda _v: self.update())
        canvas.horizontalScrollBar().rangeChanged.connect(lambda _a, _b: self.update())

    def set_beat_grid(self, seconds_per_beat: Optional[float], beats_per_measure: int) -> None:
        self._seconds_per_beat = seconds_per_beat if seconds_per_beat and seconds_per_beat > 0 else None
        self._beats_per_measure = max(1, int(beats_per_measure))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1B2631"))
        painter.setPen(QPen(QColor("#5D6D7E"), 1))
        seconds_per_measure = (
            self._seconds_per_beat * self._beats_per_measure if self._seconds_per_beat else None
        )
        span = self._canvas.width() / self._canvas.pixels_per_second()
        start_time = self._canvas.time_at_viewport_x(0.0)
        end_time = start_time + span

        if seconds_per_measure:
            measure = int(start_time // seconds_per_measure)
            while measure * seconds_per_measure <= end_time:
                self._draw_tick(painter, measure * seconds_per_measure, str(measure + 1), tall=True)
                if self._seconds_per_beat:
                    for beat in range(1, self._beats_per_measure):
                        self._draw_tick(
                            painter,
                            measure * seconds_per_measure + beat * self._seconds_per_beat,
                            "",
                            tall=False,
                        )
                measure += 1
        else:
            second = int(start_time)
            while second <= end_time:
                self._draw_tick(painter, float(second), f"{second}s", tall=True)
                second += 1

    def _draw_tick(self, painter: QPainter, seconds: float, text: str, tall: bool) -> None:
        x = self._canvas.viewport_x_for_time(seconds)
        if x < -40 or x > self.width() + 40:
            return
        top = 0 if tall else RULER_HEIGHT - 8
        painter.setPen(QPen(QColor("#85929E" if tall else "#4D5656"), 1))
        painter.drawLine(int(x), top, int(x), RULER_HEIGHT)
        if text:
            painter.setPen(QPen(QColor("#D5D8DC"), 1))
            painter.drawText(int(x) + 3, 12, text)

    def mousePressEvent(self, event):
        if self._canvas.is_read_only():
            return
        self.playheadRequested.emit(self._canvas.time_at_viewport_x(float(event.pos().x())))

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and not self._canvas.is_read_only():
            self.playheadRequested.emit(self._canvas.time_at_viewport_x(float(event.pos().x())))
```

**Step 2: 接入布局**

`PianoRollWidget.__init__` 改为：

```python
self._ruler = _TimeRulerWidget(self._canvas, parent=self)
content = QHBoxLayout()
content.setContentsMargins(0, 0, 0, 0)
content.setSpacing(0)
content.addWidget(self._keyboard)
content.addWidget(self._canvas)

layout = QVBoxLayout(self)
layout.setContentsMargins(0, 0, 0, 0)
layout.setSpacing(0)
layout.addWidget(self._ruler)
layout.addLayout(content, 1)
```

同时把 `self._canvas.is_read_only()` 补到画布上：

```python
def is_read_only(self) -> bool:
    return self._read_only
```

**Step 3: 透传拍长**

`PianoRollWidget` 增加：

```python
def set_beat_grid(self, seconds_per_beat: Optional[float], beats_per_measure: int) -> None:
    self._ruler.set_beat_grid(seconds_per_beat, beats_per_measure)
```

**Step 4: 验证**

Run: `.venv\Scripts\python.exe -c "import piano_roll"`，Expected: 无输出。
手动验收：加载 4/4、120 BPM 曲目 → 标尺每 2 秒一个小节序号且与小节线对齐；水平滚动、缩放、改变窗口宽度后仍对齐；纵向滚动时标尺不动。

**Step 5: 提交**

```bash
git add piano_roll.py
git commit -m "feat(piano-roll): add top beat ruler synced with canvas"
```

### Task 9: 缩放后整面重排与标尺刷新

**Files:**
- Modify: `piano_roll.py`（`_rebuild_after_zoom` 完善）

**Interfaces:**
- Consumes: Task 7 的 `_rebuild_after_zoom`、Task 8 的 `zoomChanged` 连接
- Produces: 缩放后背景、音符、音域框、播放辅助线、标尺全部在同一比例下刷新

<!-- comet-task-ref:f583e0c4-0184-4964-8046-fe64a2fb8ef5 -->

**Step 1: 补齐重排**

确认 `_rebuild_after_zoom` 依次执行：`_build_background(self._current_total_seconds)` → 遍历 `self._notes` 调 `_update_item_geometry` → `_update_range_item_geometry()` → 重绘播放辅助线 → `zoomChanged.emit()`。

**Step 2: 处理场景宽度**

在 `_rebuild_after_zoom` 末尾补：

```python
rect = self._scene.sceneRect()
self._scene.setSceneRect(0, 0, max(rect.width(), 400), rect.height())
```

**Step 3: 验证**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: PASS（现有 6 个 + 新增 21 个用例）

手动验收：反复放大/缩小后，音符、秒线、小节线、音域框、播放辅助线、标尺刻度仍严格对齐；缩放后拖动音符并按量化吸附，落点秒数与缩放倍数无关。

**Step 4: 提交**

```bash
git add piano_roll.py
git commit -m "feat(piano-roll): reflow all layers after zoom"
```

### Task 10: 播放辅助线锚点与定位

**Files:**
- Modify: `piano_roll.py:121-165`（初始化 `_playhead_anchor_seconds`、`_playhead_display_seconds`）
- Modify: `piano_roll.py:255-272`（`set_playhead`）
- 新增方法：`set_playhead_anchor`、`get_playhead_position`、`_draw_playhead`
- Modify: `piano_roll.py:771-830`（`PianoRollWidget` 透传新方法）

**Interfaces:**
- Produces: `set_playhead_anchor(seconds: float)`、`get_playhead_position() -> float`；`set_playhead(None)` 回落到锚点并保持可见

<!-- comet-task-ref:551d3ef7-3fa3-4020-8ff0-b25d45b1490e -->

**Step 1: 初始化状态**

`__init__` 加：

```python
self._playhead_anchor_seconds = 0.0
self._playhead_display_seconds = 0.0
```

**Step 2: 重写播放辅助线**

```python
def set_playhead_anchor(self, seconds: float) -> None:
    """设置用户定位的播放辅助线位置（粘贴与播放起点都以此为基准）。"""
    self._playhead_anchor_seconds = max(0.0, float(seconds))
    self.set_playhead(self._playhead_anchor_seconds)

def get_playhead_position(self) -> float:
    return self._playhead_anchor_seconds

def set_playhead(self, seconds: Optional[float]) -> None:
    """更新辅助线的显示位置；传 None 表示播放结束，回落到用户定位的锚点。"""
    if seconds is None:
        self._playhead_display_seconds = self._playhead_anchor_seconds
    else:
        self._playhead_display_seconds = max(0.0, float(seconds))
    self._draw_playhead()

def _draw_playhead(self) -> None:
    if self._playhead_item is not None:
        self._scene.removeItem(self._playhead_item)
        self._playhead_item = None
    x = self._time_to_x(self._playhead_display_seconds)
    height = PITCH_COUNT * ROW_HEIGHT
    line = QGraphicsLineItem(x, 0, x, height)
    line.setPen(QPen(QColor("#F1C40F"), 2))
    line.setZValue(10)
    line.setAcceptedMouseButtons(Qt.NoButton)
    self._scene.addItem(line)
    self._playhead_item = line
    self.ensureVisible(QRectF(x - 5, 0, 10, height), 60, 0)
```

**Step 3: 加载曲目时重置**

在 `set_notes` 末尾把播放辅助线重置为锚点 0：

```python
self._playhead_anchor_seconds = 0.0
self._playhead_display_seconds = 0.0
self._draw_playhead()
```

**Step 4: 标尺联动**

`PianoRollWidget.__init__` 中连接：

```python
self._ruler.playheadRequested.connect(self._canvas.set_playhead_anchor)
```

并透传 `set_playhead_anchor` / `get_playhead_position`。

**Step 5: 验证**

Run: `.venv\Scripts\python.exe -c "import piano_roll"`，Expected: 无输出。
手动验收：加载曲目后辅助线在 0s；点击标尺 8s 处辅助线移到 8s；按住左键拖动连续跟随；点击「弹奏」播放到 12s 停止后，辅助线回到 8s 且仍可见。

**Step 6: 提交**

```bash
git add piano_roll.py
git commit -m "feat(piano-roll): persistent playhead anchor with ruler seeking"
```

### Task 11: GUI 拍长传递、切曲重置与播放期禁用定位

**Files:**
- Modify: `gui.py:952-963`（`_load_piano_roll`）
- Modify: `piano_roll.py`（标尺在只读时忽略鼠标，Task 8 已实现，核对即可）

**Interfaces:**
- Consumes: `PianoRollWidget.set_beat_grid`、`set_playhead_anchor`
- Produces: 切换曲目后标尺按新 BPM/拍号重算、辅助线归零

<!-- comet-task-ref:af5ae4f2-254c-4886-9a23-7edb09a54b1e -->
<!-- comet-task-ref:30bc7557-f434-43aa-aeb2-431c923da0ba -->

**Step 1: 传拍长与重置锚点**

把 `_load_piano_roll` 中：

```python
self.piano_roll.set_measure_grid(seconds_per_beat * numerator)
```

改为：

```python
self.piano_roll.set_measure_grid(seconds_per_beat * numerator)
self.piano_roll.set_beat_grid(seconds_per_beat, numerator)
```

并把：

```python
self.piano_roll.set_playhead(None)
```

改为：

```python
self.piano_roll.set_playhead_anchor(0.0)
```

**Step 2: 核对播放期只读**

Run: `rg -n "is_read_only|set_read_only" piano_roll.py gui.py`
Expected: `_TimeRulerWidget.mousePressEvent` / `mouseMoveEvent` 均在只读时直接返回；`gui.start_playing` 调用 `set_read_only(True)`，停止与结束时调用 `False`。

**Step 3: 验证**

Run: `.venv\Scripts\python.exe -c "import gui"`，Expected: 无输出（或无 PyQt 弹窗的直接导入错误）。

手动验收：从 4/4、120 BPM 曲目切到 3/4、90 BPM 曲目 → 标尺按新拍号重新标注、辅助线回到 0；播放中点击标尺任意位置 → 播放不中断、辅助线仍随进度移动。

**Step 4: 提交**

```bash
git add gui.py piano_roll.py
git commit -m "feat(gui): feed beat grid and reset playhead on track switch"
```

### Task 12: 从播放辅助线开始播放

**Files:**
- Modify: `gui.py:1116-1174`（`start_playing`）
- Modify: `gui.py:1101-1107`（`on_play_progress`）
- Modify: `gui.py`（`__init__` 播放相关变量区，约 239 行，新增 `self._playback_start_seconds = 0.0`）
- Modify: `gui.py` 顶部导入（从 `piano_roll` 导入 `playback_notes_from_position`）

**Interfaces:**
- Consumes: `PianoRollWidget.get_playhead_position()`、`playback_notes_from_position`
- Produces: `self._playback_start_seconds: float`，播放进度 = 起点 + 已耗时

<!-- comet-task-ref:03e77383-c763-4ea0-aa0d-4f00fb1301df -->

**Step 1: 导入纯函数并初始化起点**

`gui.py` 导入区加入：

```python
from piano_roll import playback_notes_from_position
```

`__init__` 播放变量区加入：

```python
self._playback_start_seconds = 0.0
```

**Step 2: 过滤并平移播放音符**

在 `start_playing` 中，`notes = self.piano_roll.get_notes()` 之后插入：

```python
playhead = self.piano_roll.get_playhead_position()
notes = playback_notes_from_position(notes, playhead)
if not notes:
    QMessageBox.warning(self, "提示", "当前位置之后没有可播放的音符")
    return
self._playback_start_seconds = playhead
```

**Step 3: 进度叠加起点**

`on_play_progress` 中：

```python
self.piano_roll.set_playhead(self._playback_start_seconds + elapsed)
```

**Step 4: 验证**

Run: `.venv\Scripts\python.exe -m unittest tests.test_playback_start -v`
Expected: PASS（6 个用例）

手动验收：辅助线放到 10s 点「弹奏」→ 只播放 10s 之后的音符、辅助线从 10s 起移动；把辅助线放到最后一个音符之后 → 提示「当前位置之后没有可播放的音符」且不进入播放状态；跨越辅助线的长音符不重新触发。

**Step 5: 提交**

```bash
git add gui.py
git commit -m "feat(gui): start playback from playhead position"
```

### Task 13: 「播放」按钮改名为「弹奏」

**Files:**
- Modify: `gui.py:604`（初始化）
- Modify: `gui.py:1200`（`stop_playing`）
- Modify: `gui.py:1226`（`on_play_finished`）

**Interfaces:**
- Produces: 空闲文案 `▶️ 弹奏`；播放中 `⏹️ 停止(ESC)`；`objectName` 不变

<!-- comet-task-ref:1507d0cc-75a0-418a-ba5d-b68f7c0a4038 -->

**Step 1: 替换三处空闲文案**

把三处 `"▶️ 播放"` 改为 `"▶️ 弹奏"`（初始化、`stop_playing`、`on_play_finished`），不要改动 `"⏹️ 停止(ESC)"`。

**Step 2: 确认无遗漏**

Run: `rg -n "播放\"|弹奏" gui.py`
Expected: 按钮空闲文案均为 `▶️ 弹奏`；日志与提示中的「播放」字样保持不变。

**Step 3: 验证**

手动验收：启动程序按钮显示「▶️ 弹奏」；点击后变「⏹️ 停止(ESC)」；停止或播放结束后恢复「▶️ 弹奏」，按钮样式与点击行为不变。

**Step 4: 提交**

```bash
git add gui.py
git commit -m "feat(gui): rename play button label to 弹奏"
```

### Task 14: 集成验证

**Files:** 无新增；只运行检查与手动走查

**Interfaces:**
- Consumes: 前 13 个任务的全部产出
- Produces: 构建与验收入口证据

<!-- comet-task-ref:6ecb67e7-30f2-4c49-be31-7345031ee40a -->
<!-- comet-task-ref:07da8a52-7345-4914-8186-5a395f587ea2 -->

**Step 1: 全量测试**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: 全部 PASS（含既有 `test_edge_note_mapping` 的 6 个 C6 边界用例）

**Step 2: 按 specs 手动走查**

逐条核对：
1. `piano-roll-note-editing`：复制多音符、剪切、连续粘贴、空剪贴板、升/降八度、越界跳过。
2. `piano-roll-timeline`：标尺小节对齐、点击/拖动定位、默认 0s、停止后回到锚点、播放中辅助线随进度且标尺不可定位、Shift+滚轮双向缩放与锚点不漂移、缩放后拖动与量化正确。
3. `piano-roll-playback-control`：从 10s 播放、跨辅助线音符不重触发、尾部无音符提示、按钮文案三态。

**Step 3: 记录结果**

把每条通过/未通过写进 `docs/openspec/changes/piano-roll-editing-playback-tools/verification.md`（Verify 阶段会再次使用）；未通过项先修复再重跑对应步骤。

**Step 4: 提交**

```bash
git add docs/openspec/changes/piano-roll-editing-playback-tools/verification.md
git commit -m "test: record manual acceptance results for piano roll editing"
```

## Workflow follow-up

- 完成本计划后按 Comet Build 流程运行 `comet state complete-build`，再以 `comet guard <change> build --apply -- .venv\Scripts\python.exe -m unittest discover -s tests -v` 提交检查收据，随后进入 Verify。
- Verify 通过后由用户选择归档/交付方式；不自动推送。
