# Tasks

## 1. 播放列表数据层

- [x] 1.1 新增 `playlist_store.py`：`load_hidden(midi_dir)` / `save_hidden(midi_dir, names)`（`midi/.hidden_playlist.json`，损坏时按空集合处理）；新增 `tests/test_playlist_store.py` 覆盖正常读写、缺失文件、非法 JSON <!-- comet-task:a369caed-d8e2-4a46-b5a8-b3a52d892797 -->
- [x] 1.2 实现 `list_entries(midi_dir)`、`filter_entries(entries, query)`、`sort_entries(entries, mode)`：只收 `.mid/.midi`；过滤大小写不敏感；名称升序、mtime 从新到旧且同秒用名称稳定排序；补充单测并运行通过 <!-- comet-task:db1ecd16-0c14-4619-9adb-431d0b5e5181 -->
- [x] 1.3 实现 `unique_midi_name(midi_dir, base)` 与 `create_blank_midi(path, bpm=120.0, time_signature=(4,4))`：用 mido 写入 tempo、拍号与空音轨；单测读回 tempo=120、4/4、至少 1 个音轨，并验证连续生成不重名 <!-- comet-task:6ef60b6e-0987-4348-b00f-ea0edaa50bb7 -->

## 2. 列表 UI 与搜索排序

- [x] 2.1 播放列表上方新增搜索框与排序下拉框（名称/导入时间），列表改为「列表 + 右侧删除按钮」布局；搜索/排序变化调用 `refresh_play_list()` <!-- comet-task:07cb9b65-28a9-4b07-977f-e119631cb7bd -->
- [x] 2.2 改写 `refresh_play_list()`：读隐藏集合 → 过滤隐藏 → 应用搜索 → 应用排序 → 重建列表并按路径恢复选中；无结果显示占位提示 <!-- comet-task:da4ec2f8-2a18-48a1-a137-f59910facc3a -->
- [x] 2.3 手动验收：输入关键词过滤、清空恢复、切换两种排序、搜索与排序叠加、选中项保持 <!-- comet-task:ad9986ac-7d18-47c8-bb8b-20d9dca3bc38 -->

## 3. 新建空曲目

- [x] 3.1 「📁 导入MIDI」右侧新增「➕ 新建」按钮：调用 `unique_midi_name` + `create_blank_midi`，失败弹错误提示且不改列表 <!-- comet-task:18a313bd-4de5-4f40-8092-c112d72cff38 -->
- [x] 3.2 新建成功后刷新列表、按路径选中并加载；验证铺面为空、BPM 显示 120.0、未保存标记不出现；连续新建生成两个文件 <!-- comet-task:ac049ea1-723a-45b3-ab8a-a2d81948131f -->

## 4. 删除与缓存清理

- [x] 4.1 列表右侧「🗑 删除」按钮：无选中时禁用；点击弹确认框，取消不改状态；确认后写隐藏记录并刷新列表 <!-- comet-task:72bbf868-43c0-4cb8-9c4c-7447d422e46f -->
- [x] 4.2 新增 `_clear_piano_roll_cache()`：停止播放、清空铺面与辅助线、重置 `current_midi_path`/音轨/`current_bpm`/BPM 框、清未保存标记与保存按钮、切回占位页；删除当前曲目时调用 <!-- comet-task:1a76d036-11d3-4afd-856b-7e9ca06b9184 -->
- [x] 4.3 手动验收：删除未加载曲目不影响铺面；删除当前加载曲目后缓存清空；刷新与重启后被删曲目仍隐藏 <!-- comet-task:772b7b76-ecf7-4691-992e-d4cdfeee482a -->

## 5. 恢复入口

- [x] 5.1 列表右键菜单新增「恢复所有已移除曲目」：清空隐藏记录并刷新列表；验证已删除且仍在磁盘的曲目重新出现 <!-- comet-task:0d11f8da-2491-4d1b-a110-b3d2f94f7efd -->

## 6. 集成验证

- [x] 6.1 运行 `.venv\Scripts\python.exe -m unittest discover -s tests -v`，确认既有 78 项与本轮新增测试全部通过 <!-- comet-task:e7e17eec-9c8d-4ad4-8be6-a3dbba46c2d8 -->
- [x] 6.2 手动走查：搜索/排序/新建/删除/取消/恢复/重启保持，并确认播放与铺面编辑无回归 <!-- comet-task:84c26964-deb9-4003-b095-bd87251fb5d8 -->

## Workflow follow-up

- 完成 Verify 后按 Comet 交付流程归档或交付，具体方式由用户确认。
