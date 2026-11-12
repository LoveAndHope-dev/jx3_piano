# Tasks

## 1. 工具栏贴左

- [x] 1.1 第一行工具栏去掉中段 stretch，改为行尾 stretch，两行控件全部贴左 <!-- comet-task:47f60a2a-54f0-4e45-82a9-83c3eb18ae70 -->
- [x] 1.2 确认 QComboBox / QSpinBox 不再被中间空白拉伸（窗口变宽后位置不变） <!-- comet-task:0e84764a-986f-4f22-a9d7-7758d559e321 -->
- [x] 1.3 UI 测试：两行首个控件贴左，末尾存在弹性空白 <!-- comet-task:d75bce6b-12f2-478c-bfca-c9502b7bd7f4 -->

## 2. 置顶按钮移位

- [x] 2.1 控制面板改为 QFrame + 标题行（标题 + stretch + 置顶按钮），补齐 QSS <!-- comet-task:d1c7375a-d80d-4eaf-a130-2c02ed1a08d7 -->
- [x] 2.2 从操作日志标题行移除置顶按钮；`toggle_topmost` 保持原行为 <!-- comet-task:914d18d3-bcd2-409c-83f6-90bba6adbfbc -->
- [x] 2.3 UI 测试：置顶按钮在控制面板标题行、日志页不存在；置顶切换仍更新文字 <!-- comet-task:4e0a0d7b-4157-4719-be39-1ed715f50b1b -->

## 3. 原脚本移入（含一处最小修正）

- [x] 3.1 `release/谱子/arpeggiate.py` 内容移入项目根 `arpeggiate.py`，删除原件 <!-- comet-task:fb50a81d-aaa9-4438-8190-508c75db0adc -->
- [x] 3.2 仅修正展开时的时长语义：起点与结束时间同步后移，保留脚本结构、参数与 `main` <!-- comet-task:b82aa085-8fc9-4688-8152-46f52e130cd4 -->

## 4. 脚本执行与新接线

- [x] 4.1 新增 `arpeggiate_runner.py`：tpb=384 的临时 MIDI 往返、每音符独立音轨、重定向 stdout、清理临时目录 <!-- comet-task:d71c4007-074f-4982-bc5b-56ba3e4e1ef3 -->
- [x] 4.2 `piano_roll.arpeggiate_selected` 改用 runner，保持场景扩展与 `notesChanged` <!-- comet-task:3c3815cf-c8a0-4b9d-a523-5440cace36a8 -->
- [x] 4.3 GUI 以四分音符传入拍长，捕获脚本异常并记录日志 <!-- comet-task:a532832f-753b-4724-b858-92c56e5b3654 -->
- [x] 4.4 测试：和弦展开、时长不变、未选中不变、重复音符移除、异常不改铺面 <!-- comet-task:370c67e2-27db-4a12-958f-0c6aa9770fc5 -->

## 5. 集成验证

- [x] 5.1 `.venv\Scripts\python.exe -m unittest discover -s tests -v` 全部通过 <!-- comet-task:fec3a52f-1e16-4409-b459-71c98af298fc -->
- [x] 5.2 手动：窗口变宽后工具栏仍贴左；置顶按钮位置与行为；选中和弦执行曲谱优化后撤销/前进 <!-- comet-task:8500d5bd-e3a6-4378-9a2d-9eba86390c9b -->
