# 验收记录：playlist-search-add-remove

## 环境

- Windows + Python 3.14 + PyQt5 + mido
- 测试命令：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 最近一次结果：`Ran 99 tests ... OK`（既有 78 项 + 本轮 21 项：数据层 14 + GUI 7）

## 独立审查后的修复

最终集成审查（review_mode: standard）覆盖 `da782af..38b1a27`，结论「No（Critical 1）」。已修复项：

1. **Critical：新建的空白 MIDI 无法打开。** 自动选轨要求「>10 个音符」，空文件返回空音轨而报错。`_load_piano_roll` 现在把「解析成功但没有足够音符」视为第一个音轨上的空铺面；新增 7 项 offscreen GUI 测试验证「新建 → 列表选中 → 铺面为空 → BPM 120.0 → 无未保存标记」。
2. **Important：搜索过滤生效时新建的曲目被隐藏、未自动选中。** 新建后先清空搜索框再刷新与选中。
3. **Important：搜索把当前曲目过滤掉后无法播放。** `start_playing` 改为仅要求 `current_midi_path`；列表有选中且指向别的曲目时才拒绝。
4. **Important：导入时间按源文件 mtime 排序。** 导入复制后用 `os.utime(tp, None)` 刷新为导入时刻。
5. **Minor：** 删除多余的 `glob` 导入；刷新不再每次按键写日志；隐藏记录改为「临时文件 + os.replace」原子写；删除按钮固定宽度；清理缓存时补重置拍号与播放起点；补隐藏记录非数组 JSON、空白搜索、非法 BPM 等测试；修正测试文件句柄泄漏。

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

## 仍需人工确认（真实窗口观感）

- 搜索框输入/清空时的列表刷新观感；排序切换后最近导入的曲目确实排在前面。
- 新建后列表选中、铺面为空的视觉效果；连续新建两个文件。
- 删除确认框文案与按钮布局（列表右侧图标按钮宽度）。
- 重启程序后隐藏记录仍生效（自动化已覆盖刷新，不含重启进程）。

## 结论

数据层与 GUI 关键路径（新建加载、搜索清空、删除当前/取消、刷新保持隐藏、恢复）已由 21 项自动化测试覆盖；剩余为真实窗口观感确认。
