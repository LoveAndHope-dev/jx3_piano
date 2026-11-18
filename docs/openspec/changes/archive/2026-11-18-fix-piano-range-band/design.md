# Design

- `CanvasPaintMixin._build_background`：
  - 新增 `self._row_items: Dict[int, QGraphicsRectItem]`，逐行记录图元。
  - 底色改为 `_row_color(pitch)`：`_range_low_pitch - 1 <= pitch <= _range_high_pitch + 1` 用正常色，否则 `.darker(130)`。
- 新增 `_refresh_background_range()`：遍历 `_row_items` 重新设置画刷；`_update_range_item_geometry()` 末尾调用，覆盖拖动、映射下拉、加载与缩放。
- `set_notes` 清空场景时同步清空 `_row_items`。
- 音符颜色仍由 `mapped` 决定，不受影响。

验证：拖动/改映射后对比行图元颜色；默认加载时 35–84 行正常、其余变暗。
