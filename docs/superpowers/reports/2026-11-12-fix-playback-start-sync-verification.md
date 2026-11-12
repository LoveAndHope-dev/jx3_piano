# 验收记录：fix-playback-start-sync

## 环境

- Windows + Python 3.14 + PyQt5
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 173 tests ... OK`

## 缺陷复现（修复前）

`playback_data = [1.0, 'Q', 1.0, 'W', 2.0, 'E']`（按键位于 1s / 2s / 4s）：

| 起播点 | 修复前 | 修复后 |
|---|---|---|
| 1.5s | `['W', 2.0, 'E']`（提前 0.5s） | `[0.5, 'W', 2.0, 'E']` |
| 2.6s | `['E']`（提前 1.4s） | `[1.4, 'E']` |
| 3.0s | `['E']`（提前 1.0s） | `[1.0, 'E']` |
| 2.0s（延时边界） | `['W', 2.0, 'E']` | `['W', 2.0, 'E']` |

辅助线按「起播点 + 实际耗时」推进；修复后按键序列保留残余延时，两者从同一时刻开始计时。

## 覆盖

| 场景 | 测试 |
| --- | --- |
| 起播点落在延时中间保留剩余延时 | `test_keeps_remaining_delay_inside_a_gap` |
| 起播点正好在延时结束 / 按键时刻 | `test_key_exactly_at_start_is_kept` |
| 跳过起点前按键 | `test_skips_keys_before_start` |
| 超过序列尾部 | `test_start_after_end_returns_empty` |
| 0 起点返回副本 | `test_zero_start_returns_copy` |
| 既有播放数据生成与路径 | 其余 `test_play_assets.py` 用例 |

## 独立审查后的修复

- **Important**：起播边界比较使用原始累加时间，`0.1` 这类延时累加会产生 `0.7999999999999999`，导致正好落在起播点的按键被丢弃。现改为 `1e-6` 容差比较，并新增 `0.1` 步长的回归用例。
- **Minor**：起点之后只剩尾段延时时返回空列表（避免空转播放）；补充输入不可变测试。
- 复验结果：`Ran 173 tests ... OK`。

## 手动确认

- 从曲目中段（延时中）起播：按键不再抢在辅助线之前，整首保持同步。
- 从头播放行为不变。

## 结论

根因消除；边界行为、浮点累加与既有回归全部通过（共 173 项）。
