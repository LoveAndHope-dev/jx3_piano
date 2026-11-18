# 验收记录：playlist-multi-select-and-range-contrast

## 环境

- Windows + Python 3.14 + PyQt5
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 232 tests ... OK`

## 变更

### 播放列表多选删除

- 列表启用 `ExtendedSelection`；行内点击支持：
  - 普通点击：只选中该行并设为当前项；
  - Ctrl+点击：切换该行选中状态；
  - Shift+点击：从当前项到点击项连续选中。
- 搜索行下方新增「全选」「🗑 删除选中」。
- 删除选中：一次性确认（显示数量；包含当前打开且有未保存修改时额外提示），逐个删除 `midi/` 副本、`edited` MIDI 与 play_code，最后刷新列表并记录删除数量。
- 删除包含当前曲目时清空铺面并回到占位页。
- 移除每行独立删除按钮；`on_delete_play_item` 保留供单曲入口与测试使用。

### 音符与背景配色

- 音符颜色改为按音域框判断：框内（上下各 1 半音）绿色、框外灰色；选中态分别使用橙色/浅棕。
- 框体拖动或键位映射变化时，音符颜色与背景行**立即刷新**。
- 框外背景由 `.darker(130)` 加深到 `.darker(190)`，框内外亮度差明显增大。

## 覆盖

| 场景 | 测试 |
| --- | --- |
| 全选 | `test_select_all_selects_every_item` |
| 批量删除并清空当前铺面 | `test_delete_selected_play_items` |
| 未选择时不弹确认 | `test_delete_selected_without_selection_does_not_prompt` |
| Ctrl 点击切换选择 | `test_ctrl_click_row_toggles_selection` |
| 音符随框体变灰/恢复 | `test_note_color_follows_instrument_range` |
| 框内外亮度差 | `test_background_contrast_between_band_and_outside` |
| 既有行为 | 其余 226 项 |

## 备注

- 音符灰度不再依据固定游戏键位集合；`mapped` 字段仍保留用于播放提示。
- exe 已重新打包（`477cbdf`），构建产物已清理。
