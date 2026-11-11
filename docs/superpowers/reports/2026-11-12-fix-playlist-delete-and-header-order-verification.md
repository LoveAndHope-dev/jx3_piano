# 验收记录：fix-playlist-delete-and-header-order

## 环境

- Windows + Python 3.14 + PyQt5
- 测试命令：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 最近一次结果：`Ran 128 tests ... OK`（上一轮 129 项，删除与隐藏相关的 3 项按新语义调整/移除后为 128）

## 覆盖

| 能力 | 覆盖测试 |
| --- | --- |
| 列表行只显示一次曲目名 | `test_playlist_gui.test_list_row_shows_name_once`（条目文字为空、行控件含名称） |
| 删除当前曲目会删除 midi/ 副本并清缓存 | `test_playlist_gui.test_delete_current_track_clears_cache`（断言文件不存在） |
| 取消删除不删文件 | `test_playlist_gui.test_cancel_delete_keeps_everything`（断言文件仍存在） |
| 删除后刷新不再出现 | `test_playlist_gui.test_deleted_track_not_listed_after_refresh` |
| 工具栏顺序 | 手动：标题在动作行，主行以「弹奏」「曲谱优化」开头 |

## 人工确认

- 导入后列表没有重影，名称与删除按钮显示正常。
- 删除后到 `midi/` 目录确认副本消失、原始导入文件仍在。
- 工具栏顺序与两行布局符合预期。

## 结论

三处修正均有自动化覆盖或明确的人工验收点；兼容旧数据：`playlist_store` 的隐藏函数保留但不再被主流程使用，旧 `.hidden_playlist.json` 不再影响列表。
