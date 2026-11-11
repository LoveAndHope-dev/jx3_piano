# Comet Design Handoff

- Change: playlist-search-add-remove
- Phase: design
- Mode: compact
- Context hash: 55f81a00da15b6cbde727baff644b10019830ef96b7afd97512560800b43fe2a

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/playlist-search-add-remove/proposal.md

- Source: docs/openspec/changes/playlist-search-add-remove/proposal.md
- Lines: 1-30
- SHA256: 7213ace42500da3d3f89deda7e096065ea088eb8df1743219f737423b67051ed

```md
# 播放列表搜索、排序、新建与删除

## Why

左侧播放列表直接列出 `midi/` 下的全部文件：曲目多时只能靠肉眼滚动查找，也没有排序；导入后无法在工具内新建空白曲目，不想要的曲目也无法从列表里移除。本次给播放列表补上搜索、排序、新建空曲目与移除能力，并保证移除时清掉工具内该曲目的缓存。

## What Changes

- 播放列表上方新增搜索框：按文件名子串模糊匹配（不区分大小写），清空即恢复全部。
- 新增排序下拉框：按名称升序（默认）或按导入时间（文件修改时间）倒序排列。
- 「📁 导入MIDI」右侧新增「➕ 新建」按钮：在 `midi/` 生成一个唯一命名的空 MIDI（120 BPM、4/4、单音轨），刷新并自动选中加载到铺面。
- 列表右侧新增「🗑 删除」按钮：把选中曲目从列表隐藏（写入持久化的隐藏记录，磁盘 MIDI 文件保留），并在删除当前加载曲目时清空铺面、播放数据、播放辅助线与 BPM 等工具内缓存。
- 隐藏记录在刷新与重启后仍生效，避免被删除的曲目重新出现；列表右键菜单提供「恢复所有已移除曲目」作为唯一恢复入口。

## Capabilities

### New Capabilities

- `playlist-management`：播放列表的搜索、排序、新建空曲目、隐藏/删除与缓存清理。

### Modified Capabilities

- 无。

## Impact

- 新增 `playlist_store.py`：隐藏记录的读写、过滤/排序、唯一命名与空 MIDI 生成（可单测）。
- `gui.py`：播放列表区域新增搜索框、排序下拉框、新建与删除按钮；刷新列表改为经过过滤/排序；删除时清理缓存。
- 不改播放、铺面编辑、BPM、MIDI 导出逻辑；不新增第三方依赖（mido 已有）。
- 已知限制：隐藏记录按文件名匹配；若手工用同名文件替换，仍视为已隐藏，需要「恢复所有已移除曲目」后才重新出现。

```

## docs/openspec/changes/playlist-search-add-remove/design.md

- Source: docs/openspec/changes/playlist-search-add-remove/design.md
- Lines: 1-102
- SHA256: 286056bb4cf1f42fb4ec4b1bb0880b68f9127b5b98678f754589c40ccc81ff86

[TRUNCATED]

```md
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

```

Full source: docs/openspec/changes/playlist-search-add-remove/design.md

## docs/openspec/changes/playlist-search-add-remove/tasks.md

- Source: docs/openspec/changes/playlist-search-add-remove/tasks.md
- Lines: 1-37
- SHA256: 2502bd231cea2dea45c72e002809aac3b70421b03186ac3fe5422998a69714f5

