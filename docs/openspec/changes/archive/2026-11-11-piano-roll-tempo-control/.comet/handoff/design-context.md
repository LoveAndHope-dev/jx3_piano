# Comet Design Handoff

- Change: piano-roll-tempo-control
- Phase: design
- Mode: compact
- Context hash: 4de45177c53e6ea74decef5e129db2a3020447ec77f4196c3e5fb0fe5b3214ec

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/piano-roll-tempo-control/proposal.md

- Source: docs/openspec/changes/piano-roll-tempo-control/proposal.md
- Lines: 1-31
- SHA256: 76b12ffd36366f07bf392d4f4416ff751eaf63b129724d23052bfcf8054e3853

```md
# 铺面速度（BPM）显示、编辑与联动

## Why

导入曲目后，界面只按源 MIDI 的固定速度绘制网格，用户看不到当前 BPM，也无法在工具内试听或调整速度；想改变快慢只能回源文件改、再重新导入。BPM 目前只参与小节线与量化网格，「改速度」既不影响播放，也不影响标尺。本次让 BPM 成为铺面里可见、可改的一等参数，并让它统一驱动播放速度、量化网格与标尺刻度。

## What Changes

- 导入曲目时读取源 MIDI 的基础 BPM，填入工具栏新增的「BPM」数值框（保留一位小数）。
- 数值框可编辑：范围 20.0～300.0，步进 1，一位小数；播放中或无曲目时禁用。
- 修改 BPM 采用「音符拍位不变」语义：所有音符的起始时间与时长、播放辅助线位置按 `旧BPM / 新BPM` 比例重算；顶部标尺刻度、背景小节线与量化网格按新 BPM 重新计算；铺面标记为未保存。
- 播放速度随之改变：播放数据仍由音符秒数生成，因此 BPM 变大时同一乐句播放更快。
- 另存为 MIDI 时写入当前 BPM 的 tempo 事件，音符在文件中的拍位（tick）保持与改 BPM 前一致。

## Capabilities

### New Capabilities

- `piano-roll-tempo-control`：铺面编辑器的 BPM 展示、编辑，以及 BPM 变更对音符时间、播放、标尺/小节线与 MIDI 导出的联动。

### Modified Capabilities

- 无。上一轮引入的 `piano-roll-timeline` 只规定标尺按「当前曲目 BPM」对齐，BPM 可编辑后的行为由本次新能力补充，不修改其既有要求。

## Impact

- `gui.py`：工具栏 BPM 数值框、导入时回填、变更处理（重算网格、量化、未保存状态）、播放中禁用、另存 MIDI 传入当前 BPM。
- `piano_roll.py`：新增按比例缩放音符时间与播放辅助线的能力；复用现有背景/标尺重排。
- `build_music.py`：`write_notes_to_midi` 增加可选 `tempo_bpm`，写回 tempo 事件并按新速度换算 tick。
- 不影响音符音高、按键映射、音域框筛选与播放线程；不新增第三方依赖。
- 已知限制：源 MIDI 含多段 tempo 时，本工具按基础 tempo 统一处理，导出时 tempo 也会统一为当前 BPM。

```

## docs/openspec/changes/piano-roll-tempo-control/design.md

- Source: docs/openspec/changes/piano-roll-tempo-control/design.md
- Lines: 1-88
- SHA256: e232341ce64f28ba48999de1e9fb96a0bc8baa5da3a647dcba1b6e5771328d7a

[TRUNCATED]

