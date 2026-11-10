# Proposal

## Why

铺面编辑工具栏现有的「最低映射/最高映射」下拉框只代表用户设置的意图：无论是拖动调整跨度（`on_range_low_combo_changed`/`on_range_high_combo_changed` 会在跨度超出键位序列顶端时下压低边界，不回写下拉框），还是直接在铺面上拖动黄色「乐器音域框」（`instrumentRangeChanged` 信号此前未被连接），都可能让框体实际生效的音域与下拉框显示的值不一致。用户目前没有任何地方能确认乐器播放时实际使用的最低/最高键。同时现有工具栏分两行展示（标题/播放/保存一行，音域映射控件另一行），占用了铺面编辑区域的纵向空间。

## What Changes

- 新增两个只读字段，实时展示黄色「乐器音域框」当前真实生效的最低键和最高键标签；下拉框跨度联动、或直接拖动框体后都同步刷新。
- 把「铺面编辑」标签页工具栏的全部控件（标题、未保存提示、播放/保存按钮、显示映射按钮、最低/最高映射下拉框、新增的只读字段、量化下拉框）合并为同一行，不再分两行展示。

## Capabilities

### New Capabilities
- `piano-roll-range-readout`: 铺面编辑工具栏实时只读展示当前乐器音域框（黄色框）实际生效的最低/最高键标签，随拖动或下拉框联动变化同步更新。

### Modified Capabilities

(无：工具栏单行布局是实现/呈现细节，不改变已声明的行为需求)

## Impact

- `gui.py`：`_setup_piano_roll_tab` 工具栏构建、`_reset_instrument_range`/`on_range_low_combo_changed`/`on_range_high_combo_changed` 的范围变化回调，新增对 `piano_roll.instrumentRangeChanged` 信号的连接。
