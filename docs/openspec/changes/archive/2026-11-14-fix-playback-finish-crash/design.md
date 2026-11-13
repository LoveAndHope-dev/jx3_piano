# Design

## 修复点

- `start_playing()`：除现有 `finished_signal` 外，再连接 `self.play_thread.finished`（Qt 内置信号，`run()` 返回后发出）到新槽 `_cleanup_play_thread`。
- `on_play_finished(success)`：只做状态/界面恢复，删除 `self.play_thread = None`。
- `_cleanup_play_thread()`：

```python
thread = self.play_thread
if thread is None:
    return
self.play_thread = None
thread.deleteLater()
```

- `stop_playing()` 保持 `wait(3000)` 后再清引用；若清理槽稍后触发，引用已为 None，安全跳过。

## 时序

```
worker run() ──finished_signal──▶ GUI: on_play_finished（只改 UI）
        │
        └─ return ──QThread.finished──▶ GUI: _cleanup_play_thread（清引用 + deleteLater）
```

## 验证

- 回归测试：`on_play_finished` 不改变 `play_thread` 引用；`_cleanup_play_thread` 清空引用。
- 现有 182 项测试回归。
