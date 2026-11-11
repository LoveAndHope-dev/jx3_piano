# 验收记录：piano-roll-tempo-control

## 环境

- Windows + Python 3.14 + PyQt5 + mido
- 测试命令：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 最近一次结果：`Ran 78 tests ... OK`（上一轮 51 项 + 本轮 27 项）

## 独立审查后的修复

最终集成审查（review_mode: standard）覆盖 `4f33e1c..e1796d7`，结论「With fixes」，无 Critical。已修复项：

1. **Important：播放中 BPM 框没有真正禁用。** 新增 `_sync_bpm_enabled()`，在加载、开始播放、停止、播放结束四处同步「有曲目且未播放」状态。
2. **Important：越界输入被静默改成另一个合法值（500 → 50）。** 数值框输入范围放宽到 0～10000，提交时显式钳制到 20～300 并回写显示；15 BPM 的源曲目也能如实显示。
3. **Minor：改 BPM 后剪贴板仍用旧速度。** `rescale_times` 现在同步缩放 `_clipboard`。
4. **Minor：tempo 换算重复实现。** `tempo_us_from_bpm` 移到 `build_music`，`piano_roll` 直接导入并复用，删除内联副本。
5. **Minor：测试缺口。** 新增 `grid_seconds_for_bpm` 单测、剪贴板缩放测试、导出时「无 tempo 事件插入」「多 tempo 事件统一改写」「长曲 tick 一致」测试，并让未处理音轨测试同时断言 tempo 值被改写。
6. **Minor：`scaled_note_times` 注释写成「深拷贝」。** 已改为「浅拷贝（音符为扁平字典）」。

未处理（Minor，记录为已知限制）：导出时 `duration_seconds = max(duration, 0.02)` 的既有下限在极高速（如 300 BPM 且原音符 <0.05 秒）时可能把音符尾延长到 20 ms，属于改动前就存在的保护逻辑。

## 自动化覆盖

| 规格场景 | 覆盖测试 |
| --- | --- |
| 缩放因子 120→60 / 60→120 / 同值 / 非法 | `test_tempo.BpmFactorTest`（4 例） |
| tempo 微秒换算（120 / 90 / 非法） | `test_tempo.TempoUsTest`（3 例） |
| 音符时间缩放、可逆（1e-6）、不改输入 | `test_tempo.ScaledNoteTimesTest`（4 例） |
| 画布按比例缩放音符与播放辅助线 | `test_piano_roll_ui.test_rescale_times_scales_notes_and_playhead` |
| 缩放发出 notesChanged（驱动「● 未保存」） | `test_piano_roll_ui.test_rescale_times_emits_notes_changed` |
| 连续缩放可逆 | `test_piano_roll_ui.test_rescale_times_round_trip` |
| 小节线与标尺按新拍长对齐 | `test_piano_roll_ui.test_measure_lines_follow_new_tempo` |
| 导出写入新 tempo | `test_midi_tempo_export.test_writes_new_tempo` |
| 导出后音符 tick 不变 | `test_midi_tempo_export.test_note_ticks_are_preserved` |
| 未处理音轨事件保持 | `test_midi_tempo_export.test_unprocessed_track_events_are_preserved` |
| 不传 BPM 时沿用源 tempo | `test_midi_tempo_export.test_without_tempo_bpm_keeps_source_tempo` |

## 实现中的取舍

- `build_music.write_notes_to_midi` 内联计算 tempo 微秒，而不是导入 `piano_roll.tempo_us_from_bpm`：`piano_roll` 已经导入 `build_music`，反向导入会形成循环依赖。两处算法一致，`test_tempo` 与 `test_midi_tempo_export` 分别覆盖。

## 仍需人工确认（视觉 / 音频）

- 导入 120 BPM 曲目后 BPM 框显示 120.0；切换 140 BPM 曲目后显示 140.0，且不触发缩放或「未保存」。
- 把 BPM 改为 60：音符变宽、播放明显变慢、小节线每 4 秒一条且与标尺序号对齐。
- 量化 1/4 下改 BPM 后拖动音符，仍吸附到正确节拍点。
- 播放中 BPM 框禁用、修改无效；停止后恢复可编辑。
- 连续改 120→90→150 后确认音符位置与最初一致（无可见漂移）。
- 改 BPM 后另存 MIDI，再导入该文件时 BPM 框显示新速度，音符位置一致。

## 结论

三份需求维度（显示、编辑与联动、导出）的核心逻辑均有自动化覆盖；上述 6 项交互/听感检查需在真实窗口中过一遍后确认交付。
