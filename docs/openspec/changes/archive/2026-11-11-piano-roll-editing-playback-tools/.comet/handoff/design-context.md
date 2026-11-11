# Comet Design Handoff

- Change: piano-roll-editing-playback-tools
- Phase: design
- Mode: compact
- Context hash: e63a1d81277d3af1b6f43d9cf2b0b52c6f2bd89a7e774e6b51aebd76ea80dfb1

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/piano-roll-editing-playback-tools/proposal.md

- Source: docs/openspec/changes/piano-roll-editing-playback-tools/proposal.md
- Lines: 1-33
- SHA256: a17b2ceeecbb54fe63ebd4b76209c354041021dade734903150efdf817dd49bd

```md
# 铺面编辑的剪贴板、八度移动与时间轴/播放控制

## Why

当前铺面编辑器只能逐个新增、拖动、删除音符，缺少复制/剪切/粘贴这类批量编辑手段；时间轴只能按固定像素密度查看、没有拍数刻度，也无法在曲中定位播放起点，导致编辑长曲和反复试听某一段都很低效。本次补齐这些基础编辑与播放控制能力，并把容易误解的「播放」按钮改名为「弹奏」。

## What Changes

- 铺面编辑新增剪贴板操作：复制、剪切选定的音符，并在播放辅助线位置粘贴；粘贴保留音符之间的相对时距与音高。
- 选中音符后按 Shift+↑ / Shift+↓，整体上移 / 下移一个八度；会超出 A0～C8 的音符跳过，其余照常移动。
- 钢琴窗顶部新增固定拍数标尺：显示小节/拍序号，点击或拖动可定位播放辅助线；播放辅助线常驻，默认位于 0 秒。
- 播放时播放辅助线随进度同步移动；点「弹奏」从当前播放辅助线位置开始播放，而不是固定从曲首开始。
- 按住 Shift 滚动滚轮，对钢琴窗时间轴做横向放大 / 缩小；音符、网格、音域框与标尺同步缩放。
- 工具栏「▶️ 播放」按钮文案改为「▶️ 弹奏」；播放中 / 播放结束后的「停止(ESC)」与恢复文案保持原状。

## Capabilities

### New Capabilities

- `piano-roll-note-editing`：铺面音符的剪贴板操作（复制 / 剪切 / 在播放辅助线处粘贴）与八度整体移动。
- `piano-roll-timeline`：钢琴窗时间轴的拍数标尺、可定位且常驻的播放辅助线、播放中的辅助线同步，以及 Shift+滚轮横向缩放。
- `piano-roll-playback-control`：播放起点由播放辅助线决定，以及播放按钮的用户可见文案。

### Modified Capabilities

- 无。项目当前没有任何已归档的持久化 capability 规格（`docs/openspec/specs/` 为空），本次全部按新增能力处理。

## Impact

- `piano_roll.py`：音符选择与编辑、剪贴板、键盘事件、时间轴坐标换算（模块级 `PIXELS_PER_SECOND` 常量改为实例级可变缩放）、顶部标尺控件、播放辅助线状态。
- `gui.py`：播放辅助线联动、按播放头位置生成播放数据、播放按钮文案。
- 播放链路：从播放头开始时，在 GUI 侧按时间过滤并平移音符后复用 `MidiToKeysConverter.regenerate_playback_from_notes`，`player.py` 的按键执行逻辑不变。
- 不影响既有音频按键映射、音域框筛选、MIDI 另存为逻辑；不新增第三方依赖。

```

## docs/openspec/changes/piano-roll-editing-playback-tools/design.md

- Source: docs/openspec/changes/piano-roll-editing-playback-tools/design.md
- Lines: 1-118
- SHA256: 448a32d935c1265ec6f6f72e1d944bc067ba6a7a3c0399e3ca70ba8eb17b4d31

[TRUNCATED]

```md
# Design

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

```

Full source: docs/openspec/changes/piano-roll-editing-playback-tools/design.md

## docs/openspec/changes/piano-roll-editing-playback-tools/tasks.md

