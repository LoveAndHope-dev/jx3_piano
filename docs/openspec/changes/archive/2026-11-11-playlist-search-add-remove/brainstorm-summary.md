# 设计探索摘要（Design）

change: `playlist-search-add-remove`

## 已确认（用户）

- 删除：列表隐藏 + 清缓存，磁盘 MIDI 保留；有确认步骤。
- 「添加」= 新建一个空 MIDI 并加入列表（不是导入现成文件）。
- 工作区：`current`，沿用 `main`。

## 现状事实

- `refresh_play_list` 直接枚举 `midi/` 目录，没有搜索/排序/删除。
- 「📁 导入MIDI」已存在，导入后自动刷新列表。
- 铺面/播放状态集中在 `current_midi_path`、`piano_roll`、`play_thread`、`current_bpm` 等字段。

## 候选方案

1. 新增 `playlist_store.py` 数据层：隐藏记录读写、目录枚举、过滤、排序、唯一命名、空 MIDI 生成，全部纯函数可单测。
2. 隐藏记录 `midi/.hidden_playlist.json`（文件名数组），损坏时按空集合处理并保留原文件；右键「恢复所有已移除曲目」清空。
3. `refresh_play_list` 统一管线：读隐藏 → 过滤 → 搜索 → 排序 → 重建 → 按路径恢复选中。
4. UI：列表上方「搜索框 + 排序下拉」，列表右侧竖排「删除」；按钮行「导入MIDI / 新建 / 刷新」。
5. 删除当前曲目时调用 `_clear_piano_roll_cache()`：停播、清笔记/辅助线、重置 BPM 与路径、清未保存标记、切占位页。
6. 新建空 MIDI 用 mido 写 `set_tempo` + `time_signature` + 空音轨，命名 `新建曲目.mid`、`新建曲目_2.mid`…

## 备选与丢弃

| 备选 | 原因 |
| --- | --- |
| 删除时直接删磁盘文件 | 破坏用户文件，且不可逆 |
| 隐藏记录按绝对路径 | 移动目录后失效 |
| 列表改由独立 playlist.json 维护 | 需迁移现有目录数据，收益不足 |

## 风险

- 隐藏记录同名限制 → 提供恢复入口并声明。
- 删除当前曲目会丢未保存编辑 → 确认框合并提示。
- mtime 同秒 → 名称作第二排序键。

## Spec Patch

无。

## 未决问题

无。
