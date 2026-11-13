# playback-session Specification

## Purpose
保证播放结束后程序继续运行，并安全回收播放线程。

## Requirements

### Requirement: 播放完成不销毁运行中的线程

播放线程在 `run()` 内发出完成信号后才会返回。GUI 的完成回调 MUST 只更新播放状态与界面，MUST NOT 在该回调中清空或销毁线程对象；线程引用 SHALL 在线程真正结束后（`QThread.finished`）清理，并用延迟销毁释放。

#### Scenario: 正常播放到结尾

- **WHEN** 曲目播放完成、播放线程发出完成信号
- **THEN** 界面恢复为「▶️ 弹奏」，程序保持运行，不出现闪退

#### Scenario: 手动停止

- **WHEN** 播放中点击停止或按 ESC
- **THEN** 等待线程退出后再释放引用，行为与之前一致
