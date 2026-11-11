# Comet Design Handoff

- Change: piano-roll-modes-and-daw-editing
- Phase: design
- Mode: compact
- Context hash: 26dfa7874cf3033c67c7742c21a6933f954c479bc678abbcf428034985a0faf6

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/piano-roll-modes-and-daw-editing/proposal.md

- Source: docs/openspec/changes/piano-roll-modes-and-daw-editing/proposal.md
- Lines: 1-37
- SHA256: 9dd8fa441b68608a6ea9a2387c9b5351544c7d1fe4917120284961504f3aa1a1

```md
# 铺面演奏/编辑模式与 DAW 一致的基础编辑

## Why

当前「显示映射 / 隐藏映射」只控制黄框是否可见，演奏准备时铺面仍可被误编辑；钢琴窗的基础编辑与主流 DAW 习惯不一致（单击空白会新建音符、没有方向键微调、只有右边缘能改时长），按钮高度也与下拉框不齐。本次把黄框语义升级为「演奏 / 编辑」两种模式，并把钢琴窗基础编辑对齐常见 DAW 习惯。

## What Changes

- 工具栏按钮文案改为「🎹 演奏模式 / ✏️ 编辑模式」：
  - 演奏模式：显示黄色映射框，铺面只读（不可选择、拖动、新建、删除、粘贴）；工具栏选项与顶部标尺/播放辅助线仍可操作。
  - 编辑模式：隐藏黄色映射框，钢琴窗、BPM 与播放辅助线全部可操作。
- 缩放快捷键由 Shift+滚轮改为 Ctrl+滚轮。
- 钢琴窗基础编辑对齐 DAW：
  - 单击空白：取消选择（不再新建音符）；双击空白：在该位置新建音符；拖动空白：矩形框选。
  - 拖动音符主体移动；拖动左边缘调整起始时间（结束时间不变）；拖动右边缘调整时长（现有行为）。
  - 方向键 ←/→ 按当前量化网格移动选中音符（量化关闭时用默认步长）；↑/↓ 移调一个半音；Shift+↑/↓ 仍为八度。
  - Delete、Ctrl+A、Ctrl+C/X/V 保持现有行为。
- 所有工具按钮的上下高度与下拉框一致。
- 页脚文字改为「created by 66maer updated by Loveanope_Dev」。

## Capabilities

### New Capabilities

- `piano-roll-editing-modes`：演奏 / 编辑模式的切换、各自的可操作范围与按钮文案。
- `piano-roll-daw-editing`：与主流 DAW 一致的钢琴窗基础鼠标/键盘编辑行为。

### Modified Capabilities

- `piano-roll-timeline`：缩放修饰键由 Shift 改为 Ctrl（原 Shift+滚轮要求被替换）。

## Impact

- `piano_roll.py`：模式只读范围、单击/双击空白行为、左边缘调整起始时间、方向键移动与移调、滚轮修饰键。
- `gui.py`：模式按钮文案与切换逻辑（黄框可见性 + 只读）、按钮高度样式、页脚文字。
- 不改播放、BPM、播放列表、音域框筛选与 MIDI 导出逻辑。
- 已知取舍：演奏模式下不允许任何音符编辑，包括删除与粘贴；需要编辑时切回编辑模式。

```

## docs/openspec/changes/piano-roll-modes-and-daw-editing/design.md

- Source: docs/openspec/changes/piano-roll-modes-and-daw-editing/design.md
- Lines: 1-104
- SHA256: 1a3ea8020588f276aac14b718f6cd747cbcf18fcbb6e317512ed2bce5830fb29

[TRUNCATED]

