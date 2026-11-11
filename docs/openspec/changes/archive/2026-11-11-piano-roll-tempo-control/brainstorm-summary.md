# 设计探索摘要（Design）

change: `piano-roll-tempo-control`

## 一、已确认内容（用户，不再重问）

| 事项 | 决定 |
| --- | --- |
| 工作区 | `current`：沿用 `main` 与当前目录，既有 25 个无关改动保留不动 |
| 改 BPM 的语义 | 音符拍位不变、秒数按 `旧BPM / 新BPM` 重算，播放速度与标尺同步变化 |
| BPM 控件 | 工具栏「量化」旁的数值框，范围 20.0～300.0，步进 1，一位小数 |
| 另存 MIDI | 写入当前 BPM（tempo 事件），音符拍位保持不变 |

## 二、现状事实（已核实源码）

- `extract_notes` 已按源 MIDI tempo 把音符存成「秒」（`start` / `duration`）。
- `gui.current_bpm` 目前只用于 `set_measure_grid` 与 `_apply_quantize_grid`（`gui.py:952-1006`）。
- 播放数据由 `regenerate_playback_from_notes` 从音符秒数生成，播放线程不读 BPM。
- 顶部标尺与背景小节线共用 `seconds_per_beat = 60 / BPM`（`set_beat_grid` / `set_measure_grid`）。
- `write_notes_to_midi` 用 `mid.ticks_per_beat` 与 `_scan_base_tempo` 把秒数换算成 tick，tempo 事件沿用源文件（`build_music.py:833-914`）。

## 三、候选技术方案（待确认）

1. **缩放秒数实现速度变更**：`factor = 旧/新`；`_PianoRollCanvas.rescale_times(factor)` 缩放全部音符 `start`/`duration` 与播放辅助线锚点/显示位置，重排图元、扩展场景并 `notesChanged`。
2. **工具栏 `QDoubleSpinBox`**：20.0～300.0、1 位小数、步进 1、`keyboardTracking(False)`；`_updating_bpm` 保护位避免回填触发重算；播放中与无曲目禁用。
3. **固定更新顺序**：算 factor → `rescale_times` → `set_measure_grid` → `set_beat_grid` → `_apply_quantize_grid` → 更新 `current_bpm` → 标记未保存。
4. **播放链路不改**：秒数变了播放自然变快/变慢；辅助线按同一 factor 缩放，粘贴锚点仍对齐同一拍位。
5. **导出写回 tempo**：`write_notes_to_midi(..., tempo_bpm=None)`，提供时统一改写全部 `set_tempo`（缺失则插入），并用新 tempo 做秒→tick 换算，使 tick 拍位不变。

## 四、备选与被丢弃方案

| 备选 | 丢弃理由 |
| --- | --- |
| 为每个音符新增 `beat` 字段、渲染时换算 | 需改写所有编辑/播放/导出路径与数据格式，成本高 |
| 只改网格不改音符 | 播放速度不变，不满足需求 |
| 只缩放播放延迟 | 铺面与播放进度会错位，风险最高 |
| 改音符 tick 而不改 tempo（导出） | 导出文件仍按原速播放，与铺面速度不一致 |
| 保留多段 tempo 渐变 | 与「单一 BPM」模型冲突；本次声明为已知限制 |

## 五、风险与验证策略

- **多段 tempo 源文件**：按基础 tempo 统一处理，导出统一 tempo；在 proposal/design 中声明限制。
- **浮点漂移**：连续缩放用乘法因子，验收允许 1e-6 秒误差。
- **大曲目性能**：一次遍历全部音符，与缩放重排同量级。
- **误触**：`keyboardTracking(False)` + 播放中禁用；改动标记未保存。
- **测试**：纯函数（factor/tempo_us/缩放）、画布层 `rescale_times`、mido 构造 MIDI 的导出断言、上一轮 51 项回归。

## 六、Spec Patch

无。已有 `specs/piano-roll-tempo-control/spec.md` 覆盖全部已确认行为。

## 七、未决问题

无。
