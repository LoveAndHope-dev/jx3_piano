# Tasks

## 1. 工具栏合并为一行

- [ ] 1.1 把 `_setup_piano_roll_tab` 中 `range_toolbar`（音域映射/量化控件）的全部 `addWidget` 调用迁移进同一个 `toolbar`（`QHBoxLayout`），删除 `range_toolbar` 这个独立布局对象与多余的 `addStretch()`；验证：启动程序，打开任意曲目，「铺面编辑」标签页的工具栏控件（标题、未保存提示、播放/保存按钮、显示映射按钮、最低/最高映射下拉框、量化下拉框）目视只占一行。

## 2. 只读音域展示

- [ ] 2.1 新增 `_note_name_for_pitch(pitch)` 方法（复用 `MidiToKeysConverter().get_note_name(pitch)` 换算为标准钢琴音名，如 `C4`，不复用下拉框专用的游戏按键字母 `self.key_ladder`），并在合并后的 toolbar 中新增两个只读字段控件 `range_bottom_display`/`range_top_display`（`QLineEdit` + `setReadOnly(True)`），分别带标签「当前最低键:」「当前最高键:」；验证：运行程序，确认两个字段在界面上可见且无法通过键盘输入修改内容。
- [ ] 2.2 新增 `_refresh_range_display()` 方法，读取 `self.piano_roll.get_instrument_range()` 并用 `_note_name_for_pitch` 写入上述两个只读字段；在 `_reset_instrument_range`、`on_range_low_combo_changed`、`on_range_high_combo_changed` 末尾调用该方法，并把 `self.piano_roll.instrumentRangeChanged` 信号连接到该方法（忽略信号参数，统一以 `get_instrument_range()` 为准）；验证：在 GUI 中加载一首曲目后只读字段显示默认范围对应的标准音名；拖动黄色音域框后只读字段随之刷新；切换「最低映射」或「最高映射」下拉框（含触发低边界下压的跨度调整）后只读字段显示实际生效边界对应的标准音名。

## 3. 验证

- [ ] 3.1 启动 `gui.py`，完整走一遍：打开曲目 → 查看默认只读值 → 拖动音域框多次（含跨越 B-C/E-F 的情况）→ 切换最低/最高映射下拉框 → 切换到另一首曲目确认重置；记录每一步只读字段与 `get_instrument_range()` 实际值一致，且工具栏始终为一行。