```md
# Design

行为需求以 `specs/piano-roll-editing-modes`、`specs/piano-roll-daw-editing`、`specs/piano-roll-timeline` 三份 delta spec 为准；本文说明实现方式与取舍。

## Context

- 工具栏「🟨 显示映射 / 隐藏映射」当前只切换黄框可见性（`gui.on_range_toggle_clicked`）。
- `_PianoRollCanvas` 的所有编辑入口都受 `_read_only` 控制：`mousePressEvent` 直接 return，`keyPressEvent` 转发给父类；`set_read_only(True)` 目前只在播放期间使用。
- 空白区域当前行为：按下记录 `_pending_create_note` 并进入 `select-rect-or-create`，拖动形成框选、不拖动则在松开时新建音符。
- 音符命中区域只区分「右边缘 6px 调整时长」与「主体移动」，没有左边缘。
- `keyPressEvent` 只处理 Ctrl+A、Delete、Ctrl+C/X/V、Shift+↑/↓；没有普通方向键。
- `wheelEvent` 以 `ShiftModifier` 触发缩放。
- 全部按钮样式由全局 QSS 控制（`QPushButton` padding），高度高于下拉框。

## Goals / Non-Goals

**Goals:**

- 用同一套 `_read_only` 机制表达「演奏模式」，避免维护第二套交互开关。
- 空白区域三种手势（单击/双击/拖动）互不干扰。
- 方向键遵循当前量化网格；无量化时用固定默认步长。
- 修饰键变更不破坏现有缩放逻辑。

**Non-Goals:**

- 不做多轨、力度、复制拖动（Ctrl+拖动克隆）、吸附开关切换等扩展 DAW 能力。
- 不实现「演奏模式自动从辅助线开始播放」等联动。
- 不改播放、BPM、播放列表与音域框筛选。

## Decisions

### 1. 模式 = 黄框可见性 + 只读

- `on_range_toggle_clicked` 改为：黄框可见 ⇔ 演奏模式。
- 进入演奏模式：`piano_roll.set_instrument_range_visible(True)` 且 `piano_roll.set_read_only(True)`。
- 进入编辑模式：`set_instrument_range_visible(False)` 且 `set_read_only(False)`（播放中仍由播放逻辑保持只读，见风险）。
- 按钮文案按「点击后进入的模式」：演奏中显示「✏️ 编辑模式」，编辑中显示「🎹 演奏模式」。
- 未采用单独的 `mode` 字段：`_read_only` 已覆盖所有编辑入口，复用最稳。

### 2. 只读时的播放辅助线

- 标尺已监听 `is_read_only()`；演奏模式下 `mousePressEvent/mouseMoveEvent` 直接 return，会把「演奏模式下可用辅助线」破坏。
- 决策：把「播放中禁止标尺定位」改用独立状态 `_playback_locked`（或 `is_playing` 传入），不再复用 `is_read_only`；`set_playhead_anchor` 在演奏模式仍可调用。
- `PianoRollWidget` 新增 `set_playhead_locked(bool)` 供播放期间锁定标尺。

### 3. 空白区域手势

- `mousePressEvent`：空白处只记录按下位置并进入 `select-rect-or-create`，不再立即准备新建。
- `mouseReleaseEvent`：若未发生拖动：
  - 单击 → `_set_selection(set())`；
  - 双击（Qt 的 `mouseDoubleClickEvent`）→ 新建音符并选中。
- 拖动 → 框选（现有逻辑不变）。
- 双击事件单独实现 `mouseDoubleClickEvent`，避免与单击的「取消选择」竞争：双击时先清空再创建。

### 4. 左边缘调整起始时间

- 命中测试增加 `near_left_edge = scene_pos.x() - rect.left() <= RESIZE_MARGIN`，且左边缘不与右边缘同时命中（短音符时优先右边缘）。
- 新模式 `resize-start`：拖动时新起点 = 吸附后的时间，钳制到 `[0, end - MIN_NOTE_DURATION]`，`duration = end - new_start`。
- 右边缘逻辑保持不变。

### 5. 方向键

- 量化开启：步长 = `_quantize_seconds`；关闭：`DEFAULT_NUDGE_SECONDS = 0.1`。
- ←/→：对整组选中音符按步长平移（保持相对时距），起点钳制 ≥0。
- ↑/↓：复用 `octave_shift_pitches` 的单半音版本（新增 `semitones` 参数或调用 delta=±1）；越界跳过。
- Shift+↑/↓ 仍走 ±12。
- 无选中时直接返回。

### 6. Ctrl+滚轮

- `wheelEvent` 判断 `ControlModifier` 而非 `ShiftModifier`；其余锚点/重排逻辑不变。
- 按住 Ctrl 且 `angleDelta().y()==0` 时保持原「纯横向滚轮不缩放」保护。

### 7. 按钮高度与页脚

- 在全局样式表追加 `QPushButton { max-height: 26px; min-height: 26px; }`（与 `QComboBox` 高度一致），或对按钮统一 `setFixedHeight(26)`；优先 QSS，改动集中。
- 页脚文案改为 `created by 66maer updated by Loveanope_Dev`。

## Risks / Trade-offs


```

