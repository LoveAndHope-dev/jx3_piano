# Tasks

- [x] 1.1 连接 `QThread.finished` 到清理槽，完成回调不再清空线程引用 <!-- comet-task:183c831d-15ae-4fbb-86b5-fdc8695afdab -->
- [x] 1.2 清理槽清空引用并 `deleteLater()`；停止流程保持先 `wait()` 再释放 <!-- comet-task:2c3c9d65-574a-4dbd-bf7c-014998b6e1f0 -->
- [x] 2.1 回归测试：完成回调保留引用、清理槽释放引用 <!-- comet-task:3b8f83d2-6e04-40f0-b0fb-0c3b45855be7 -->
- [x] 3.1 `.venv\Scripts\python.exe -m unittest discover -s tests -v` 全部通过 <!-- comet-task:a4b7f9bb-7c64-4624-9692-423cabef7101 -->
