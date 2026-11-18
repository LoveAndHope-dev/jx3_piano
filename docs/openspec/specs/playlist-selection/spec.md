# playlist-selection Specification

## Purpose
让播放列表可以批量选择与删除，减少整理曲目时的重复操作。

## Requirements

### Requirement: 多选与全选

播放列表 SHALL 支持扩展选择：普通点击选中单项，Ctrl+点击切换单项，Shift+点击从当前项到点击项连续选中。界面 SHALL 提供「全选」操作，选中当前过滤结果中的全部曲目。

#### Scenario: Ctrl 多选

- **WHEN** 依次 Ctrl+点击三个曲目行
- **THEN** 三行同时处于选中状态

#### Scenario: 全选

- **WHEN** 点击「全选」
- **THEN** 列表中当前显示的所有曲目都被选中

### Requirement: 批量删除

界面 SHALL 提供「删除选中」操作：删除前一次性确认并显示数量；确认后删除每个选中曲目的 `midi/` 副本、`edited` MIDI 与 play_code JSON。删除的曲目包含当前打开项时 MUST 清空铺面；完成后刷新列表。列表 MUST NOT 再提供每行独立的删除按钮。

#### Scenario: 删除多个曲目

- **WHEN** 选中 3 个曲目并点击「删除选中」并确认
- **THEN** 3 个曲目及其工作文件被删除，列表只保留未选中的项

#### Scenario: 删除当前曲目

- **WHEN** 选中包含当前打开曲目的多项并确认删除
- **THEN** 铺面清空并回到占位提示

#### Scenario: 取消删除

- **WHEN** 在确认框选择「否」
- **THEN** 所有曲目保持不变