Full source: docs/openspec/changes/piano-roll-modes-and-daw-editing/design.md

## docs/openspec/changes/piano-roll-modes-and-daw-editing/tasks.md

- Source: docs/openspec/changes/piano-roll-modes-and-daw-editing/tasks.md
- Lines: 1-41
- SHA256: a0b0195bd378d195f4d6a2c443db50fac89bccc6e4b762d1620a6c88b632c53d

```md
# Tasks

## 1. 模式切换

- [ ] 1.1 `gui.on_range_toggle_clicked` 改为「演奏/编辑」：黄框可见 ⇔ 演奏模式，并同步 `piano_roll.set_read_only`；按钮文案改为「🎹 演奏模式 / ✏️ 编辑模式」 <!-- comet-task:b36f2527-04b8-4abd-95d6-18d32373370f -->
- [ ] 1.2 标尺定位与只读解耦：`PianoRollWidget` 增加 `set_playhead_locked(bool)`，播放开始/停止时设置；标尺用该状态而非 `is_read_only` 决定是否响应鼠标 <!-- comet-task:8f30ba86-b6fb-4f61-b01b-88d25f1d652c -->
- [ ] 1.3 手动验收：演奏模式下铺面不可编辑、标尺仍可定位、工具栏可用；编辑模式下全部恢复；播放中切模式不解锁只读 <!-- comet-task:0de529dd-54de-4bdf-b209-f45308dd571b -->

## 2. DAW 空白区域行为

- [ ] 2.1 空白区域：单击清空选择、双击新建并选中、拖动框选；新增 `mouseDoubleClickEvent`，互不干扰 <!-- comet-task:b30b7093-398c-4fc7-96cb-ded536578053 -->
- [ ] 2.2 offscreen UI 测试覆盖三种手势（音符数、选中集合断言） <!-- comet-task:7b45562d-5a98-43f3-9b42-b5e3bef4eeb1 -->

## 3. 左边缘调整起始时间

- [ ] 3.1 命中测试区分左/右边缘（短音符优先右边缘）；新增 `resize-start` 拖拽：结束时间不变、起点吸附、钳制到最小时长 <!-- comet-task:5896f990-0f22-448c-96ea-fd304b4f2de9 -->
- [ ] 3.2 UI 测试：左边缘拖动改变 start/end 关系；拖过结尾停在最小时长 <!-- comet-task:9ea42864-bdb8-4402-ac73-a718b83ce065 -->

## 4. 方向键微调

- [ ] 4.1 新增方向键处理：←/→ 按量化步长（关闭时 0.1s）平移选中音符；↑/↓ 半音移调；Shift+↑/↓ 八度；越界跳过、无选中无变化 <!-- comet-task:fe8ee5e7-1230-4113-8dd3-1e8416af0c9d -->
- [ ] 4.2 UI 测试：量化 1/8 步长、半音/八度、无选中 <!-- comet-task:730e6150-fbd6-4f72-af86-e8896206bb7e -->

## 5. Ctrl+滚轮缩放

- [ ] 5.1 `wheelEvent` 由 Shift 改为 Ctrl 触发缩放；Shift+滚轮恢复普通滚动；更新既有缩放测试 <!-- comet-task:84210419-5582-4e9f-9ee6-98880309274b -->
- [ ] 5.2 手动验收：Ctrl+滚轮锚点不漂移；Shift+滚轮不再缩放 <!-- comet-task:5bba82b8-7882-4a16-92ef-44b7b07342b4 -->

## 6. 按钮高度与页脚

- [ ] 6.1 全局 QSS 让按钮上下高度与下拉框一致（约 26px），确认播放/保存/导入/新建/删除等按钮统一 <!-- comet-task:6634e911-8a74-4a7e-80b1-b7b7d21c3afc -->
- [ ] 6.2 页脚文案改为 `created by 66maer updated by Loveanope_Dev` <!-- comet-task:0fa73f88-5cf8-438f-9d79-5b772d45a01c -->

## 7. 集成验证

- [ ] 7.1 运行 `.venv\Scripts\python.exe -m unittest discover -s tests -v`，确认既有 99 项（含改为 Ctrl 的缩放测试）与本轮新增全部通过 <!-- comet-task:4691400d-86f8-49c6-afd4-4deb02ebf5ba -->
- [ ] 7.2 手动走查：模式切换、空白三种手势、左右边缘、方向键、Ctrl/Shift+滚轮、按钮高度、页脚文字 <!-- comet-task:ffe4dbd3-9d09-4407-b1c1-2a7ab7e75bed -->

## Workflow follow-up

- 完成 Verify 后按 Comet 交付流程归档或交付，具体方式由用户确认。

```

