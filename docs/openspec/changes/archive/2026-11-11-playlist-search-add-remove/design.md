---
comet_change: playlist-search-add-remove
role: technical-design
canonical_spec: openspec
archived-with: 2026-11-11-playlist-search-add-remove
status: final
---

# Design

行为需求以 `specs/playlist-management/spec.md` 为准；本文说明实现方式与取舍。

## Context

- 播放列表当前直接列出 `midi/` 下的文件（`gui.refresh_play_list`），没有搜索、排序、新建或移除能力。
- 列表与铺面通过 `on_select_play_file` / `on_piano_roll_selection_changed` 联动；当前曲目由 `current_midi_path` 表示，铺面数据在 `piano_roll` 内，播放数据在 `play_thread`/`current_bpm` 等字段中。
- 导入流程（`PlayThread` 之外的 `MIDIImportThread`）只负责把文件复制到 `midi/`。
- 项目测试使用 `unittest`，已有 78 项通过。

## Goals / Non-Goals

**Goals:**

- 搜索、排序、新建、移除都由一个可测试的数据层支撑，UI 只做展示与调用。
- 移除语义可逆（保留文件 + 隐藏记录 + 恢复入口），且删除当前曲目时彻底清理缓存。
- 不改变导入、播放、铺面编辑与 BPM 行为。

**Non-Goals:**

- 不做重命名、拖拽排序、多选删除。
- 不做“彻底删除磁盘文件”。
- 不持久化搜索词与排序选择（本次会话内有效）。

## Decisions

### 1. 独立 `playlist_store.py` 数据层

模块提供：

- `load_hidden(midi_dir) -> Set[str]` / `save_hidden(midi_dir, names)`：隐藏记录存放在 `midi/.hidden_playlist.json`（JSON 数组）。读取失败或格式非法时按空集合处理并保留原文件。
- `list_entries(midi_dir) -> List[Entry]`：返回 `(name, path, mtime)`，只含 `.mid/.midi`。
- `filter_entries(entries, query) -> List[Entry]`：文件名子串、大小写不敏感。
- `sort_entries(entries, mode) -> List[Entry]`：`name` 升序（不区分大小写），`mtime` 从新到旧。
- `unique_midi_name(midi_dir, base="新建曲目") -> str`：`新建曲目.mid`、`新建曲目_2.mid`… 不覆盖。
- `create_blank_midi(path, bpm=120.0, time_signature=(4, 4))`：用 mido 写一个含 `set_tempo`、`time_signature` 与空音轨的文件。

未采用「列表直接读目录、删除即删文件」：会破坏用户文件，且刷新后无法保持移除状态。

### 2. 隐藏记录按文件名

- 记录文件名而不是绝对路径，移动 `midi/` 目录或复制工程后仍然有效。
- 恢复入口清空整个隐藏集合，实现简单且不会误删记录。

### 3. UI 结构

- 列表上方一行：搜索 `QLineEdit`（占位提示「搜索曲目…」）+ 排序 `QComboBox`（名称/导入时间）。
- 列表改为 `QHBoxLayout`：`QListWidget` + 右侧竖排「🗑 删除」按钮（固定宽度，与列表等高）。
- 控制面板按钮行 1：`📁 导入MIDI`、`➕ 新建`、`🔄`。
- 列表 `setContextMenuPolicy(Qt.CustomContextMenu)`，右键菜单一项「恢复所有已移除曲目」。

### 4. 刷新与搜索/排序的组合

`refresh_play_list()` 变成：

1. 读取隐藏集合与目录条目；
2. 过滤掉隐藏项；
3. 应用当前搜索词；
4. 按当前排序模式排序；
5. 重建列表并尽量恢复选中项（按路径匹配）。

排序/搜索控件变化时直接调用 `refresh_play_list()`，避免两份过滤逻辑。

### 5. 删除与缓存清理

- 删除前 `QMessageBox.question` 二次确认。
- 确认后：把文件名加入隐藏集合并保存 → `refresh_play_list()`。
- 若被删曲目是 `current_midi_path`：调用新增的 `_clear_piano_roll_cache()`：
  - 正在播放则先 `stop_playing()`；
  - `piano_roll.set_notes([])`、`set_playhead_anchor(0.0)`；
  - `current_midi_path = None`、`current_processed_tracks = []`、`current_bpm = 120.0`、BPM 框回 120.0；
  - `piano_roll_dirty = False`、保存按钮禁用、显示占位页；
  - `piano_stack` 切回占位 label。
- 未保存修改与删除冲突时：确认框合并提示「该曲目有未保存修改，删除会丢失」，只弹一次。

### 6. 新建空曲目

- 生成文件后 `refresh_play_list()`，再按路径选中并触发加载，走既有 `_load_piano_roll`，因此 BPM 回填、铺面重置、未保存状态都复用现有逻辑。
- 生成失败只提示，不刷新列表。

## Risks / Trade-offs

- **隐藏记录与文件同名**：用户手工放回同名文件仍被隐藏。→ 提供「恢复所有已移除曲目」入口，并在 proposal 声明限制。
- **删除当前曲目时的编辑丢失**：确认框明确提示；若不确认则不删除。
- **搜索/排序不持久化**：重启回到默认；本次范围不要求。
- **mtime 精度**：同秒导入的多个文件排序可能不稳定 → 以名称作为第二排序键保证确定性。
- **删光列表**：列表为空时删除按钮与恢复菜单仍可用；删除按钮在无选中时禁用。

## Test Strategy

- `tests/test_playlist_store.py`：隐藏记录读写/损坏容错、过滤（大小写/中文）、排序（名称、mtime、同秒稳定）、唯一命名、空 MIDI 生成后用 mido 读回 tempo/拍号/音轨。
- UI 层手动验收：搜索、切换排序、新建并自动加载、删除未加载/当前曲目、取消删除、刷新与重启后仍隐藏、恢复全部。
- 回归：现有 78 项测试保持通过。

## Migration Plan

无数据迁移：隐藏记录文件缺失时视为空；首次写入时创建。

## Open Questions

无。