```md
# Tasks

## 1. 播放列表数据层

- [ ] 1.1 新增 `playlist_store.py`：`load_hidden(midi_dir)` / `save_hidden(midi_dir, names)`（`midi/.hidden_playlist.json`，损坏时按空集合处理）；新增 `tests/test_playlist_store.py` 覆盖正常读写、缺失文件、非法 JSON <!-- comet-task:a369caed-d8e2-4a46-b5a8-b3a52d892797 -->
- [ ] 1.2 实现 `list_entries(midi_dir)`、`filter_entries(entries, query)`、`sort_entries(entries, mode)`：只收 `.mid/.midi`；过滤大小写不敏感；名称升序、mtime 从新到旧且同秒用名称稳定排序；补充单测并运行通过 <!-- comet-task:db1ecd16-0c14-4619-9adb-431d0b5e5181 -->
- [ ] 1.3 实现 `unique_midi_name(midi_dir, base)` 与 `create_blank_midi(path, bpm=120.0, time_signature=(4,4))`：用 mido 写入 tempo、拍号与空音轨；单测读回 tempo=120、4/4、至少 1 个音轨，并验证连续生成不重名 <!-- comet-task:6ef60b6e-0987-4348-b00f-ea0edaa50bb7 -->

## 2. 列表 UI 与搜索排序

- [ ] 2.1 播放列表上方新增搜索框与排序下拉框（名称/导入时间），列表改为「列表 + 右侧删除按钮」布局；搜索/排序变化调用 `refresh_play_list()` <!-- comet-task:07cb9b65-28a9-4b07-977f-e119631cb7bd -->
- [ ] 2.2 改写 `refresh_play_list()`：读隐藏集合 → 过滤隐藏 → 应用搜索 → 应用排序 → 重建列表并按路径恢复选中；无结果显示占位提示 <!-- comet-task:da4ec2f8-2a18-48a1-a137-f59910facc3a -->
- [ ] 2.3 手动验收：输入关键词过滤、清空恢复、切换两种排序、搜索与排序叠加、选中项保持 <!-- comet-task:ad9986ac-7d18-47c8-bb8b-20d9dca3bc38 -->

## 3. 新建空曲目

- [ ] 3.1 「📁 导入MIDI」右侧新增「➕ 新建」按钮：调用 `unique_midi_name` + `create_blank_midi`，失败弹错误提示且不改列表 <!-- comet-task:18a313bd-4de5-4f40-8092-c112d72cff38 -->
- [ ] 3.2 新建成功后刷新列表、按路径选中并加载；验证铺面为空、BPM 显示 120.0、未保存标记不出现；连续新建生成两个文件 <!-- comet-task:ac049ea1-723a-45b3-ab8a-a2d81948131f -->

## 4. 删除与缓存清理

- [ ] 4.1 列表右侧「🗑 删除」按钮：无选中时禁用；点击弹确认框，取消不改状态；确认后写隐藏记录并刷新列表 <!-- comet-task:72bbf868-43c0-4cb8-9c4c-7447d422e46f -->
- [ ] 4.2 新增 `_clear_piano_roll_cache()`：停止播放、清空铺面与辅助线、重置 `current_midi_path`/音轨/`current_bpm`/BPM 框、清未保存标记与保存按钮、切回占位页；删除当前曲目时调用 <!-- comet-task:1a76d036-11d3-4afd-856b-7e9ca06b9184 -->
- [ ] 4.3 手动验收：删除未加载曲目不影响铺面；删除当前加载曲目后缓存清空；刷新与重启后被删曲目仍隐藏 <!-- comet-task:772b7b76-ecf7-4691-992e-d4cdfeee482a -->

## 5. 恢复入口

- [ ] 5.1 列表右键菜单新增「恢复所有已移除曲目」：清空隐藏记录并刷新列表；验证已删除且仍在磁盘的曲目重新出现 <!-- comet-task:0d11f8da-2491-4d1b-a110-b3d2f94f7efd -->

## 6. 集成验证

- [ ] 6.1 运行 `.venv\Scripts\python.exe -m unittest discover -s tests -v`，确认既有 78 项与本轮新增测试全部通过 <!-- comet-task:e7e17eec-9c8d-4ad4-8be6-a3dbba46c2d8 -->
- [ ] 6.2 手动走查：搜索/排序/新建/删除/取消/恢复/重启保持，并确认播放与铺面编辑无回归 <!-- comet-task:84c26964-deb9-4003-b095-bd87251fb5d8 -->

## Workflow follow-up

- 完成 Verify 后按 Comet 交付流程归档或交付，具体方式由用户确认。

```

## docs/openspec/changes/playlist-search-add-remove/.openspec.yaml

- Source: docs/openspec/changes/playlist-search-add-remove/.openspec.yaml
- Lines: 1-2
- SHA256: b8f20def63a86ae4075c5499ff9ed413265d8704692a8493712424dc3f28d8e3

```md
schema: spec-driven
created: 2026-11-11

```

## docs/openspec/changes/playlist-search-add-remove/specs/playlist-management/spec.md

