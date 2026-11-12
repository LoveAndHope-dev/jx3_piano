# Tasks

## 1. 时间轴对齐

- [x] 1.1 `build_play_code_data` 计算首个可播放音符的绝对起点，并在 `playback_data` 前补齐前导延迟；新增 JSON 字段 `timeline_offset` <!-- comet-task:775665c3-a629-4863-aabb-19809664a2f3 -->
- [x] 1.2 `gui.start_playing` 的辅助线起点改为 `playhead`（去掉首音偏移补偿），保持进度叠加 <!-- comet-task:e5df92b4-615c-4e60-87ab-a3d1eaf896b1 -->
- [x] 1.3 更新 `tests/test_play_assets.py`：首音在 5 秒时数据以 5.0 开头；补充 0 秒起播、首音前起播、末尾后起播用例 <!-- comet-task:efdf0128-b149-4699-a80a-0a40ff295e97 -->

## 2. 自动保存与删除（回归确认）

- [x] 2.1 确认进入演奏模式/导入时保存 `midi/edited` 与 `play_code`；删除曲目时清理两份文件（已有测试，补充删除后 JSON 不存在的断言） <!-- comet-task:bf7a2ff5-7b19-4cd6-a0d4-f5abe47c05d0 -->

## 3. 吞音与效率

- [x] 3.1 保存时统计映射框外音符数并提示；框内音符全部参与生成（±1 半音扩展） <!-- comet-task:0923571a-7355-4190-b09c-b1cf4cbce7ae -->
- [x] 3.2 播放只读 JSON + 一次裁剪，不重复转换（代码核对 + 手动验证） <!-- comet-task:a9bb6928-564e-40db-b91a-a4b484e6e83e -->

## 4. 集成验证

- [x] 4.1 `.venv\Scripts\python.exe -m unittest discover -s tests -v` 全部通过 <!-- comet-task:c3d36c5b-e4d8-4f47-85b8-d689aff0f74a -->
- [x] 4.2 手动：从曲首、曲中、首音前、末尾后分别点击弹奏，确认声音与辅助线同步 <!-- comet-task:ec656190-007d-44a4-8e79-96f0cfb24353 -->
