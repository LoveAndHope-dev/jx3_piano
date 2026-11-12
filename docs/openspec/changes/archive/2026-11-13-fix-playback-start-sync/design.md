# Design

## 修复点

`play_assets.split_playback_at` 改为线性扫描延时并累计时间；当「已耗时 + 当前延时」越过起播点时：

```python
remaining = elapsed + duration - start_at
return ([round(remaining, 6)] if remaining > 0 else []) + list(rest)
```

- 起播点恰好落在延时结束（remaining == 0）时不插入 0 延时。
- 起播点在 0 或之前仍返回副本。
- 序列耗尽仍返回空列表。
- 按键不累计时间，因此夹在延时之间的按键行为不变。

## 影响

- 只有 `split_playback_at` 与对应测试变化；`player.play_from_data` 调用方式不变。
- 时间轴、JSON 结构、辅助线推进与界面均不变。

## 验证

- 新增/更新 `tests/test_play_assets.py`：延时中间、延时边界、按键间、超尾、零起点。
- 现有 168 项测试回归。
