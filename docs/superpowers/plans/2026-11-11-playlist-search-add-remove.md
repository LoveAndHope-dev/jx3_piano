---
change: playlist-search-add-remove
design-doc: docs/openspec/changes/playlist-search-add-remove/design.md
base-ref: da782af7d646a6175d53439016e604be2e3ebda4
archived-with: 2026-11-11-playlist-search-add-remove
---

<!-- comet-task-authority: docs/openspec/changes/playlist-search-add-remove/tasks.md -->

# 播放列表搜索/排序/新建/删除 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans. 任务状态以 tasks.md 为准；本计划只用 `comet-task-ref` 引用任务 ID。

**Goal:** 给左侧播放列表加搜索、排序、新建空曲目、移除（隐藏）与恢复，并在移除当前曲目时清空工具内缓存。

**Architecture:** 新增 `playlist_store.py` 纯数据层（隐藏记录、枚举、过滤、排序、命名、空 MIDI 生成），GUI 只做展示与调用；`refresh_play_list` 统一走「读隐藏 → 过滤 → 搜索 → 排序」；删除当前曲目时调用 `_clear_piano_roll_cache()`。

**Tech Stack:** Python 3 + PyQt5 + mido；测试 `unittest`。

**Spec:** `docs/openspec/changes/playlist-search-add-remove/design.md`

## Global Constraints

- 中文注释与产物；不新增第三方依赖。
- 磁盘 MIDI 永不删除（仅隐藏）；隐藏记录放 `midi/.hidden_playlist.json`。
- 搜索不改变已加载曲目；删除前必须二次确认。
- 既有 78 项测试保持通过；只 `git add` 本计划涉及文件。

## Review Focus

- 隐藏记录损坏/缺失时不能崩溃或清空用户数据（保留原文件）。
- 删除当前曲目后不得残留播放线程、铺面音符或未保存标记。
- 搜索/排序叠加时选中项按路径恢复，不能误切到别的曲目。
- 新建连续两次不得覆盖已有文件。
- 删除未加载曲目不得影响当前铺面或播放。

---

### Task 1: 隐藏记录读写

**Files:** Create `playlist_store.py`; Test `tests/test_playlist_store.py`

**Interfaces:** `load_hidden(midi_dir) -> Set[str]`、`save_hidden(midi_dir, names) -> None`、常量 `HIDDEN_FILENAME = ".hidden_playlist.json"`

<!-- comet-task-ref:a369caed-d8e2-4a46-b5a8-b3a52d892797 -->

**Step 1: 写失败测试**

- 空目录 → 返回空集合。
- 写入 `{"a.mid"}` 后读回一致。
- 文件内容为 `not-json` → 返回空集合且文件内容保持原样。
- 保存会创建 `midi/` 目录。

**Step 2: 运行确认失败**：`.venv\Scripts\python.exe -m unittest tests.test_playlist_store -v` → ImportError。

**Step 3: 实现**

```python
HIDDEN_FILENAME = ".hidden_playlist.json"

def load_hidden(midi_dir: str) -> Set[str]:
    path = os.path.join(midi_dir, HIDDEN_FILENAME)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return set()
    if not isinstance(data, list):
        return set()
    return {str(name) for name in data if isinstance(name, str)}

def save_hidden(midi_dir: str, names: Set[str]) -> None:
    os.makedirs(midi_dir, exist_ok=True)
    path = os.path.join(midi_dir, HIDDEN_FILENAME)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sorted(names), fh, ensure_ascii=False, indent=2)
```

**Step 4: 通过后提交** `feat(playlist): add hidden list store`

### Task 2: 枚举 / 过滤 / 排序

**Files:** Modify `playlist_store.py`; Test `tests/test_playlist_store.py`

**Interfaces:** `Entry = Tuple[str, str, float]`（name, path, mtime）；`list_entries(midi_dir)`、`filter_entries(entries, query)`、`sort_entries(entries, mode)`

<!-- comet-task-ref:db1ecd16-0c14-4619-9adb-431d0b5e5181 -->

**Step 1: 写失败测试**

- 只收 `.mid` / `.midi`，忽略其它文件。
- `filter_entries(entries, "QING")` 命中 `qing.mid`；中文关键词命中；空串返回全部。
- `sort_entries(..., "name")` 不区分大小写升序；`"mtime"` 从新到旧；同 mtime 用名称稳定排序。

**Step 2: 运行确认失败**（函数不存在）。

**Step 3: 实现**

```python
def list_entries(midi_dir: str) -> List[Entry]:
    entries = []
    if not os.path.isdir(midi_dir):
        return entries
    for name in os.listdir(midi_dir):
        if os.path.splitext(name)[1].lower() not in (".mid", ".midi"):
            continue
        path = os.path.join(midi_dir, name)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        entries.append((name, path, mtime))
    return entries

def filter_entries(entries, query):
    needle = query.strip().lower()
    if not needle:
        return list(entries)
    return [e for e in entries if needle in e[0].lower()]

def sort_entries(entries, mode):
    if mode == "mtime":
        return sorted(entries, key=lambda e: (-e[2], e[0].lower()))
    return sorted(entries, key=lambda e: e[0].lower())
```