- Source: docs/openspec/changes/piano-roll-editing-playback-tools/tasks.md
- Lines: 1-43
- SHA256: 2aea88c6093262d5ca9db4e8f590548d6b720849c48d0f029e54e5df0d983a70

```md
# Tasks

## 1. 可测试的纯逻辑

- [ ] 1.1 在 `piano_roll.py` 中抽出音符剪贴板所需的纯函数：以剪贴板最早起始时间为基准、按播放辅助线计算粘贴后的 `start` 列表，并保证输入不被修改；新增 `tests/test_note_clipboard.py` 覆盖多音符相对时距、单音符、起始时间为 0 的情况，运行 `.venv\Scripts\python.exe -m unittest tests.test_note_clipboard -v` 通过 <!-- comet-task:5795b48f-f846-4064-b3ab-249ec7003b8e -->
- [ ] 1.2 抽出八度移动的纯函数：输入音符列表、选中 id 集合与方向，返回新的音高映射，越界音符保持原音高；在 `tests/test_note_clipboard.py` 中补充升/降八度、部分越界、全部越界的断言并运行通过 <!-- comet-task:7e371289-6682-4fa4-92bc-8a4b423a1b75 -->
- [ ] 1.3 抽出播放起点过滤的纯函数：按 `playhead` 排除更早开始的音符，并把保留下来的 `start` 平移为相对时间（`1e-6` 容差）；新增 `tests/test_playback_start.py` 覆盖跨辅助线音符、恰好落在辅助线、过滤后为空、时间平移四种情况并运行通过 <!-- comet-task:a4f189ce-7475-491a-aed6-89793b964b69 -->
- [ ] 1.4 抽出横向缩放的纯函数：比例夹紧到 10～600、按锚点时间计算缩放后的滚动偏移；新增 `tests/test_zoom_math.py` 覆盖上下限、放大后锚点时间不变、缩小后锚点时间不变并运行通过 <!-- comet-task:81b1efb9-0e8a-437a-86e3-9d2a2d185881 -->

## 2. 画布剪贴板与八度移动

- [ ] 2.1 在 `_PianoRollCanvas` 中保存内部剪贴板，接入 Ctrl+C 复制选中音符；验证：加载曲目后选中多个音符按 Ctrl+C，再删除其中一个原音符并多次粘贴，粘贴出的仍是复制时刻的内容（手动验收） <!-- comet-task:6e3710d1-7234-425b-9e2a-a05c0892e75c -->
- [ ] 2.2 接入 Ctrl+X 剪切与 Ctrl+V 在播放辅助线处粘贴：新音符获得唯一 id、成为当前选中集合、铺面显示未保存标记、场景宽度按需扩展；验证：依 `piano-roll-note-editing` 的三个粘贴场景手动验收 <!-- comet-task:48602a6e-f25e-4c5e-92f1-5daa8336255f -->
- [ ] 2.3 接入 Shift+↑ / Shift+↓ 八度移动：越界音符跳过、其余音符音高变化且起始时间与时长不变、`mapped` 重新计算、发出 `notesChanged`；验证：按 `piano-roll-note-editing` 的八度场景手动验收，并确认第 1.2 组测试仍通过 <!-- comet-task:6b51f8a7-8093-46f9-be5b-2b7df08e7385 -->
- [ ] 2.4 更新 `piano_roll.py` 顶部模块说明，补入剪贴板与八度移动，并确认说明与实现一致 <!-- comet-task:e5a372a1-c0d1-43d8-85a3-2f75efa67f1e -->

## 3. 时间轴横向缩放

- [ ] 3.1 把模块级 `PIXELS_PER_SECOND` 改为画布实例缩放值，统一更新坐标换算、音符矩形、背景网格、音域框、拖动与时长调整中的像素/秒计算；验证：以默认比例运行现有测试，并在 GUI 中拖动音符与调整时长、开启量化后行为与改动前一致（手动验收） <!-- comet-task:25419ee0-14a1-48cf-994d-1b83f8808001 -->
- [ ] 3.2 实现 Shift+滚轮缩放：向上放大、向下缩小，以鼠标指针时间点为锚，比例夹紧到 10～600，未按 Shift 时保持原纵向滚动；验证：按 `piano-roll-timeline` 的缩放场景手动验收 <!-- comet-task:6438bc9c-6776-467e-af59-d4d31929a544 -->
- [ ] 3.3 缩放后重排背景、全部音符、音域框与播放辅助线，并刷新顶部标尺；验证：缩放后确认音符、网格、音域框、辅助线、标尺仍然对齐，拖动与量化仍按正确秒数工作（手动验收） <!-- comet-task:f583e0c4-0184-4964-8046-fe64a2fb8ef5 -->

## 4. 顶部拍数标尺与播放辅助线

- [ ] 4.1 新增固定高度的顶部标尺控件并接入 `PianoRollWidget` 布局，按每小节秒数与拍长绘制小节序号和拍刻度，缺少节拍信息时退化为秒标注；验证：加载 4/4、120 BPM 曲目时每 2 秒显示一个小节序号并与小节线对齐（手动验收） <!-- comet-task:f5d05313-6b44-433f-9e1f-861ddc36dd44 -->
- [ ] 4.2 让标尺随画布横向滚动与缩放同步、纵向滚动不移动；验证：水平滚动、横向缩放和改变窗口宽度后标尺与铺面始终对齐（手动验收） <!-- comet-task:6698d655-5b9e-45ad-87d7-3da758136a7c -->
- [ ] 4.3 实现播放辅助线的锚点/显示分离：锚点默认 0、点击或拖动标尺更新锚点、`set_playhead(None)` 回落到锚点而不再隐藏；验证：按 `piano-roll-timeline` 的常驻与定位场景手动验收 <!-- comet-task:551d3ef7-3fa3-4020-8ff0-b25d45b1490e -->
- [ ] 4.4 在 `gui._load_piano_roll` 中把拍长与每小节拍数传给铺面，并在切换曲目时重置辅助线到 0；验证：切换到 BPM 或拍号不同的曲目后标尺重新标注、辅助线回到 0（手动验收） <!-- comet-task:af5ae4f2-254c-4886-9a23-7edb09a54b1e -->
- [ ] 4.5 播放期间由进度驱动辅助线移动并禁用标尺定位；验证：播放中点击标尺不改变播放位置、辅助线随进度持续右移（手动验收） <!-- comet-task:30bc7557-f434-43aa-aeb2-431c923da0ba -->

## 5. 播放起点与按钮文案

- [ ] 5.1 修改 `gui.start_playing`：按播放辅助线过滤并平移音符后再生成播放数据，进度回调叠加起点时间，过滤后为空时提示"当前位置之后没有可播放的音符"；验证：按 `piano-roll-playback-control` 的起点场景手动试听，并确认第 1.3 组测试通过 <!-- comet-task:03e77383-c763-4ea0-aa0d-4f00fb1301df -->
- [ ] 5.2 把空闲状态的播放按钮文案改为「▶️ 弹奏」（初始化、停止、播放结束三处），播放中保持「⏹️ 停止(ESC)」，`objectName` 不变；验证：启动程序看到「弹奏」，播放中变为「停止(ESC)」，停止后恢复「弹奏」（手动验收） <!-- comet-task:1507d0cc-75a0-418a-ba5d-b68f7c0a4038 -->

## 6. 集成验证

- [ ] 6.1 运行 `.venv\Scripts\python.exe -m unittest discover -s tests -v`，确认全部测试通过且既有 C6 边界测试无回归 <!-- comet-task:6ecb67e7-30f2-4c49-be31-7345031ee40a -->
- [ ] 6.2 按验收清单手动走查：多选复制/剪切/粘贴、Shift+↑/↓、Shift+滚轮缩放、标尺定位与播放同步、从辅助线开始播放、按钮文案，全部符合 `specs/` 中的场景 <!-- comet-task:07da8a52-7345-4914-8186-5a395f587ea2 -->

## Workflow follow-up

- 完成 Verify 后按 Comet 交付流程归档或交付，具体方式由用户确认。

```

