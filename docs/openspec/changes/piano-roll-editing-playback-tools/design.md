---
comet_change: piano-roll-editing-playback-tools
role: technical-design
canonical_spec: openspec
---

# Design

行为需求以 `specs/piano-roll-note-editing`、`specs/piano-roll-timeline`、`specs/piano-roll-playback-control` 三份 delta spec 为准；本文只说明实现方式与取舍。

## Context

本次改动集中在铺面编辑器（`piano_roll.py`）与主窗口（`gui.py`）。

现有约束：

- `PIXELS_PER_SECOND = 70` 是模块级常量，被坐标换算、音符矩形、背景网格、音域框、拖动与量化共同使用；`ROW_HEIGHT` 与音高行严格 1:1。
- 播放辅助线已有 `set_playhead(seconds)`，播放期间由 `on_play_progress` 驱动；播放结束后 GUI 调用 `set_playhead(None)` 清除。
- 小节线已由 `set_measure_grid(seconds_per_measure)` 按曲目 BPM 与拍号绘制；标尺尚无。
- 键盘交互集中在 `_PianoRollCanvas.keyPressEvent`（Ctrl+A、Delete/Backspace）。
- 播放数据是扁平的按键/延迟列表，没有逐事件时间戳；`player.JX3Player` 的播放逻辑不含起点参数。
- 项目没有持久化 capability 规格，也没有 pytest；测试使用 `unittest`。

## Goals / Non-Goals

**Goals:**

- 在单一画布内完成复制/剪切/粘贴、八度移动、横向缩放与播放辅助线定位，不引入新的窗口或依赖。
- 横向缩放只改变"像素/秒"比例，不改变任何时间、音高数据。
- 播放从播放辅助线开始，且不修改播放数据格式与 `player.py` 的按键执行逻辑。
- 标尺与画布共用同一套时间换算，滚动/缩放后始终对齐。

**Non-Goals:**

- 不实现撤销/重做栈、系统剪贴板互通、跨曲目粘贴。
- 不在播放中拖动辅助线做 seek（播放中定位交互被禁用）。
- 不改变音域框筛选、按键映射、MIDI 另存为语义。
- 不改变 `ROW_HEIGHT` 或纵向滚动行为。

## Decisions

### 1. 横向缩放：模块常量改为画布实例状态

把 `PIXELS_PER_SECOND` 改为 `_PianoRollCanvas._pixels_per_second`（默认 70，范围 10～600），所有坐标换算统一走 `_time_to_x` / `_x_to_time`；拖动和调整时长的像素增量也改用同一实例值。

- 缩放时以鼠标指针下的时间点为锚：记录 `anchor_time = _x_to_time(scene_x)`，换算新比例后调整 `horizontalScrollBar` 的值，使 `anchor_time` 仍落在同一屏幕 x。
- 缩放后重建背景（`_build_background`）、重排全部音符矩形、音域框与播放辅助线，并通知标尺刷新。
- 未采用 `QGraphicsView.scale()`：它会同时缩放行高与文字，破坏"1 行 = 1 个半音"的纵向语义，也会让拖动像素换算变复杂。
- 未采用保留常量 + 视图变换矩阵：拖动逻辑已按像素/秒直接换算，混用两套比例容易产生量化与命中测试偏差。

### 2. 顶部标尺：独立 `_TimeRulerWidget`，与画布共享时间换算

在 `PianoRollWidget` 的纵向布局顶部加入固定高度的标尺控件（约 28px），下方仍是"键盘 + 画布"。

- 标尺只负责绘制与鼠标定位，通过公开方法从画布取当前 `_pixels_per_second`、`_measure_seconds`、拍长与水平滚动值。
- 监听画布的 `horizontalScrollBar().valueChanged/rangeChanged` 与尺寸变化重绘，保证与画布横向对齐；纵向滚动不触发重绘。
- 拍数显示：每小节画一条刻度并标注从 1 开始的小节序号；小节内每隔一拍画一条较短的刻度线。缺少 BPM/拍号时退化为按秒标注。
- 点击/拖动标尺发出 `playheadRequested(float seconds)` 信号，由画布更新播放辅助线锚点。
- 未采用 `drawForeground` 叠加：它属于场景坐标，会随纵向滚动上下移动，无法固定在窗口顶部。
- 未采用 `QHeaderView`：本视图不是表格模型，接入成本高于自绘。

### 3. 播放辅助线：锚点与播放预览分离

画布保存两个状态：

- `_playhead_anchor_seconds`：用户最后定位的位置，默认 0，加载/切换曲目时归零。
- `_playhead_display_seconds`：当前实际绘制位置。

接口：

- `set_playhead_anchor(seconds)`：更新锚点并重绘（标尺点击/拖动使用）。
- `set_playhead(seconds)`：保持既有签名，更新显示位置；播放进度使用。
- `set_playhead(None)`：显示位置回落到锚点（不再隐藏），使现有 GUI 停止/结束调用自动符合"常驻"需求。

播放中禁用标尺定位：`set_read_only(True)` 时标尺忽略鼠标事件。

### 4. 剪贴板：画布内部深拷贝列表