**Step 4: 通过后提交** `feat(playlist): filter and sort playlist entries`

### Task 3: 唯一命名与空 MIDI

**Files:** Modify `playlist_store.py`; Test `tests/test_playlist_store.py`

**Interfaces:** `unique_midi_name(midi_dir, base="新建曲目") -> str`、`create_blank_midi(path, bpm=120.0, time_signature=(4, 4)) -> None`

<!-- comet-task-ref:6ef60b6e-0987-4348-b00f-ea0edaa50bb7 -->

**Step 1: 写失败测试**

- 空目录返回 `新建曲目.mid`；已存在同名返回 `新建曲目_2.mid`，连续调用两个名字不同。
- `create_blank_midi` 后用 mido 读回：存在 tempo=`500000`、`time_signature` 4/4、至少 1 个音轨且无 note 事件。

**Step 2: 运行确认失败**。

**Step 3: 实现**

```python
def unique_midi_name(midi_dir, base="新建曲目"):
    candidate = f"{base}.mid"
    if not os.path.exists(os.path.join(midi_dir, candidate)):
        return candidate
    index = 2
    while os.path.exists(os.path.join(midi_dir, f"{base}_{index}.mid")):
        index += 1
    return f"{base}_{index}.mid"

def create_blank_midi(path, bpm=120.0, time_signature=(4, 4)):
    numerator, denominator = time_signature
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("set_tempo", tempo=int(round(60_000_000 / bpm)), time=0))
    track.append(mido.MetaMessage("time_signature", numerator=numerator, denominator=denominator, time=0))
    track.append(mido.MetaMessage("end_of_track", time=0))
    mid.tracks.append(track)
    mid.save(path)
```

**Step 4: 通过后提交** `feat(playlist): create blank midi with unique name`

### Task 4: 列表 UI（搜索 / 排序 / 删除布局）

**Files:** Modify `gui.py:578-583`（列表区）、`gui.py:552-566`（按钮行）

**Interfaces:** 新增 `self.play_search`、`self.play_sort_combo`、`self.play_delete_btn`

<!-- comet-task-ref:07cb9b65-28a9-4b07-977f-e119631cb7bd -->

**Step 1: 改布局**

```python
search_row = QHBoxLayout()
self.play_search = QLineEdit()
self.play_search.setPlaceholderText("搜索曲目…")
self.play_search.textChanged.connect(self.refresh_play_list)
self.play_sort_combo = QComboBox()
self.play_sort_combo.addItem("名称", "name")
self.play_sort_combo.addItem("导入时间", "mtime")
self.play_sort_combo.currentIndexChanged.connect(self.refresh_play_list)
search_row.addWidget(self.play_search, 1)
search_row.addWidget(self.play_sort_combo)
list_layout.addLayout(search_row)

row = QHBoxLayout()
row.addWidget(self.play_listbox, 1)
self.play_delete_btn = QPushButton("🗑")
self.play_delete_btn.setToolTip("从列表移除（保留文件）")
self.play_delete_btn.setEnabled(False)
self.play_delete_btn.clicked.connect(self.on_delete_play_item)
row.addWidget(self.play_delete_btn)
list_layout.addLayout(row)
```

按钮行 1 在 `import_btn` 右侧加 `self.new_btn = QPushButton("➕ 新建")`。

**Step 2: 选中状态联动**：`on_select_play_file` 里同步 `self.play_delete_btn.setEnabled(item is not None)`。

**Step 3: 验证**：`py_compile gui.py`。

**Step 4: 提交** `feat(gui): lay out playlist search, sort and delete`

### Task 5: 刷新管线

**Files:** Modify `gui.py`（`refresh_play_list`，约 865-890）

**Interfaces:** Consumes `playlist_store` 全部函数

<!-- comet-task-ref:da4ec2f8-2a18-48a1-a137-f59910facc3a -->
<!-- comet-task-ref:ad9986ac-7d18-47c8-bb8b-20d9dca3bc38 -->

**Step 1: 改写**

```python
def refresh_play_list(self):
    midi_dir = get_midi_dir_path()
    hidden = load_hidden(midi_dir)
    entries = [e for e in list_entries(midi_dir) if e[0] not in hidden]
    entries = filter_entries(entries, self.play_search.text())
    entries = sort_entries(entries, self.play_sort_combo.currentData())
    current_path = self.current_midi_path
    self.play_listbox.blockSignals(True)
    self.play_listbox.clear()
    for name, path, _mtime in entries:
        item = QListWidgetItem(name)
        item.setData(Qt.UserRole, path)
        self.play_listbox.addItem(item)
        if path == current_path:
            self.play_listbox.setCurrentItem(item)
    self.play_listbox.blockSignals(False)
    self.play_delete_btn.setEnabled(self.play_listbox.currentItem() is not None)
```