## docs/openspec/changes/piano-roll-editing-playback-tools/.openspec.yaml

- Source: docs/openspec/changes/piano-roll-editing-playback-tools/.openspec.yaml
- Lines: 1-2
- SHA256: b8f20def63a86ae4075c5499ff9ed413265d8704692a8493712424dc3f28d8e3

```md
schema: spec-driven
created: 2026-11-11

```

## docs/openspec/changes/piano-roll-editing-playback-tools/specs/piano-roll-note-editing/spec.md

- Source: docs/openspec/changes/piano-roll-editing-playback-tools/specs/piano-roll-note-editing/spec.md
- Lines: 1-73
- SHA256: 5208e47db65ca664515ca536f07837bef516cfca0560b87bfb63a08fa6da3381

```md
# Spec Delta

## Purpose

为铺面编辑器提供基于剪贴板的音符复制、剪切与粘贴，以及按八度整体移动选中音符的编辑能力，使用户不必逐个重建重复片段。

## ADDED Requirements

### Requirement: 复制选中音符

在铺面编辑器获得键盘焦点且存在选中音符时，按 Ctrl+C SHALL 把当前全部选中音符的副本写入内部剪贴板，并保留这些音符之间的相对起始时间差与音高关系；剪贴板内容 MUST 是写入时刻的快照，之后继续编辑或删除原音符不得改变剪贴板内容。

#### Scenario: 复制多个音符

- **WHEN** 选中 3 个起始时间与音高各不相同的音符，按 Ctrl+C，然后拖动并删除其中一个原音符
- **THEN** 剪贴板中仍保存复制时刻的 3 个音符副本，相对时距与音高保持复制时的状态

#### Scenario: 无选中音符时复制

- **WHEN** 铺面编辑器中没有选中任何音符，按 Ctrl+C
- **THEN** 剪贴板内容保持不变，铺面不发生变化

### Requirement: 剪切选中音符

存在选中音符时，按 Ctrl+X SHALL 先按复制规则写入剪贴板，再从铺面删除这些选中音符，并把铺面标记为有未保存修改。

#### Scenario: 剪切后原音符消失

- **WHEN** 选中 2 个音符并按 Ctrl+X
- **THEN** 这两个音符从铺面移除，选中集合清空，剪贴板保存它们的副本，铺面显示未保存标记

#### Scenario: 无选中音符时剪切

- **WHEN** 没有选中任何音符，按 Ctrl+X
- **THEN** 剪贴板与铺面均保持不变

### Requirement: 在播放辅助线处粘贴

剪贴板非空时，按 Ctrl+V SHALL 在播放辅助线当前所在时间处粘贴剪贴板中的全部音符：剪贴板中最早音符的起始时间对齐到播放辅助线时间，其余音符保持与它的相对时距，音高与时长保持不变；粘贴产生的新音符 MUST 成为当前选中集合，且原有音符不被修改。

#### Scenario: 在播放辅助线处粘贴

- **WHEN** 剪贴板中有起始时间为 1s 和 3s 的两个音符，播放辅助线位于 10s，按 Ctrl+V
- **THEN** 铺面新增起始时间为 10s 和 12s 的两个音符，音高与时长与剪贴板一致，且只有这两个新音符被选中

#### Scenario: 连续粘贴

- **WHEN** 先在第 5s 处粘贴一次，把播放辅助线移到第 15s 后再粘贴一次
- **THEN** 两次粘贴各产生一组独立音符，分别位于 5s 与 15s 起，互不影响

#### Scenario: 空剪贴板粘贴

- **WHEN** 剪贴板为空时按 Ctrl+V
- **THEN** 铺面不新增任何音符，也不改变当前选中集合

### Requirement: 选中音符的八度移动

存在选中音符时，按 Shift+↑ SHALL 把每个选中音符的音高升高 12 个半音，按 Shift+↓ SHALL 降低 12 个半音；移动后音高会超出 A0（MIDI 21）～C8（MIDI 108）范围的那些音符 MUST 保持原音高不动，其余选中音符照常移动；移动不得改变音符的起始时间与时长。

#### Scenario: 整体升高一个八度

- **WHEN** 选中 3 个合法范围内的音符并按 Shift+↑
- **THEN** 3 个音符的音高都增加 12，起始时间与时长不变，铺面显示未保存标记

#### Scenario: 越界音符保持不动

- **WHEN** 选中两个音符，其中一个升高 12 个半音后会超过 C8，按 Shift+↑
- **THEN** 未越界的音符升高 12 个半音，会越界的音符保持原音高，其余属性不变

#### Scenario: 无选中音符时移动八度

- **WHEN** 没有选中任何音符时按 Shift+↑ 或 Shift+↓
- **THEN** 铺面不发生任何变化

```