## docs/openspec/changes/piano-roll-modes-and-daw-editing/.openspec.yaml

- Source: docs/openspec/changes/piano-roll-modes-and-daw-editing/.openspec.yaml
- Lines: 1-2
- SHA256: b8f20def63a86ae4075c5499ff9ed413265d8704692a8493712424dc3f28d8e3

```md
schema: spec-driven
created: 2026-11-11

```

## docs/openspec/changes/piano-roll-modes-and-daw-editing/specs/piano-roll-daw-editing/spec.md

- Source: docs/openspec/changes/piano-roll-modes-and-daw-editing/specs/piano-roll-daw-editing/spec.md
- Lines: 1-59
- SHA256: a58c41d8d0de027b52710828546f95521bef40e4cda4476ba02caae16cc52f21

```md
# Spec Delta

## Purpose

让钢琴窗的基础鼠标与键盘编辑行为与主流 DAW 的钢琴卷帘保持一致。

## ADDED Requirements

### Requirement: DAW 一致的空白区域行为

铺面空白区域 SHALL：单击取消当前选择且不新建音符；双击在双击位置新建一个音符（音高取所在行、起始时间取所在时间，时长为当前量化格或默认时长）；按住拖动形成矩形框选。三种行为 MUST 互不干扰。

#### Scenario: 单击空白取消选择

- **WHEN** 已有选中音符时单击空白区域
- **THEN** 选择被清空，且不新增音符

#### Scenario: 双击空白新建

- **WHEN** 在空白处双击
- **THEN** 在该音高与时间位置新建一个音符并被选中

#### Scenario: 拖动空白框选

- **WHEN** 在空白处按住左键拖动
- **THEN** 出现矩形选区，松开后选中与矩形相交的音符，且不新建音符

### Requirement: 方向键微调

编辑模式下，方向键 SHALL 作用于选中音符：←/→ 按当前量化网格步长移动起始时间（量化关闭时使用默认步长），↑/↓ 移调一个半音；Shift+↑/↓ MUST 仍为八度移动。移动/移调 MUST 保持相对时距与音程关系，并标记未保存。

#### Scenario: 左右移动

- **WHEN** 量化 1/8 下选中音符按 → 一次
- **THEN** 音符起始时间增加一个 1/8 网格的秒数，其余选中音符同步移动

#### Scenario: 上下移调

- **WHEN** 选中音符按 ↑
- **THEN** 音高增加一个半音；按 Shift+↑ 仍增加一个八度

#### Scenario: 无选中时按键

- **WHEN** 没有选中音符时按方向键
- **THEN** 铺面不发生变化

### Requirement: 左边缘调整起始时间

拖动音符左边缘 SHALL 调整该音符的起始时间并保持结束时间不变，时长为正且不小于最小时长；量化开启时起点吸附到网格。拖动右边缘的既有行为保持不变。

#### Scenario: 拖左边缘缩短

- **WHEN** 拖动一个 1.0s 长音符的左边缘向右 0.2s（量化关闭）
- **THEN** 起始时间增加 0.2s，结束时间不变，时长变为 0.8s

#### Scenario: 左边缘不能超过结尾

- **WHEN** 把左边缘拖到结束时间之后
- **THEN** 起始时间停在「结束时间 − 最小时长」，音符不被删除

```