**Step 2: 验证**：`py_compile` + 手动搜索/排序/**选中保持**。

**Step 3: 提交** `feat(gui): filter and sort the playlist on refresh`

### Task 6: 新建空曲目

**Files:** Modify `gui.py`（新增 `on_new_play_item`）

<!-- comet-task-ref:18a313bd-4de5-4f40-8092-c112d72cff38 -->
<!-- comet-task-ref:ac049ea1-723a-45b3-ab8a-a2d81948131f -->

**Step 1: 实现**

```python
def on_new_play_item(self):
    midi_dir = get_midi_dir_path()
    try:
        os.makedirs(midi_dir, exist_ok=True)
        name = unique_midi_name(midi_dir)
        path = os.path.join(midi_dir, name)
        create_blank_midi(path)
    except Exception as exc:
        QMessageBox.critical(self, "新建失败", f"新建空 MIDI 失败：{exc}")
        return
    self.refresh_play_list()
    self._select_play_list_item_by_path(path)
```

**Step 2: 验证**：连续新建两次生成两个文件；铺面为空、BPM 120.0、无未保存标记。

**Step 3: 提交** `feat(gui): create blank midi from playlist`

### Task 7: 删除与缓存清理

**Files:** Modify `gui.py`（`on_delete_play_item`、`_clear_piano_roll_cache`）

<!-- comet-task-ref:72bbf868-43c0-4cb8-9c4c-7447d422e46f -->
<!-- comet-task-ref:1a76d036-11d3-4afd-856b-7e9ca06b9184 -->
<!-- comet-task-ref:772b7b76-ecf7-4691-992e-d4cdfeee482a -->

**Step 1: 实现**

```python
def on_delete_play_item(self):
    item = self.play_listbox.currentItem()
    if item is None:
        return
    name = item.text()
    path = item.data(Qt.UserRole)
    extra = "（该曲目有未保存修改，删除会丢失）" if (path == self.current_midi_path and self.piano_roll_dirty) else ""
    reply = QMessageBox.question(self, "移除曲目", f"从列表移除「{name}」？{extra}\n磁盘文件会保留。", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if reply != QMessageBox.Yes:
        return
    midi_dir = get_midi_dir_path()
    hidden = load_hidden(midi_dir)
    hidden.add(name)
    save_hidden(midi_dir, hidden)
    if path == self.current_midi_path:
        self._clear_piano_roll_cache()
    self.refresh_play_list()
```

`_clear_piano_roll_cache` 按 design 第 5 条实现（停播、清 notes/辅助线、重置字段与控件、切占位页）。

**Step 2: 验证**：删除未加载曲目不影响铺面；删除当前曲目后铺面为空、BPM 120、无未保存标记、播放停止。

**Step 3: 提交** `feat(gui): remove playlist items and clear caches`

### Task 8: 恢复入口

**Files:** Modify `gui.py`（列表 `customContextMenuRequested` + `on_playlist_context_menu`）

<!-- comet-task-ref:0d11f8da-2491-4d1b-a110-b3d2f94f7efd -->

**Step 1: 实现**

```python
self.play_listbox.setContextMenuPolicy(Qt.CustomContextMenu)
self.play_listbox.customContextMenuRequested.connect(self.on_playlist_context_menu)

def on_playlist_context_menu(self, pos):
    menu = QMenu(self)
    action = QAction("恢复所有已移除曲目", self)
    action.triggered.connect(self.on_restore_hidden_items)
    menu.addAction(action)
    menu.exec_(self.play_listbox.mapToGlobal(pos))

def on_restore_hidden_items(self):
    midi_dir = get_midi_dir_path()
    save_hidden(midi_dir, set())
    self.refresh_play_list()
```

**Step 2: 验证**：删除两个曲目后恢复，仍在磁盘的两个都重新出现。

**Step 3: 提交** `feat(gui): restore hidden playlist items`

### Task 9: 集成验证

**Files:** 无新增

<!-- comet-task-ref:e7e17eec-9c8d-4ad4-8be6-a3dbba46c2d8 -->
<!-- comet-task-ref:84c26964-deb9-4003-b095-bd87251fb5d8 -->

**Step 1: 全量测试**：`.venv\Scripts\python.exe -m unittest discover -s tests -v` → 78 项 + 新增全部 PASS。

**Step 2: 手动走查**：搜索、排序、新建（连续两次）、删除未加载/当前曲目、取消、重启后仍隐藏、恢复全部。

**Step 3: 记录结果**：写入 `docs/superpowers/reports/2026-11-11-playlist-search-add-remove-verification.md`。

**Step 4: 提交** `test: record playlist management acceptance`

## Workflow follow-up

- 完成后 `comet state complete-build`，再 `comet guard playlist-search-add-remove build --apply -- .venv\Scripts\python.exe -m unittest discover -s tests -v`。