```md
# Design

行为需求以 `specs/piano-roll-tempo-control/spec.md` 为准；本文说明实现方式与取舍。

## Context

- 音符进入铺面时已由 `extract_notes` 按源 MIDI tempo 折算成「秒」保存（`start` / `duration`）。
- `gui.current_bpm` 目前只用于 `set_measure_grid` 与 `_apply_quantize_grid`。
- 播放数据由 `regenerate_playback_from_notes` 从音符秒数生成，因此只要音符秒数变化，播放速度自然变化，无需改播放线程。
- 顶部标尺与背景小节线共用 `seconds_per_beat = 60 / BPM`。
- 另存 MIDI 由 `MidiToKeysConverter.write_notes_to_midi` 用 `mid.ticks_per_beat` 与源文件基础 tempo 把秒数换算成 tick，tempo 事件沿用源文件。

## Goals / Non-Goals

**Goals:**

- BPM 成为铺面里唯一的速度真源：改一次，音符时间、播放、量化、标尺、小节线、导出全部一致。
- 采用「拍位不变」语义，连续修改可逆，不累积漂移。
- 导出 MIDI 写回当前 BPM，且音符 tick 不变。

**Non-Goals:**

- 不支持多段 tempo 渐变编辑；源文件多段 tempo 时按基础 tempo 统一处理（导出时也统一）。
- 不做速度自动化曲线、不做拍号编辑。
- 不改变音符音高、按键映射、音域框筛选与播放线程。

## Decisions

### 1. 以「缩放秒数」实现速度变更

- 设旧 BPM 为 B0、新 BPM 为 B1，缩放因子 `factor = B0 / B1`。
- `piano_roll` 新增 `rescale_times(factor)`：遍历音符把 `start` 与 `duration` 乘以 `factor`；播放辅助线锚点与显示位置同样相乘（钳制 ≥0）；更新图元几何、场景宽度并发出 `notesChanged`。
- `duration` 不设最小钳制：按比例缩放保持拍长关系；编辑时才有 `MIN_NOTE_DURATION` 限制。
- 未采用「保存拍位、渲染时换算」：那需要给每个音符新增 beat 字段并改写所有编辑/导出路径，成本更高且会改变数据格式。

### 2. GUI 状态与控件

- 工具栏「量化」旁新增 `QDoubleSpinBox`：范围 20.0～300.0，`decimals=1`，`singleStep=1`，`keyboardTracking(False)`（回车或失焦时才提交，避免逐字符拖动整首曲子）。
- `_updating_bpm` 保护位：导入曲目回填时置位，避免程序化赋值触发重算。
- 变更处理顺序：先算 `factor` → `piano_roll.rescale_times(factor)` → `set_measure_grid(60/B1*bpb)` → `set_beat_grid(60/B1, bpb)` → `_apply_quantize_grid()` → `current_bpm = B1` → 标记未保存。顺序固定，避免网格用旧值绘制。
- 播放中通过 `set_read_only(True)` 与 `setEnabled(False)` 双重禁用；`_set_range_controls_enabled` 统一管理无曲目/播放中状态。

### 3. 播放与辅助线

- 播放链路不改：`start_playing` 仍读取音符秒数；BPM 变更只改秒数本身。
- 播放辅助线按同一 `factor` 缩放，保证改速度后粘贴锚点与播放起点仍在同一拍位。
- 播放中禁止修改，因此不会出现播放数据与辅助线使用不同速度的状态。

### 4. 标尺、小节线与量化

- 三者都由 `seconds_per_beat` 派生；BPM 变更时统一用新值重算并触发重绘。
- 标尺已监听画布 `zoomChanged`、滚动与 resize；`set_beat_grid` 自身会 `update()`，无需新增信号。

### 5. MIDI 导出写入新 BPM

- `write_notes_to_midi(source, notes, processed_tracks, output_path, tempo_bpm=None)`：
  - 传入 `tempo_bpm` 时，先把文件中所有 `set_tempo` 事件的 tempo 改为 `round(60_000_000 / bpm)`；若文件没有任何 tempo 事件，在 0 号音轨开头插入一个。
  - 秒数换算 tick 时使用新 tempo（`mido.second2tick(seconds, tpb, new_tempo)`），因此 `tick = seconds * new_tempo/1e6 * tpb = beats * tpb`，拍位不变。
  - 未处理的音轨事件与 tick 数据保持原样；它们在新 tempo 下听起来会同步变快/变慢，这是修改全局速度的预期结果。
- 未采用「改音符 tick 而不改 tempo」：那样导出文件仍以原速播放，与铺面速度不一致。

### 6. 浮点与容差

- 连续修改使用乘法因子，理论上可逆；验证时允许 `1e-6` 秒级误差。
- BPM 与因子计算统一保留双精度，写 MIDI 时只对 tempo 取整（微秒/拍），不写回 `current_bpm`。

## Risks / Trade-offs

- **多段 tempo 源文件**：按基础 tempo 统一缩放会把渐变速度拉平。→ 在 proposal 与本文件声明为已知限制；导出时统一 tempo，避免文件内速度冲突。
- **长时间连续调 BPM 的浮点漂移**：乘法误差极小；以 1e-6 容差验收，若出现可见漂移再改为「以原始拍位为基准重算」。
- **大曲目重排性能**：`rescale_times` 会遍历全部音符并更新图元；与缩放重排同一量级，可接受。
- **误触修改**：`keyboardTracking(False)` + 播放中禁用，降低误改概率；改动会标记未保存，不会静默覆盖 MIDI。
- **tempo 事件位置**：可能存在多个 tempo 事件，统一改写为同一值；不保留原渐变。

## Test Strategy

- **纯逻辑（unittest）**：`bpm_scale_factor(old, new)`、`tempo_us_from_bpm(bpm)`、`scaled_note_times(notes, factor)` 的边界与可逆性；`piano_roll` 层用 `rescale_times` 断言音符与辅助线缩放。
- **MIDI 导出（unittest）**：用 `mido` 在临时目录造一个 120 BPM、含两个音轨的 MIDI，调用 `write_notes_to_midi(..., tempo_bpm=90)`，读回断言：tempo 为 90、处理音轨音符 tick 与源一致、未处理音轨字节等价。
- **UI / 交互（手动）**：导入 120 BPM 曲目显示 120.0；改为 60 后音符变宽、播放变慢、小节线每 4 秒；播放中控件禁用；连续改回 120 后恢复原样。
- **回归**：上一轮 51 项测试全部通过；播放起点过滤、标尺对齐、缩放锚点不受影响。

```

