# 验收记录：fix-piano-range-band

## 环境

- Windows + Python 3.14 + PyQt5
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 226 tests ... OK`

## 根因

钢琴窗背景行按固定的游戏键位映射集合（约 B1–C6）决定淡/暗，与黄色音域框的 `_range_low_pitch/_range_high_pitch` 无关；框体移动后也不会重绘。

## 修复

- `_build_background` 逐行记录 `pitch → QGraphicsRectItem`。
- 行底色改由 `_row_color(pitch)` 计算：`框体下界-1 ≤ pitch ≤ 框体上界+1` 使用正常色，其余 `.darker(130)`，与框体视觉范围一致。
- 新增 `_refresh_background_range()`；`_update_range_item_geometry()` 开头调用，因此：
  - 拖动黄色框体（演奏模式）→ 淡色区域同步移动；
  - 修改最低/最高键位映射 → 跨度变化后同步；
  - 加载曲目、缩放、重建背景后保持正确。
- 音符颜色仍按 `mapped` 字段区分，未改动。

## 覆盖

| 场景 | 测试 |
| --- | --- |
| 默认范围淡/暗边界（35/84 在内，34 在外） | `test_background_band_follows_instrument_range` |
| 框体移动后行颜色变化 | 同上（46 移出、90 移入） |
| 映射跨度变化后更新 | `test_background_band_follows_span_change` |
| 128 行图元完整 | 同上 |

## 手动确认

- 编辑模式下背景淡色区域与默认框体（C2–B5 扩展 1 半音，即 B1–C6）一致。
- 演奏模式拖动黄框，淡色区域随之上下移动；改映射下拉后同步。
