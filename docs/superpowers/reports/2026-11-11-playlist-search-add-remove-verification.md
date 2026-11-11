# 验收记录：playlist-search-add-remove

## 环境

- Windows + Python 3.14 + PyQt5 + mido
- 测试命令：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 最近一次结果：`Ran 90 tests ... OK`（既有 78 项 + 本轮 12 项）

## 自动化覆盖

| 能力 | 覆盖测试 |
| --- | --- |
| 隐藏记录：缺失返回空集 | `test_playlist_store.HiddenStoreTest.test_missing_file_is_empty` |
| 隐藏记录：保存后读回 | `test_save_and_load` |
| 隐藏记录：损坏 JSON 返回空集且保留原文件 | `test_corrupt_file_returns_empty_and_keeps_content` |
| 隐藏记录：保存自动建目录 | `test_save_creates_directory` |
| 只枚举 `.mid/.midi` | `test_playlist_store.EntriesTest.test_lists_only_midi` |
| 搜索大小写不敏感、空串返回全部 | `test_filter_is_case_insensitive` |
| 名称升序排序 | `test_sort_by_name` |
| 导入时间从新到旧 | `test_sort_by_mtime_desc` |
| 同时间用名称稳定排序 | `test_sort_ties_are_stable` |
| 唯一命名 | `test_playlist_store.BlankMidiTest.test_unique_name` |
| 空 MIDI 的 tempo/拍号/无音符 | `test_create_blank_midi_contents` |
| 连续新建不覆盖 | `test_create_two_blanks_do_not_overwrite` |

## 仍需人工确认（GUI 交互）

- 搜索框输入关键词过滤、清空恢复；切换「名称 / 导入时间」排序，且与搜索叠加。
- 点击「➕ 新建」：新文件出现在列表并被选中，铺面为空、BPM 120.0、无「● 未保存」；连续两次生成两个文件。
- 删除未加载曲目：列表消失、磁盘文件仍在、当前铺面不变。
- 删除当前加载曲目：铺面清空、播放停止、辅助线回到 0、BPM 回 120.0、保存按钮禁用、无未保存标记。
- 取消删除：列表、铺面与文件都不变。
- 重启程序后，被删曲目仍不出现；右键「恢复所有已移除曲目」后重新出现。

## 结论

数据层（隐藏记录、过滤、排序、命名、空 MIDI 生成）已由 12 项单测覆盖；上述 6 项为真实窗口交互，需要在应用里过一遍确认交付。