Full source: docs/openspec/changes/piano-roll-tempo-control/design.md

## docs/openspec/changes/piano-roll-tempo-control/tasks.md

- Source: docs/openspec/changes/piano-roll-tempo-control/tasks.md
- Lines: 1-36
- SHA256: ced2ae2b941865ccaa8dce2dbd359d87c3a69dc22fd53eb232338f29ffb526ac

```md
# Tasks

## 1. 纯逻辑与测试

- [ ] 1.1 在 `piano_roll.py` 新增 `bpm_scale_factor(old_bpm: float, new_bpm: float) -> float` 与 `tempo_us_from_bpm(bpm: float) -> int`，非法 BPM（<=0）抛 `ValueError`；新增 `tests/test_tempo.py` 覆盖 120→60、60→120、同值、非法输入，运行通过 <!-- comet-task:2696a302-cadb-4871-b3b8-70d50e82978f -->
- [ ] 1.2 新增 `scaled_note_times(notes: List[Dict], factor: float) -> List[Dict]`：返回深拷贝且 `start`/`duration` 乘 factor，不改输入；补充升速、降速、连续缩放可逆（1e-6）的断言并运行通过 <!-- comet-task:69ff741b-153d-4819-ad13-aeb75eedf877 -->

## 2. 画布时间缩放

- [ ] 2.1 在 `_PianoRollCanvas` 新增 `rescale_times(factor: float) -> None`：缩放全部音符 `start`/`duration` 与播放辅助线锚点/显示位置（钳制 >=0），重排图元、扩展场景宽度并发出 `notesChanged`；`PianoRollWidget` 透传；用 `tests/test_piano_roll_ui.py` 断言音符与锚点按比例变化 <!-- comet-task:19d6d18f-9c09-4c8e-809a-f48bcc44094c -->
- [ ] 2.2 验证连续缩放可逆：UI 测试中 1.0→0.75→1.25→1.0 后音符时间与初始一致（1e-6 容差） <!-- comet-task:45bf94ad-b7cb-4be1-99fe-c50cb2a8fe2d -->

## 3. 工具栏 BPM 控件

- [ ] 3.1 在 `gui.py` 工具栏「量化」旁新增「BPM」`QDoubleSpinBox`（20.0～300.0、1 位小数、步进 1、`keyboardTracking(False)`）；无曲目与播放中禁用，随 `_set_range_controls_enabled` 一起切换 <!-- comet-task:a9142c56-4d43-48ca-8137-8a5b2185fdee -->
- [ ] 3.2 `_load_piano_roll` 中用 `converter.get_tempo_and_time_signature` 的 BPM 回填数值框，并用 `_updating_bpm` 保护位避免触发重算；切换曲目时必须覆盖旧值 <!-- comet-task:b158f98c-f99e-4745-94ac-2ee7f3c6f1a0 -->
- [ ] 3.3 连接 `valueChanged`：按 `factor = 旧/新` 调 `piano_roll.rescale_times`，再用新 BPM 重算 `set_measure_grid`、`set_beat_grid` 与量化网格，最后更新 `current_bpm` 并标记未保存；播放中直接返回 <!-- comet-task:fb81e917-d556-44c9-8aa2-7108b9193713 -->

## 4. 标尺与网格联动验证

- [ ] 4.1 验证 BPM 变更后顶部标尺小节序号、背景小节线、量化吸附三者使用同一 `60/BPM` 拍长（手动：4/4 曲目 120→60 时小节线每 4 秒一条、标尺序号对齐） <!-- comet-task:161103a5-afc0-4053-934b-6a038c836017 -->
- [ ] 4.2 验证量化档位 1/4 下改 BPM 后拖动音符仍吸附到正确节拍点（手动） <!-- comet-task:b8c61abf-783b-4f56-84ba-432045e5d7f3 -->

## 5. MIDI 导出写入 BPM

- [ ] 5.1 `build_music.write_notes_to_midi` 增加可选 `tempo_bpm: Optional[float] = None`：提供时把所有 `set_tempo` 事件改写为 `tempo_us_from_bpm`，缺失则在 0 号音轨插入；秒数→tick 使用新 tempo；新增 `tests/test_midi_tempo_export.py` 用 mido 构造 120 BPM 两音轨文件，导出 90 BPM 后断言 tempo=90、处理音轨 tick 不变、未处理音轨等价 <!-- comet-task:19590cb1-6e7b-46d6-abee-9adb87b1fda8 -->
- [ ] 5.2 `gui.save_piano_roll` 传入 `self.current_bpm`；验证改 BPM 后另存的文件读回速度为当前 BPM（手动或用第 5.1 组测试覆盖的同一入口） <!-- comet-task:bc2fee92-a541-4a55-b53b-8264336bbd5e -->

## 6. 集成验证

- [ ] 6.1 运行 `.venv\Scripts\python.exe -m unittest discover -s tests -v`，确认上一轮 51 项与本轮新增测试全部通过 <!-- comet-task:18093b5c-1e59-4b3c-aa5b-2048d7de33f8 -->
- [ ] 6.2 手动走查：导入显示 BPM、修改后播放变快/变慢、标尺与小节线对齐、连续改回原值、播放中禁用、另存 MIDI 速度为当前 BPM <!-- comet-task:d3bed8ba-4811-448e-88f2-ae5b2aff946b -->

## Workflow follow-up

- 完成 Verify 后按 Comet 交付流程归档或交付，具体方式由用户确认。

```

