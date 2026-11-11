---
comet_change: piano-roll-tempo-control
role: technical-design
canonical_spec: openspec
archived-with: 2026-11-11-piano-roll-tempo-control
status: final
---

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

## Migration Plan

无数据迁移：BPM 只存在于运行时；另存 MIDI 才落盘。回滚即还原对应提交。

## Open Questions

无。
