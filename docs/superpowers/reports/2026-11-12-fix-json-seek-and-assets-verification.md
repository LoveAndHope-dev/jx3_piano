# 验收记录：fix-json-seek-and-assets

## 环境

- Windows + Python 3.14 + PyQt5
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 141 tests ... OK`

## 覆盖

| 能力 | 覆盖 |
| --- | --- |
| play_code 时间轴从 0 开始、首音在 5 秒时前导延迟 5.0 | `test_play_assets.PlayCodeDataTest.test_first_note_keeps_absolute_time_axis` |
| 任意位置裁剪：0 秒、曲中、末尾后 | `test_play_assets.SplitPlaybackTest`（3 例） |
| 自动保存 midi/edited 与 play_code | `test_playlist_gui.test_entering_play_mode_saves_midi_and_play_code` |
| 删除曲目清理两份文件 | `test_playlist_gui.test_delete_removes_saved_assets` |
| 框内音符保留、框外过滤 | `test_play_assets.PlayCodeDataTest`（3 例） |

## 修复说明

- 根因：`regenerate_playback_from_notes` 省略了首音前的静音，而辅助线按绝对时间裁剪；两者时间原点不同导致多跳。
- 修复：生成 JSON 时补前导延迟，时间轴与铺面一致；辅助线起点直接用辅助线位置。
- 吞音：保存时提示框外音符数量；框内音符全部参与生成（±1 半音扩展）。
- 效率：播放只读 JSON + 一次线性裁剪，不再逐次转换。

## 人工确认

- 从曲首、曲中、首音前、末尾后分别点击弹奏，声音与辅助线同步。
- 切模式/导入后 `midi/edited` 与 `play_code` 生成；删除曲目后两份文件消失。
