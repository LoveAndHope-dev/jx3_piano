# Design

行为需求以 `specs/simple-mode/spec.md`、`specs/piano-roll-playback-assets/spec.md`、`specs/usage-guide/spec.md` 为准。

## Context

- 播放入口：`app/playback.py::start_playing`，正常模式与简单模式最终都走这里。
- 可演奏范围由 `piano_roll.get_instrument_range()` 决定；生成 play_code 时按 `low-1 .. high+1` 过滤（`regenerate_playback_from_notes`）。
- 简单播放：`app/simple_mode.py::on_simple_play_clicked` 先重读原始 MIDI，再优化、保存并调用 `start_playing`。
- 现有 `_save_current_play_assets` 只记录框外音符日志，不弹窗。

## Decisions

### 1. 共享检测与确认

在 `app/playback.py` 增加：

- `_count_unplayable_notes(notes=None)`：默认读取当前铺面音符，按 `low-1 <= pitch <= high+1` 统计超出数量。
- `_confirm_play_out_of_range(notes=None)`：数量为 0 直接返回 True；否则 `QMessageBox.question` 显示数量，选择继续或取消。
- `start_playing(self, confirm_range=True)`：在曲目校验之后、生成播放资产之前调用确认；取消时写日志并返回。

### 2. 简单模式

- 读取原始 MIDI 音符后、`set_notes` 与曲谱优化之前，调用 `self._confirm_play_out_of_range(notes)`；取消则直接返回，不写盘、不优化。
- 通过确认后调用 `self.start_playing(confirm_range=False)`，避免第二次弹窗。

### 3. 向导

- 保留「数据位置」小节及 `midi/`、`midi/edited/`、`play_code/` 说明。
- 删除简单/正常模式小节中的内部实现描述（重读原始 MIDI、保存 play_code JSON、铺面资产），改为面向用户的说法。
- 新增「朝晖琴、南音三弦等拨奏类乐器的移调建议在 +5 到 -5 之间」。
- 简单模式小节新增「MIDI 中的所有音符需要落在 C2 至 B5 之间」。
- 把「铺面编辑工具栏」与「钢琴窗」两个顶层章节移入正常模式小节。

## Risks

- 正常模式现在每次播放都可能弹窗；仅当确有框外音符时出现。
- 简单模式取消后保持原有铺面，不产生优化/保存副作用。

## Test Strategy

- 正常模式：有框外音符时选择「否」不播放；选择「是」继续。
- 简单模式：有框外音符时取消不调用优化/保存/播放；继续时只弹一次。
- 无框外音符时不弹窗。
- 向导包含移调与 C2–B5 文本；铺面编辑与钢琴窗说明位于正常模式小节；简单/正常模式小节不出现「play_code JSON」「铺面资产」等内部术语；「数据位置」保留。
- 既有 245 项回归。
