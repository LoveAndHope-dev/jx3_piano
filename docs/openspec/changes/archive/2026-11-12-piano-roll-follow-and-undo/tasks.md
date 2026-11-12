# Tasks

## 1. 画布信号与播放跟随

- [x] 1.1 画布新增 `undoRequested` / `redoRequested` 信号，Ctrl+Z / Ctrl+Shift+Z 转发（只读时不处理）；`PianoRollWidget` 透传 <!-- comet-task:68285e47-58da-4c9d-a028-a4aadb1e933f -->
- [x] 1.2 画布新增 `follow_playhead()`：辅助线超过视口 80% 时整页滚动到左侧 20%；`set_playhead` 在播放期间调用 <!-- comet-task:7932c213-5ec3-4288-8dbe-c34ca97f6f62 -->
- [x] 1.3 UI 测试：阈值内不滚动、超过阈值滚动、停止后不跟随 <!-- comet-task:2d23051f-f5fc-4875-960c-0c585546ae80 -->

## 2. 历史管理

- [x] 2.1 GUI 新增历史栈（音符/BPM/拍号/辅助线，50 步）与基线快照；`notesChanged` 记录步骤并清空 redo <!-- comet-task:1468bf7e-bed5-42dd-b98e-8a21440e7f22 -->
- [x] 2.2 实现 `undo` / `redo`：应用快照、重建网格与 BPM 框、恢复辅助线、按基线重算未保存标记 <!-- comet-task:cf6265bb-cdd9-4e59-8b1b-8bd1934c15a0 -->
- [x] 2.3 BPM 变更入栈，撤销后 BPM 与标尺/量化同步恢复 <!-- comet-task:7bd2571d-d34b-467a-933a-2a4bd0da58e0 -->

## 3. 快捷键与只读

- [x] 3.1 GUI 连接画布信号；演奏模式/播放中忽略快捷键 <!-- comet-task:d7633237-774a-480a-afe4-8f5981990340 -->
- [x] 3.2 手动验证：Ctrl+Z 撤销删除/移动/粘贴/曲谱优化/BPM，Ctrl+Shift+Z 重做 <!-- comet-task:c9c6be4d-ccb6-40af-ad94-11329987558e -->

## 4. 边界与历史上限

- [x] 4.1 新操作清空前进栈；撤销不记录为新步骤；连续 60 次编辑最多撤销 50 步 <!-- comet-task:df9ea79b-eb70-40e3-9c9d-5285652a2adc -->
- [x] 4.2 UI 测试覆盖上述边界与「撤销到初始状态后未保存标记消失」 <!-- comet-task:ba474501-5bc3-4ac5-86ac-cb2b3f6b3821 -->

## 5. 集成验证

- [x] 5.1 `.venv\Scripts\python.exe -m unittest discover -s tests -v` 全部通过 <!-- comet-task:63bc5023-6a0b-42e9-b101-392b2af1c165 -->
- [x] 5.2 手动：长曲播放观察翻页跟随；编辑多种操作后撤销/重做 <!-- comet-task:4a51c866-31b0-4b93-a418-dd3080310c4e -->
