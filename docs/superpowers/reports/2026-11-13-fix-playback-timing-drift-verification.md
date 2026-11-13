# 验收记录：fix-playback-timing-drift

## 环境

- Windows + Python 3.14 + PyQt5
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 182 tests ... OK`

## 缺陷与根因

现象：播放时 DD 按键相对辅助线越播越滞后（从头与中段起播都会出现）。

根因：`player._execute_playback_data` 使用相对延时——按完一组键后再 `sleep(下一段延时)`。`DD_key` 按下/释放的调用耗时与 10ms 步长 sleep 的固定超时逐段叠加，而辅助线按 `time.time()` 推进。

## 修复

- 改为绝对时间轴：累计延时得到每组按键的应触发时刻 `start_time + scheduled_offset`，等待到该时刻再按键。
- 按键耗时与 sleep 抖动由后续等待吸收，不再逐段累积。
- 进度回调仍按真实耗时上报，辅助线与声音同源。
- 时钟与 sleep 可注入，便于用虚拟时钟断言调度时刻。

## 覆盖

| 场景 | 测试 |
| --- | --- |
| 按键耗时 20ms、延时 100ms 时不累积 | `test_key_press_cost_does_not_accumulate` |
| 100 组后仍对齐绝对时刻 | `test_many_groups_keep_absolute_schedule` |
| 进度按真实耗时单调上报 | `test_progress_uses_wall_clock` |
| 停止信号立即中断 | `test_stop_signal_interrupts_playback` |
| 空数据返回 False | `test_empty_data_returns_false` |

以上用例在旧的相对延时实现下会失败（每段多加 20ms）。

## 独立审查后的修复

- **Important 1**：调度改用单调时钟 `time.monotonic`，避免系统时间回拨导致停播或前跳；倒计时也改用可注入的 sleep。
- **Important 2**：记录每组按键相对计划时刻的最大延迟，超过 30ms 时在完成日志中提示，便于判断「持续跟不上」。
- **Minor**：补充 sleep 步长 ≤10ms、等待期间停止、sleep 超时被吸收、延迟告警等测试；spec 措辞补充「按键组耗时不超过后续延时」的前提。
- 复验结果：`Ran 182 tests ... OK`；release exe 已重新打包。

## 手动确认

- 从头播放长曲：按键与辅助线全程保持一致，不再越播越偏。
- 从曲中起播：起点对齐，后续不漂移。
- ESC 停止、进度日志与完成统计行为不变。

## 结论

累积漂移根因消除；182 项测试通过，release exe 已重新打包。
