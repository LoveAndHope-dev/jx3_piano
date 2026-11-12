# Design

## 问题定位

`regenerate_playback_from_notes` 生成的 `playback_data` 会省略第一个按键之前的静音（第一个事件直接位于数据时间 0），但 `start_at` 使用铺面绝对秒数。两者时间原点不同，导致按辅助线裁剪时多跳。

## 决策

1. **补齐前导静音**：`build_play_code_data` 计算第一个可播放音符（映射框范围内、经移调后仍可映射）的绝对起始时间 `lead`，若 `lead > 0` 则在 `playback_data` 前插入 `round(lead, 3)`。JSON 增加 `timeline_offset: 0.0` 字段表明时间轴从 0 开始。
2. **播放起点**：`start_at = playhead`，`split_playback_at` 直接按绝对时间裁剪；辅助线起点改为 `playhead`（不再加首音偏移），进度 `playhead + elapsed`。
3. **防御空数据**：裁剪后为空时提示「当前位置之后没有可播放的按键」。
4. **吞音**：保留 ±1 半音边界扩展；保存时统计框外音符并日志提示。
5. **性能**：JSON 读取 + 一次线性扫描，不在播放路径做映射转换。

## 风险

- 首个可播放音的计算若未考虑边界映射，`lead` 可能略小于真实首音（最多一个边界半音），偏差在毫秒级，可接受。
- 旧的 play_code（无前导静音）在升级后首次播放可能偏移；进入演奏模式会自动重写 JSON，覆盖旧文件。

## Test Strategy

- `test_play_assets`：首音在 5 秒时 `playback_data[0] == 5.0`；`split_playback_at` 在 10 秒、首音前、末尾后三种情况的结果。
- GUI：从辅助线位置播放时 `_playback_start_seconds == playhead`（模拟）。
- 回归：现有 140 项测试。