- Source: docs/openspec/changes/playlist-search-add-remove/specs/playlist-management/spec.md
- Lines: 1-87
- SHA256: c17f0d1cc45ba437d9a0cd558a4f49999299a60a58047d54e6ff26fd0b228223

[TRUNCATED]

```md
# Spec Delta

## Purpose

让左侧播放列表可以按名称搜索、按名称或导入时间排序、新建空白曲目，并能把不需要的曲目从列表移除（磁盘文件保留），同时保证移除当前曲目时工具内缓存被清空。

## ADDED Requirements

### Requirement: 按名称搜索播放列表

播放列表上方 SHALL 提供搜索输入框；输入非空时列表只显示文件名包含该子串的曲目（不区分大小写），清空输入后 SHALL 恢复显示全部未被移除的曲目。搜索 MUST 只影响显示，不改变磁盘文件与当前已加载曲目。

#### Scenario: 输入关键词过滤

- **WHEN** 列表中有「青花瓷.mid」「晴天.mid」，在搜索框输入「qing」或「青」
- **THEN** 列表只显示匹配的曲目，其余被隐藏

#### Scenario: 清空搜索

- **WHEN** 搜索框中已有内容，用户清空输入
- **THEN** 列表恢复显示全部未被移除的曲目

### Requirement: 按名称或导入时间排序

播放列表 SHALL 提供排序选择，至少包含「名称」与「导入时间」两项：名称按升序（不区分大小写），导入时间按文件修改时间从新到旧；切换排序后列表立即重排，搜索过滤与排序 MUST 同时生效。当前选中项若仍在结果中，MUST 保持选中。

#### Scenario: 切换为按时间排序

- **WHEN** 列表按名称排序时切换为「导入时间」
- **THEN** 最近导入的曲目排在前面

#### Scenario: 搜索与排序叠加

- **WHEN** 搜索框有关键词且排序为「导入时间」
- **THEN** 只显示匹配项，并按修改时间从新到旧排列

### Requirement: 新建空白曲目

「📁 导入MIDI」右侧 SHALL 提供「➕ 新建」按钮；点击后在 `midi/` 生成一个唯一命名的空 MIDI 文件（120 BPM、4/4 拍、至少一个空音轨），刷新列表并自动选中、加载该曲目到铺面。同名文件已存在时 MUST 追加序号（如「新建曲目_2.mid」），不得覆盖已有文件。

#### Scenario: 新建并自动加载

- **WHEN** 点击「➕ 新建」
- **THEN** `midi/` 出现新的空 MIDI，列表中出现并选中它，铺面显示为空、BPM 显示 120.0、未保存标记不出现

#### Scenario: 连续新建不覆盖

- **WHEN** 连续点击两次「➕ 新建」
- **THEN** 生成两个不同名字的空 MIDI 文件

#### Scenario: 新建失败

- **WHEN** `midi/` 目录不可写导致创建失败
- **THEN** 弹出错误提示，列表与铺面保持原状

### Requirement: 从列表移除曲目并清理缓存

列表右侧 SHALL 提供「🗑 删除」按钮；对选中曲目点击后 MUST 先从列表移除并写入持久化隐藏记录（磁盘 MIDI 文件保留），再判断它是否为当前加载曲目：是则清空铺面音符、播放辅助线、BPM 与播放相关缓存并停止播放。删除 MUST 有确认步骤，取消时不改变任何状态。

#### Scenario: 移除未加载的曲目

- **WHEN** 选中一个未加载的曲目点击删除并确认
- **THEN** 该曲目从列表消失，磁盘文件仍在，当前铺面与播放状态不变

#### Scenario: 移除当前加载的曲目

- **WHEN** 删除当前正在编辑的曲目并确认
- **THEN** 列表移除该曲目，铺面清空、播放辅助线回到 0、BPM 重置、未保存标记清除、保存按钮禁用

#### Scenario: 取消删除

- **WHEN** 在确认框中点击取消
- **THEN** 列表、缓存与磁盘文件都不发生变化

#### Scenario: 刷新或重启后仍移除

- **WHEN** 删除后刷新列表或重启程序
- **THEN** 被移除的曲目不再出现

### Requirement: 恢复被移除的曲目

```

Full source: docs/openspec/changes/playlist-search-add-remove/specs/playlist-management/spec.md
