# Design

## Context

- 播放列表条目同时有 `QListWidgetItem` 文字与 `setItemWidget` 行控件，两者都绘制曲目名，产生重影。
- 删除当前写入 `midi/.hidden_playlist.json` 隐藏记录；用户希望直接删掉 `midi/` 下导入时生成的副本。
- 工具栏上方动作行当前是「曲谱优化」，主行开头是标题「铺面编辑」。

## Decisions

1. **条目文字清空**：`QListWidgetItem` 只保留路径与文件名数据，`setText("")`；显示交给行控件的 `QLabel`。搜索/排序仍基于 `list_entries` 的文件名，选中恢复仍按 `UserRole` 路径，行为不变。
2. **物理删除**：确认后 `os.remove(path)` 删除 `midi/` 副本；`FileNotFoundError` 视为已删除；其他 `OSError` 弹错误并保留列表。删除当前曲目继续调用 `_clear_piano_roll_cache()`。随后 `refresh_play_list()`。
3. **隐藏记录退役**：删除 `load_hidden`/`save_hidden` 的主流程调用与恢复菜单；`playlist_store` 保留隐藏函数（旧文件兼容），但刷新不再过滤隐藏集合。
4. **工具栏换位**：动作行放标题；主行首两项为「弹奏」「曲谱优化」，其余顺序不变（未保存、保存、模式、两个映射、第二行绝对键/量化/BPM）。
5. **风险**：物理删除不可恢复 → 保留确认框并在文案中说明「会删除 midi 文件夹中的副本」；源文件不受影响。
6. **测试**：GUI 测试改为断言删除后文件不存在、取消不删、列表刷新后不出现；去掉隐藏记录与恢复相关用例；新增条目文字为空且行控件含名称的断言。

## Test Strategy

- offscreen GUI：新建 → 删除当前（文件消失、缓存清空）、取消不删、删除未加载不影响铺面。
- 行控件：`item.text() == ""` 且 `itemWidget` 的标签文本为曲目名。
- 回归：既有 129 项（其中删除/隐藏相关用例按新语义调整）。

## Migration Plan

旧 `midi/.hidden_playlist.json` 不再读取；用户如需找回已隐藏曲目，重新导入源文件即可。
