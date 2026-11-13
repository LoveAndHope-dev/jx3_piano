# 修复播放结束后闪退

## 问题

曲目播放到结尾后，程序直接退出（没有异常提示，属于进程级闪退）。

## 根因

`gui.on_play_finished()` 在播放完成回调里执行 `self.play_thread = None`。

`PlayThread.run()` 是在发出 `finished_signal` **之后**才返回的；信号跨线程排队投递，主线程空闲时可能在 `run()` 返回前就执行回调。此时丢掉最后一个 Python 引用会立刻销毁 `QThread`，Qt 触发 `QThread: Destroyed while thread is still running` 致命错误并终止进程。

## 修复范围

- 播放完成回调只更新界面与播放状态，不再释放线程引用。
- 连接 `QThread.finished`（`run()` 真正返回后发出）到清理槽：清空引用并 `deleteLater()`。
- `stop_playing` 仍先 `wait()` 再释放，保持原行为。
- 新增回归测试：完成回调不得丢失运行中的线程引用；清理槽负责释放。

## 非目标

- 不改变播放数据、按键调度、辅助线或界面布局。
- 不改变停止（ESC）与关闭窗口的流程。