- `self._clipboard: List[Dict]` 保存 `dict(note)` 深拷贝，按当前选中集合写入。
- Ctrl+C：写入剪贴板，不改铺面。
- Ctrl+X：写入剪贴板后复用 `_delete_selected()` 的删除逻辑，并触发 `notesChanged`。
- Ctrl+V：若剪贴板为空直接返回；否则以剪贴板内最早 `start` 为基准，把每个副本的 `start` 平移为 `anchor + (start - min_start)`，分配新的 `id`，按当前 `mapped_pitches` 重算 `mapped`，追加到 `_notes` 并创建图元，最后把选择设为新音符并 `_ensure_scene_width`、发出 `notesChanged`。
- 未采用系统剪贴板（QClipboard + JSON）：需求只在本编辑器内，内部列表避免格式版本与跨窗口粘贴的兼容问题。

### 5. 八度移动：在键盘事件中逐个音符判断

- Shift+↑ / Shift+↓ 在 `keyPressEvent` 中处理，遍历 `_selected_ids`。
- 新音高 = 原音高 ± 12；若超出 `MIN_PITCH..MAX_PITCH` 则跳过该音符，其余照常。
- 更新 `mapped` 与图元几何，发出 `notesChanged`。
- 未采用"整体回退"或"全部钳制"：用户已确认跳过越界音符以保持音程关系。

### 6. 从播放辅助线开始：GUI 侧过滤音符后复用现有转换

- `start_playing()` 读取 `playhead = _playhead_anchor_seconds`。
- 过滤 `notes = [n for n in notes if n["start"] >= playhead - 1e-6]`，并把每个音符的 `start` 减去 `playhead`（不改变 `duration`）。
- 继续调用 `MidiToKeysConverter.regenerate_playback_from_notes(filtered, pitch_range, transpose)`，播放数据格式、音域筛选、移调逻辑完全复用。
- 该转换会省略第一个音之前的静音（第一个音立即发声），因此辅助线显示起点取
  `playhead + first_playable_start(filtered, pitch_range)`，即第一个经过音域筛选、
  真正会发声的音符的相对时间；否则起点落在休止符里时，辅助线会在整段播放中
  落后于实际发声。
- 进度回调改为 `self.piano_roll.set_playhead(_playback_start_seconds + elapsed)`。
- 过滤后无音符时提示"当前位置之后没有可播放的音符"并返回。
- 未改动 `player.py`：播放数据是无时间戳的扁平列表，要在播放器内 seek 必须改数据格式；在音符层过滤更小、更安全。

### 7. 按钮文案

- 空闲文案改为「▶️ 弹奏」，共 3 处（初始化、停止、播放结束）。
- 播放中文案「⏹️ 停止(ESC)」不变；`objectName` 仍为 `playBtn`/`stopBtn`，避免样式失效。

### 8. 标尺数据来源

- 在 `set_measure_grid` 之外新增 `set_beat_grid(seconds_per_beat, beats_per_measure)`，由 `gui._load_piano_roll` 传入。
- 标尺用 `beats_per_measure` 决定每小节内短刻度数量，用 `seconds_per_beat` 决定刻度间距；`measure_seconds` 仍由现有逻辑提供。

## Risks / Trade-offs

- **缩放时全量重排**：每个滚轮刻度都会重建背景并遍历全部音符。→ 铺面音符通常在数百到数千级，QGraphicsRectItem 更新成本可控；若出现卡顿，后续可只重排可见区域。
- **播放中自动横向滚动**：现有 `set_playhead` 调用 `ensureVisible`，可能与用户手动滚动冲突。→ 保留现状（属于既有行为）；播放中定位被禁用，用户不会同时操作标尺。
- **浮点边界**：播放起点用 `1e-6` 容差判断 `start >= playhead`，避免恰好落在辅助线上的音符被误排除。
- **标尺与滚动条对齐**：依赖 `valueChanged` 与 `rangeChanged` 两个信号及 resize 事件；漏接任一信号会出现错位。→ 在实现后用手动滚动/缩放/改变窗口宽度三种方式验证。
- **缩放后量化**：吸附基于秒数而非像素，缩放本身不影响吸附结果；需回归验证拖动与时长调整。
- **无自动化 GUI 测试**：项目只有 `unittest` 且无 UI 测试框架。→ 把可抽离的纯逻辑（剪贴板偏移、八度越界判断、播放过滤与时间平移）做成可测试函数，UI 交互由手动验收覆盖。

## Test Strategy

- **纯逻辑（unittest）**：把粘贴时间计算、八度越界判断、播放起点过滤与时间平移、缩放比例夹紧与锚点滚动偏移抽成模块级纯函数，分别由 `tests/test_note_clipboard.py`、`tests/test_playback_start.py`、`tests/test_zoom_math.py` 覆盖，并保持既有 C6 边界测试通过（`python -m unittest discover -s tests -v`）。
- **交互（手动验收）**：多选复制/剪切/连续粘贴、Shift+↑/↓ 越界跳过、Shift+滚轮缩放后的拖动与量化、标尺点击/拖动定位、播放中辅助线同步且标尺不可定位、从辅助线开始播放、按钮文案。
- **对齐回归**：横向滚动、横向缩放、改变窗口宽度三种情况下，标尺刻度与小节线保持同一屏幕位置。
- **失败路径**：过滤后无音符时提示且不进入播放状态；剪贴板为空时粘贴不改动铺面；越界八度移动不改动任何音符属性。

## Migration Plan

无数据或配置迁移。改动只涉及源码与界面；回滚即还原对应提交。

## Open Questions

无。
