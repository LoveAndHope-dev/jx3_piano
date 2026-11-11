---
comet_change: piano-roll-modes-and-daw-editing
role: technical-design
canonical_spec: openspec
archived-with: 2026-11-11-piano-roll-modes-and-daw-editing
status: final
---

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

- **播放中切到演奏模式**：播放本身已 `set_read_only(True)`，切回编辑模式时若仍在播放不得解除只读。→ 编辑模式恢复时使用 `self.is_playing` 决定是否保持只读。
- **双击与单击竞争**：Qt 双击会先发 press/release，单击若在 release 清空选择会闪一下；实现时双击路径先创建并选中，单击只在「未发生拖动且非双击」时清空，必要时用 250ms 定时器区分，若复杂则接受轻微闪烁并记录。
- **左边缘与短音符**：时长小于两个 RESIZE_MARGIN 时左右命中重叠 → 固定优先右边缘，左边缘需要更靠左的点击。
- **方向键与系统焦点**：铺面需获得焦点；点击后已有焦点，保持现有 `StrongFocus`。
- **量化关闭的默认步长**：0.1s 是经验值，规格未规定具体值，按本设计执行。

## Test Strategy

- 纯逻辑/UI（offscreen Qt，沿用 `tests/test_piano_roll_ui.py` 模式）：
  - 单击空白清空选择且音符数不变；双击空白新增 1 个音符且被选中；拖动框选选中相交音符。
  - 左边缘拖动改变 start、end 不变；拖过结尾停在最小时长。
  - 方向键：量化 1/8 下步长正确；↑ 半音、Shift+↑ 八度；无选中无变化。
  - Ctrl+滚轮缩放、Shift+滚轮不缩放。
  - 演奏模式（read_only）下点击/拖动/键盘不改数据；播放辅助线可被标尺定位。
- 手动：模式按钮文案与黄框显隐、按钮高度是否与下拉框一致、页脚文字。
- 回归：现有 99 项测试全部通过（其中 Shift+滚轮测试需改为 Ctrl）。

## Migration Plan

无数据迁移；快捷键变更需在变更说明中提示用户。

## Open Questions

无。
