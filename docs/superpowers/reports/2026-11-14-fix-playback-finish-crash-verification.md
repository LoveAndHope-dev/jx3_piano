# 验收记录：fix-playback-finish-crash

## 环境

- Windows + Python 3.14 + PyQt5
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 188 tests ... OK`

## 缺陷与根因

现象：曲目播放到结尾后程序直接退出，无异常提示。

根因：`gui.on_play_finished()` 在完成回调里 `self.play_thread = None`。`PlayThread.run()` 发出完成信号后才返回，信号跨线程排队投递，主线程可能在 `run()` 返回前执行回调；此时销毁运行中的 `QThread` 会触发 Qt 致命错误并终止进程。

## 修复

- `start_playing` 额外连接 `QThread.finished` → `_cleanup_play_thread`。
- `on_play_finished` 只更新播放状态与界面，不再清空线程引用。
- `_cleanup_play_thread`：清空引用并 `deleteLater()`；重复调用安全。
- `stop_playing`：`wait(3000)` 超时仍保留引用，交给 finished 清理。

## 覆盖

| 场景 | 测试 |
| --- | --- |
| 完成回调保留线程引用 | `test_play_finished_keeps_thread_reference` |
| 清理槽释放引用 | `test_cleanup_play_thread_releases_reference` |
| 无线程时清理安全 | `test_cleanup_play_thread_is_safe_without_thread` |
| 播放模式锁定/停止（既有） | `test_stop_playback_keeps_play_mode_locked` |

## 独立审查后的修复

- **Critical**：清理槽原先读取「当前」线程引用，旧线程的 `finished` 可能释放新线程。现改为通过 `sender()`（或显式参数）绑定发出信号的线程，只有仍是当前线程时才清空引用。
- **Critical**：开始播放前检查旧线程是否仍在运行；运行中则提示「上一次播放仍在收尾」并拒绝开始，避免覆盖引用。
- **Important**：完成/进度回调增加线程身份校验，过期信号不再重置当前播放；`closeEvent` 改为按线程是否存在停止，而不是按 `is_playing`。
- **测试**：新增「清理不误删新线程」「过期完成信号不影响当前播放」「旧线程运行中拒绝开始」；复验 `Ran 188 tests ... OK`。

## 手动确认

- 播放整首到结尾：界面恢复「▶️ 弹奏」，程序保持运行。
- 播放中停止 / ESC / 关闭窗口：行为不变。

## 结论

播放结束不再销毁运行中的线程；清理与重启/关闭均按线程身份与状态保护。188 项测试通过，release exe 已重新打包。