## docs/openspec/changes/piano-roll-tempo-control/.openspec.yaml

- Source: docs/openspec/changes/piano-roll-tempo-control/.openspec.yaml
- Lines: 1-2
- SHA256: b8f20def63a86ae4075c5499ff9ed413265d8704692a8493712424dc3f28d8e3

```md
schema: spec-driven
created: 2026-11-11

```

## docs/openspec/changes/piano-roll-tempo-control/specs/piano-roll-tempo-control/spec.md

- Source: docs/openspec/changes/piano-roll-tempo-control/specs/piano-roll-tempo-control/spec.md
- Lines: 1-106
- SHA256: d5686733f01e6062319ce7d6fa471d6415575ad01d7e2aef429a07e092898e0a

[TRUNCATED]

```md
# Spec Delta

## Purpose

让铺面编辑器的 BPM 可见、可编辑，并让 BPM 变更统一驱动音符时间、播放速度、量化网格、顶部标尺与背景小节线，同时保证另存 MIDI 时写回新的速度。

## ADDED Requirements

### Requirement: 导入曲目时显示 BPM

加载曲目成功后，工具栏 SHALL 在「BPM」数值框中显示该曲目的基础 BPM，保留一位小数；切换曲目时 MUST 用新曲目的 BPM 覆盖旧值，不得沿用上一首的编辑值。曲目未加载、解析失败或播放进行中时，BPM 数值框 MUST 处于禁用状态。

#### Scenario: 显示源曲目速度

- **WHEN** 导入一首基础速度为 120 BPM 的曲目
- **THEN** BPM 数值框显示 120.0 且可编辑

#### Scenario: 切换曲目后更新

- **WHEN** 当前曲目 BPM 被改为 90.0 后，切换到另一首 140 BPM 的曲目
- **THEN** BPM 数值框显示 140.0，不保留 90.0

#### Scenario: 无曲目时禁用

- **WHEN** 尚未选择任何曲目
- **THEN** BPM 数值框为禁用状态，无法输入

### Requirement: 编辑 BPM

BPM 数值框 SHALL 接受 20.0～300.0 之间的数值，步进 1，保留一位小数；超出范围的输入 MUST 被钳制到最近边界值，无法解析的输入 MUST 回退到最近一次有效值。播放进行中 MUST 禁止修改 BPM。

#### Scenario: 修改为合法值

- **WHEN** 曲目加载完成后把 BPM 从 120.0 改为 150.0
- **THEN** 数值框显示 150.0，铺面含义按新速度更新

#### Scenario: 越界输入被钳制

- **WHEN** 在 BPM 数值框中输入 500
- **THEN** 数值框停在 300.0，铺面按 300.0 更新

#### Scenario: 播放中禁止修改

- **WHEN** 正在播放时尝试修改 BPM 数值框
- **THEN** 数值框不可编辑，播放与铺面都不发生变化

### Requirement: BPM 变更按拍位保持不变重算时间

设修改前 BPM 为 B0、修改后为 B1，则每个音符的起始时间与时长 SHALL 乘以 `B0 / B1`；播放辅助线的锚点与当前显示位置 MUST 同样按该比例换算且不小于 0。音高、音轨、力度等其余属性 MUST 保持不变，铺面 MUST 标记为有未保存修改。

#### Scenario: 放慢速度

- **WHEN** 曲目 BPM 为 120，起始时间 1.000 秒、时长 0.500 秒的音符在 BPM 改为 60 后
- **THEN** 该音符起始时间变为 2.000 秒、时长变为 1.000 秒，音高不变

#### Scenario: 加快速度

- **WHEN** 曲目 BPM 为 60，起始时间 2.000 秒的音符在 BPM 改为 120 后
- **THEN** 该音符起始时间变为 1.000 秒，其余属性不变

#### Scenario: 连续修改可逆

- **WHEN** 依次把 BPM 从 120 改为 90，再改为 150，最后改回 120
- **THEN** 每个音符的起始时间与时长回到最初值（允许 1e-6 秒级浮点误差）

### Requirement: 标尺、小节线与量化网格随 BPM 更新

BPM 变更后，顶部标尺的小节序号与拍刻度、背景小节线、量化网格 SHALL 按新 BPM 重新计算（一拍秒数 = `60 / BPM`），并与铺面时间轴保持同一横向坐标；三者 MUST 在同一帧内一致更新，不得出现只更新其中一部分的状态。

#### Scenario: 小节线间距变化

- **WHEN** 4/4 拍、120 BPM（每小节 2 秒）的曲目把 BPM 改为 60
- **THEN** 背景小节线间距变为每 4 秒一条，顶部标尺的小节序号与之一一对齐

#### Scenario: 量化网格跟随

- **WHEN** 量化档位为 1/4，BPM 从 120 改为 90 后拖动音符
- **THEN** 吸附网格使用 60/90 秒一拍对应的间距，音符落在正确的节拍点上

### Requirement: 播放速度跟随 BPM

```

Full source: docs/openspec/changes/piano-roll-tempo-control/specs/piano-roll-tempo-control/spec.md
