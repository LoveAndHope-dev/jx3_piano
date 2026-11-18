# Design

- `app/main_window.py`：`play_listbox.setSelectionMode(QAbstractItemView.ExtendedSelection)`；列表上方搜索行追加「全选」与「删除选中」按钮（小号样式）。
- `app/ui/playlist_page.py`：
  - 行控件去掉删除按钮；`mousePressEvent` 根据 Ctrl/Shift 调用 `item.setSelected`、范围选择或普通单选，并更新当前项。
  - 新增 `select_all_play_items()`：`play_listbox.selectAll()`。
  - 新增 `on_delete_selected_play_items()`：收集 `selectedItems()`，一次确认（显示数量与当前项未保存提示），逐个调用 `_delete_play_track(path, name)`；删除当前项后 `_clear_piano_roll_cache()`，最后刷新并记录数量。
  - 保留 `on_delete_play_item(path=None, name=None)` 供单曲删除入口与测试使用，内部复用 `_delete_play_track`。
- `piano_roll/canvas_paint.py`：
  - `_note_brush`：不再依据 `mapped`，改为 `self._pitch_in_instrument_band(pitch)`；框外灰色 `#7F8C8D`（选中 `#E59866`），框内保持 `#58D68D` / 选中 `#F5B041`。
  - 新增 `_refresh_note_range_colors()`，在 `_update_range_item_geometry()` 开头与背景一起刷新。
  - `_row_color`：框外颜色由 `.darker(130)` 改为 `.darker(190)`，加大框内外亮度差。
- 选中集合变化时仍由 `_set_selection` 更新画刷；`_update_item_geometry` 使用新的 `_note_brush`。

## 验证

- 列表：Ctrl/Shift 选择、全选、批量删除、取消删除、删除当前项清空铺面。
- 音符：框外变灰、框内恢复、移动框体即时刷新。
- 背景：框外颜色亮度显著低于框内。
- 既有 226 项回归。