## docs/openspec/changes/piano-roll-editing-playback-tools/specs/piano-roll-playback-control/spec.md

- Source: docs/openspec/changes/piano-roll-editing-playback-tools/specs/piano-roll-playback-control/spec.md
- Lines: 1-40
- SHA256: 24f71ddc5ac4f6612b0212e5d8ccbf4f6c5a20a848024884d00fb70021bc8b36

```md
# Spec Delta

## Purpose

让铺面播放从用户选定的播放辅助线位置开始，并把工具栏播放按钮的用户可见文案统一为「弹奏」。

## ADDED Requirements

### Requirement: 从播放辅助线位置开始播放

用户点击「弹奏」时，系统 SHALL 以播放辅助线当前时间作为本次播放的起点：只有起始时间不早于该位置的音符参与本次播放，起始时间早于该位置的音符不重新触发；参与播放的音符按相对于该位置的时间间隔依次演奏，因此位置之后最近的音符在开始演奏时立即发声。

#### Scenario: 从曲中位置开始

- **WHEN** 播放辅助线位于第 10 秒，第 10 秒之后存在音符，点击「弹奏」
- **THEN** 播放从第 10 秒开始，只演奏起始时间不早于第 10 秒的音符，辅助线从第 10 秒起随进度移动

#### Scenario: 跨过辅助线的音符不重触发

- **WHEN** 一个音符从第 8 秒持续到第 12 秒，播放辅助线位于第 10 秒，点击「弹奏」
- **THEN** 该音符不被重新触发，播放从第 10 秒之后的音符开始

#### Scenario: 辅助线之后没有音符

- **WHEN** 播放辅助线位于最后一个音符结束之后，点击「弹奏」
- **THEN** 系统提示当前位置之后没有可播放的音符，并且不开始播放

### Requirement: 弹奏按钮文案

工具栏播放按钮在空闲状态 SHALL 显示「▶️ 弹奏」；播放进行中显示「⏹️ 停止(ESC)」；停止播放或播放结束后 MUST 恢复为「▶️ 弹奏」。

#### Scenario: 空闲状态显示弹奏

- **WHEN** 程序启动或一次播放结束、停止后
- **THEN** 工具栏按钮显示「▶️ 弹奏」

#### Scenario: 播放中显示停止

- **WHEN** 用户点击「弹奏」并成功开始播放
- **THEN** 按钮显示「⏹️ 停止(ESC)」，点击后停止播放并恢复「▶️ 弹奏」

```