## docs/openspec/changes/piano-roll-modes-and-daw-editing/specs/piano-roll-editing-modes/spec.md

- Source: docs/openspec/changes/piano-roll-modes-and-daw-editing/specs/piano-roll-editing-modes/spec.md
- Lines: 1-40
- SHA256: 083f7d1f446898405de271275eb1380a4f2b4bd0afd5340db46aca91970c946e

```md
# Spec Delta

## Purpose

提供「演奏 / 编辑」两种模式：演奏模式显示映射框并锁定铺面，编辑模式恢复全部编辑能力。

## ADDED Requirements

### Requirement: 演奏模式与编辑模式切换

工具栏 SHALL 提供「🎹 演奏模式 / ✏️ 编辑模式」切换按钮。演奏模式 MUST 显示黄色映射框并把铺面切换为只读；编辑模式 MUST 隐藏映射框并恢复全部编辑能力。按钮文案 MUST 反映「点击后会进入的模式」（编辑中显示「🎹 演奏模式」，演奏中显示「✏️ 编辑模式」）。

#### Scenario: 切到演奏模式

- **WHEN** 编辑模式下点击「🎹 演奏模式」
- **THEN** 黄色映射框出现，铺面进入只读，按钮文案变为「✏️ 编辑模式」

#### Scenario: 切回编辑模式

- **WHEN** 演奏模式下点击「✏️ 编辑模式」
- **THEN** 黄色映射框隐藏，铺面恢复可编辑，按钮文案变为「🎹 演奏模式」

### Requirement: 演奏模式的可操作范围

演奏模式下，钢琴窗 SHALL 拒绝选择、拖动、新建、删除、粘贴与方向键编辑；顶部标尺点击/拖动定位播放辅助线、工具栏选项（含 BPM、量化、映射范围、播放/保存）MUST 保持可用。

#### Scenario: 演奏模式下点击音符

- **WHEN** 演奏模式下点击或拖动铺面中的音符
- **THEN** 音符不被选中、不移动，铺面数据不变

#### Scenario: 演奏模式下键盘

- **WHEN** 演奏模式下按 Delete、Ctrl+V 或方向键
- **THEN** 铺面与剪贴板都不发生变化

#### Scenario: 演奏模式下定位播放辅助线

- **WHEN** 演奏模式下点击顶部标尺
- **THEN** 播放辅助线移动到点击位置，可继续播放

```

## docs/openspec/changes/piano-roll-modes-and-daw-editing/specs/piano-roll-timeline/spec.md

- Source: docs/openspec/changes/piano-roll-modes-and-daw-editing/specs/piano-roll-timeline/spec.md
- Lines: 1-22
- SHA256: 6d892224915ddbc3d6bc18dba1ad3c4276047343d60b8cbd87a29b8a48436572

```md
# Spec Delta

## MODIFIED Requirements

### Requirement: Shift+滚轮横向缩放

缩放修饰键由 Shift 改为 Ctrl：按住 Ctrl 滚动滚轮 SHALL 横向放大或缩小时间轴（向上放大、向下缩小），缩放 MUST 以鼠标指针所在的时间点为锚点，使该时间点在缩放前后保持在同一横向屏幕位置，并受 10～600 px/s 的最小与最大比例限制。按住 Shift 滚动滚轮 MUST 恢复为普通滚动，不再改变缩放比例；其余既有要求（不按修饰键时保持原有滚动、缩放后时间语义不变）保持不变。

#### Scenario: 向上滚动放大

- **WHEN** 按住 Ctrl 把滚轮向上滚动一格
- **THEN** 时间轴放大，鼠标指针下的时间点在屏幕上保持不动，可见时间范围变短

#### Scenario: 向下滚动缩小

- **WHEN** 按住 Ctrl 把滚轮向下滚动一格
- **THEN** 时间轴缩小，鼠标指针下的时间点保持不动，可见时间范围变长

#### Scenario: 不按 Shift 时保持原有滚动

- **WHEN** 不按 Ctrl 滚动滚轮（包括按住 Shift）
- **THEN** 铺面按原有行为滚动，横向缩放比例不变

```
