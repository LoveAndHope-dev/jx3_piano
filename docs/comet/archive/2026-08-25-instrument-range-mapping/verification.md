---
generated_from_state_version: 13
---

# Verification

## Current result

- Result: **Passed**
- Assurance: **skill-coordinated**
- Goal cycle: 1
- Iteration: 3
- Verifier attempt: 1
- Completed: 2026-08-25T18:03:22.813Z
- Summary: 9/9 项验收通过。此前发现的 A8 缺陷（多音轨 MIDI 中新增音符因硬编码 track=0 而在保存时被静默丢弃）已通过双重修复解决：铺面新增音符现在使用当前曲目实际处理音轨（set_default_track），write_notes_to_midi 额外增加防御性兜底防止任何音符因音轨不匹配而丢失。已用与失败报告完全一致的复现场景重新验证通过。

## Acceptance

| ID | Result | Source | Criterion | Reason |
| --- | --- | --- | --- | --- |
| A1 | passed | brief.md | A1: 选中一首已导入的 MIDI 曲目后，铺面顶部出现「显示/隐藏映射」按钮和两个映射下拉框（默认显示 A / J）；点击按钮后铺面上出现覆盖 MIDI 47～60（共 14 个半音／黑白键）范围、横向贯穿整个时间轴的黄色半透明框体。 | 默认区间 A/J 扩展为 MIDI 47-60（14半音）；切换可见性正确渲染黄色框体。 |
| A2 | passed | brief.md | A2: 将「最低映射」下拉框改为 V、「最高映射」改为 3 后，音域框（若可见）立即更新为覆盖 MIDI 40～77（共 38 个半音／黑白键）的范围。 | 下拉框改为 V/3 后扩展区间为 MIDI 40-77（38半音），与修正后的数值一致。 |
| A3 | passed | brief.md | A3: 音域框可见时，在框体内部（非音符处）按下并上下拖动，可整体平移音域框到合法的键位位置，两个下拉框的值随拖动实时更新；拖动到 Z 以下或 7 以上会被限制在边界。 | 真实 QMouseEvent 拖动整体平移框体并保持键位跨度不变，实时同步两个下拉框；越界拖动在 Z/7 处正确夹紧。 |
| A4 | passed | brief.md | A4: 点击播放（▶️）后，不产生/不写入任何 `play_code/*.json` 文件；实际触发的按键序列只包含音高落在当前音域框扩展范围内的音符，范围外的音符被静默跳过（可通过检查生成的内存按键序列验证，无需真实连接游戏）。 | regenerate_playback_from_notes 按当前音域框范围正确过滤音符；播放前后均未产生/修改 play_code/*.json。 |
| A5 | passed | brief.md | A5: 播放列表来自 `midi/` 目录下已导入的 `.mid`/`.midi` 文件，而不是 `play_code/*.json`；导入一个新 MIDI 文件后列表中出现对应条目，且不会在 `play_code/` 下生成新文件。 | 播放列表读取 midi/*.mid/*.midi；导入流程只校验+复制，不再生成 play_code json。 |
| A6 | passed | brief.md | A6: 选中曲目 A 并调整音域框范围后，切换选中曲目 B 再切回曲目 A，音域框范围重置为默认 A～J（不保留上次调整）。 | 重新选中曲目后音域框范围与可见性均重置为默认 A/J、隐藏。 |
| A7 | passed | brief.md | A7: 在铺面中新增/删除/拖动/调整某个音符后，无需保存即可直接点击播放，触发的按键序列反映编辑后的音符状态（含音域框范围过滤）。 | 播放直接读取铺面当前（含编辑）状态与音域框范围生成内存数据，无需保存。 |
| A8 | passed | brief.md | A8: 编辑音符后点击「保存」，`midi/` 目录下出现一个新的 `.mid` 文件（不同于原始导入文件名，且原始文件内容不变），播放列表自动刷新并选中这个新文件；重新选中它时铺面显示的音符与保存前的编辑结果一致（通过重新解析该新 MIDI 文件验证）。 | 已修复此前失败的场景：track0为纯tempo音轨、track1为旋律（processed_tracks=[1]）时，通过真实鼠标点击新增的音符现在正确落在 track1（set_default_track 生效），保存后的新 MIDI 文件包含该新增音符，原文件不变，重新解析后音符与编辑结果一致。 |
| A9 | passed | brief.md | A9: 铺面存在未保存的编辑时切换选中到另一个曲目，或尝试关闭程序，工具会提示用户确认是否放弃未保存的更改（沿用既有确认机制，只是"保存"目标改为 MIDI 文件）。 | 未保存修改时切换曲目/关闭程序会触发放弃确认对话框，逻辑未受本轮改动影响。 |

## Checks

_No Runtime checks were recorded._

## Blockers

_None._

## Risks and skipped work

- write_notes_to_midi 新增的 track 兜底逻辑（不在 processed_tracks 内的音符归入 processed_tracks[0]）是防御性设计，当前唯一的音符来源（铺面新增音符）已通过 set_default_track 正确赋值，该兜底路径在正常使用中不会被触发；仅在理论上防止未来出现的音符数据带有过期/错误 track 值时静默丢失，不影响当前行为。

## Previous iterations

| Goal cycle | Iteration | Attempt | Outcome | Unresolved | Summary | Completed |
| ---: | ---: | ---: | --- | --- | --- | --- |
| 1 | 1 | 1 | recovery | — | Observed implementation write before piano_roll.py | 2026-08-25T17:42:13.590Z |
| 1 | 2 | 1 | recovery | — | Observed implementation write before piano_roll.py | 2026-08-25T17:57:15.762Z |
| 1 | 3 | 1 | pass | — | 9/9 项验收通过。此前发现的 A8 缺陷（多音轨 MIDI 中新增音符因硬编码 track=0 而在保存时被静默丢弃）已通过双重修复解决：铺面新增音符现在使用当前曲目实际处理音轨（set_default_track），write_notes_to_midi 额外增加防御性兜底防止任何音符因音轨不匹配而丢失。已用与失败报告完全一致的复现场景重新验证通过。 | 2026-08-25T18:03:22.813Z |

## Conclusion

9/9 项验收通过。此前发现的 A8 缺陷（多音轨 MIDI 中新增音符因硬编码 track=0 而在保存时被静默丢弃）已通过双重修复解决：铺面新增音符现在使用当前曲目实际处理音轨（set_default_track），write_notes_to_midi 额外增加防御性兜底防止任何音符因音轨不匹配而丢失。已用与失败报告完全一致的复现场景重新验证通过。
