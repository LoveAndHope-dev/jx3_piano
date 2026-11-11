# 设计探索摘要（Design）

change: `piano-roll-editing-playback-tools`

## 一、已确认内容（来自用户，不再重问）

| 事项 | 决定 |
| --- | --- |
| 工作区隔离 | `current`：沿用 `main` 和当前目录，不新建分支/worktree |
| 播放起点 | 从播放辅助线位置开始播放；早于该位置的音符不重触发 |
| 顶部「播放辅助线及播放总览条」 | 只做单条固定拍数标尺（小节/拍刻度 + 点击或拖动定位），不做整曲缩略总览 |
| 未定位时的粘贴 | 播放辅助线常驻，默认 0 秒，粘贴永远有目标 |
| 八度移动越界 | 跳过会超出 A0(21)～C8(108) 的音符，其余照常移动，保持音程关系 |
| 能力划分 | 3 个新能力：`piano-roll-note-editing`、`piano-roll-timeline`、`piano-roll-playback-control` |

## 二、现状事实（已核实源码）

- `piano_roll.py`：`PIXELS_PER_SECOND = 70` 为模块级常量，被坐标换算、音符矩形、背景网格、音域框、拖动/量化共同使用。
- 已有 `set_playhead(seconds)` 播放线；`gui.on_play_progress` 已按播放进度驱动它，播放结束时 `set_playhead(None)` 将其隐藏。
- 已有 `set_measure_grid(seconds_per_measure)` 按 BPM/拍号绘制小节线；尚无顶部标尺控件。
- 键盘事件集中在 `_PianoRollCanvas.keyPressEvent`（Ctrl+A、Delete/Backspace），无剪贴板与 Shift+方向键。
- 播放数据是扁平 key/delay 列表，无逐事件时间戳；`player.JX3Player` 不支持 seek。
- 测试使用 `unittest`（现有 6 个用例），无 GUI 测试框架。

## 三、候选技术方案（待用户确认）

1. **横向缩放用实例级 `_pixels_per_second`**（默认 70，夹紧 10～600），统一走 `_time_to_x` / `_x_to_time`；Shift+滚轮以鼠标时间点为锚，调整 `horizontalScrollBar` 使锚点时间停留在同一屏幕位置；缩放后重建背景、重排音符/音域框/播放线并刷新标尺。
2. **顶部标尺为独立 `_TimeRulerWidget`**（约 28px）叠加在同一条横向时间坐标系上，订阅画布横向滚动/缩放/尺寸变化重绘；小节序号从 1 起编号，小节内按拍画短刻度；无节拍信息时退化为按秒标注。点击/拖动发出 `playheadRequested(seconds)`。
3. **播放辅助线拆成锚点与显示位置**：`_playhead_anchor_seconds`（用户定位，默认 0，切曲归零）与 `_playhead_display_seconds`（实际绘制）；`set_playhead(None)` 回落到锚点而非隐藏；`set_read_only(True)` 时标尺忽略鼠标事件。
4. **剪贴板为画布内部深拷贝列表**：Ctrl+C 快照、Ctrl+X 复制后复用 `_delete_selected()`、Ctrl+V 以剪贴板最早 `start` 对齐锚点，新音符分配新 id、重算 `mapped`、成为当前选中集合并 `notesChanged`。
5. **八度移动在键盘事件中逐音符判断**：±12 半音，越界跳过，更新 `mapped` 与图元几何。
6. **播放起点在 GUI 侧过滤**：按 `start >= playhead - 1e-6` 过滤并把 `start` 平移为相对时间，复用 `regenerate_playback_from_notes`；进度回调改为 `playhead + elapsed`；过滤后为空则提示且不播放。不改 `player.py`、不改播放数据格式。
7. **按钮文案** 3 处（初始化/停止/结束）改为「▶️ 弹奏」，播放中「⏹️ 停止(ESC)」与 `objectName` 不变。
8. **标尺数据来源**：新增 `set_beat_grid(seconds_per_beat, beats_per_measure)`，由 `gui._load_piano_roll` 传入。

## 四、备选方案与被丢弃理由

| 备选 | 丢弃理由 |
| --- | --- |
| 用 `QGraphicsView.scale()` 做横向缩放 | 会同时缩放行高与文字，破坏「1 行 = 1 半音」；拖动像素换算变复杂 |
| 保留模块常量 + 视图变换矩阵 | 拖动逻辑按像素/秒直接换算，两套比例混用易产生量化与命中测试偏差 |
| 用 `drawForeground` 在场景内画标尺 | 属于场景坐标，会随纵向滚动上下移动，无法固定在窗口顶部 |
| 用 `QHeaderView` 做标尺 | 本视图不是表格模型，接入成本高于自绘 |
| 系统剪贴板（QClipboard + JSON） | 需求只在本编辑器内，内部列表避免格式版本与跨窗口兼容问题 |
| 在 `player.py` 内 seek | 播放数据无时间戳，必须改数据格式；在音符层过滤更小更安全 |
| 八度越界整体回退或全部钳制 | 用户已选择跳过越界音符以保持音程关系 |

## 五、风险与验证策略

- **缩放全量重排的性能**：数百至数千音符下 QGraphicsRectItem 更新成本可控；若卡顿，后续只重排可见区域。
- **标尺与滚动条对齐**：依赖 `valueChanged` / `rangeChanged` / resize 三个事件；需分别用手动横向滚动、缩放、改窗口宽度验证。
- **浮点边界**：`1e-6` 容差避免恰好落在辅助线上的音符被误排除。
- **无 GUI 自动化测试**：把粘贴偏移、八度越界、播放起点过滤、缩放锚点数学抽成纯函数，用 `unittest` 覆盖；UI 交互手动验收。
- **播放中自动 `ensureVisible`**：属既有行为，保留；播放中禁用标尺定位以避免冲突。

## 六、UI 草图（文本）

```
┌───────────────────────────────────────────────┐
│ 1        2        3        4        5   ← 拍数标尺（可点击/拖动）
│ │   ·   ·  │   ·   ·  │   ·   ·  │            │
├──┬────────────────────────────────────────────┤
│键│ ▮▮▮      ▮▮                                │ ← 音符
│盘│     ▮▮▮▮          ▮▮▮                     │
│  │        ┊ ← 播放辅助线（常驻，默认 0s）      │
└──┴────────────────────────────────────────────┘
```

## 七、Spec Patch

无。已确认的行为都能由现有 3 份 delta spec 覆盖，不需要修改 spec。

## 八、未决问题

无。用户体验层面的取舍已在 Open 阶段确认，剩余均为实现细节。