## docs/openspec/changes/piano-roll-editing-playback-tools/specs/piano-roll-timeline/spec.md

- Source: docs/openspec/changes/piano-roll-editing-playback-tools/specs/piano-roll-timeline/spec.md
- Lines: 1-101
- SHA256: 9e0f0816eb9b19bbb77771ae21b7f9854bffa15cccddc886dc3a0c8a643750ce

[TRUNCATED]

```md
# Spec Delta

## Purpose

为钢琴窗提供带拍数刻度的顶部时间标尺、可定位且常驻的播放辅助线，以及按住 Shift 滚动滚轮控制的横向时间轴缩放，使用户能在长曲中快速定位与查看细节。

## ADDED Requirements

### Requirement: 顶部拍数标尺

钢琴窗顶部 SHALL 显示一条固定的时间标尺，按当前曲目的每小节秒数标出从 1 开始的小节序号，并与铺面时间轴使用同一套横向坐标；标尺 MUST 随铺面横向滚动和横向缩放同步对齐，且不随铺面纵向滚动而移动。

#### Scenario: 标尺与小节对齐

- **WHEN** 加载一首 4/4 拍、BPM 为 120 的曲目
- **THEN** 标尺在每 2 秒处显示一个小节序号，序号位置与铺面背景中对应的小节线水平对齐

#### Scenario: 横向滚动时标尺跟随

- **WHEN** 水平滚动铺面或改变横向缩放比例
- **THEN** 标尺上的小节序号与铺面中的小节线始终对齐，不出现横向错位

#### Scenario: 切换曲目后重新标注

- **WHEN** 从一首曲目切换到 BPM 或拍号不同的另一首曲目
- **THEN** 标尺按新曲目的每小节秒数重新计算并显示小节序号

### Requirement: 用标尺定位播放辅助线

在未播放时，用户 SHALL 能通过点击或按住拖动顶部标尺来设置播放辅助线的时间位置；标尺上的横向位置按与铺面相同的时间映射换算为秒数，结果不得小于 0。

#### Scenario: 点击标尺定位

- **WHEN** 未播放时点击标尺上与铺面第 8 秒对齐的位置
- **THEN** 播放辅助线移动到第 8 秒，并在铺面上显示对应位置的竖线

#### Scenario: 拖动标尺连续定位

- **WHEN** 在标尺上按住鼠标左键并左右拖动
- **THEN** 播放辅助线随拖动连续移动，松开后停留在最后位置

### Requirement: 播放辅助线常驻

铺面 SHALL 始终显示一条播放辅助线；加载曲目后其默认位置为 0 秒。播放结束后辅助线 MUST 回到用户最后一次设置的位置，而不是被隐藏。

#### Scenario: 默认位置

- **WHEN** 首次加载一首曲目
- **THEN** 播放辅助线显示在时间轴 0 秒处

#### Scenario: 停止播放后恢复定位

- **WHEN** 播放辅助线被设置在 6 秒，开始播放并在 12 秒处停止
- **THEN** 播放辅助线回到 6 秒处，保持可见

### Requirement: 播放时辅助线同步移动

播放进行中，播放辅助线 SHALL 按播放进度从起始位置持续向右移动；此时标尺的定位交互 MUST 被禁用，不得因用户点击或拖动标尺而改变当前播放位置或中断播放。

#### Scenario: 播放中辅助线移动

- **WHEN** 从第 4 秒开始播放
- **THEN** 播放辅助线从第 4 秒起随时间推移持续右移，与实际播放进度一致

#### Scenario: 播放中点击标尺

- **WHEN** 播放进行中点击标尺的其他位置
- **THEN** 播放继续进行，播放辅助线保持由播放进度驱动，不跳转到被点击的位置

### Requirement: Shift+滚轮横向缩放

在铺面区域按住 Shift 滚动滚轮 SHALL 横向放大或缩小时间轴：向上滚动放大（每秒占用更多像素），向下滚动缩小；缩放 MUST 以鼠标指针所在的时间点为锚点，使该时间点在缩放前后保持在同一横向屏幕位置，并受最小与最大缩放比例限制。

#### Scenario: 向上滚动放大

- **WHEN** 按住 Shift 把滚轮向上滚动一格
- **THEN** 时间轴放大，鼠标指针下的时间点在屏幕上保持不动，可见时间范围变短

#### Scenario: 向下滚动缩小


```

Full source: docs/openspec/changes/piano-roll-editing-playback-tools/specs/piano-roll-timeline/spec.md
