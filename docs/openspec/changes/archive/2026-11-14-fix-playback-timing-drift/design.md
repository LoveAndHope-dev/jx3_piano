# Design

## 修复点

`player._execute_playback_data()` 由相对延时改为绝对时间轴调度：

```python
start_time = time.time()
scheduled_offset = 0.0
for item in playback_data:
    if isinstance(item, (int, float)):
        scheduled_offset += float(item)
        target = start_time + scheduled_offset
        while True:
            remaining = target - clock()
            if remaining <= 0:
                break
            time.sleep(min(0.01, remaining))
            emit_progress_if_due()
    elif isinstance(item, str):
        press_keys(item)
    emit_progress_if_due()
```

- 每段延时的目标时刻 = 开始时间 + 累计延时，不再「按完键再睡 delay」。
- DD 按键耗时与 sleep 抖动被后续等待吸收；若某组确实超时，下一次仍对齐绝对时刻，不会逐段放大。
- 进度回调仍使用 `clock() - start_time`（真实耗时），辅助线与声音同源。
- 便于测试，把 `clock` 与 `press_keys` 抽成实例方法/可替换函数，`JX3Player` 默认使用 `time.time` 与 `self.dd.key_press`。

## 影响

- 只改 `player.py` 的播放执行循环与测试；`play_from_data`、`split_playback_at`、GUI 不变。
- 停止检查仍以 10ms 步长进行，ESC 响应速度不变。

## 验证

- 用假时钟与假按键器构造「按键耗时 20ms + 延时 100ms」的序列，断言第 N 组按键时刻等于累计延时（不随组数增长）。
- 现有 173 项测试回归。
