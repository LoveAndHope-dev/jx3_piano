---
change: refactor-project-structure-and-antd-theme
design-doc: docs/openspec/changes/refactor-project-structure-and-antd-theme/design.md
base-ref: 3479117
archived-with: 2026-11-14-refactor-project-structure-and-antd-theme
---

<!-- comet-task-authority: docs/openspec/changes/refactor-project-structure-and-antd-theme/tasks.md -->

# 项目结构重构与 Ant Design 主题 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans. 任务状态以 tasks.md 为准；本计划只用 `comet-task-ref` 引用任务 ID。

**Goal:** 把三个千行文件拆成职责模块，并用 antd 深色令牌统一界面；行为与导入路径不变。

**Architecture:** 入口文件保留薄门面；`app/`（窗口、页面、播放、历史、线程、主题）、`piano_roll/`、`music/` 三个包承载实现。

**Spec:** `docs/openspec/changes/refactor-project-structure-and-antd-theme/design.md`

## Global Constraints

- 188 项测试全绿；每步迁移后全量运行。
- `import gui`、`from piano_roll import ...`、`from build_music import ...` 不变。
- 不改变控件数量、功能位置、快捷键与播放/编辑行为。
- 单文件目标 ≤800 行。

## Review Focus

- 门面是否遗漏测试替换的模块级名字（Qt 类、路径函数）。
- mixin 拆分是否引入循环导入或丢失初始化顺序。
- QSS 选择器是否仍匹配现有 objectName。
- 画布绘制/交互拆分后行为是否一致（缩放、拖动、框选、播放线）。
- 打包后新包是否被 PyInstaller 收集。

---

### Task 1: 主题

**Files:** `app/ui/theme.py`（新建）、`gui.py`

<!-- comet-task-ref:6498d221-7a48-4a34-870f-c566ba404a41 -->
<!-- comet-task-ref:f8df1d2a-e827-405e-8ab0-880d3016fa11 -->
<!-- comet-task-ref:03d60010-0e5a-410b-8385-5fc32bc321e3 -->
<!-- comet-task-ref:bd619a14-8402-47e7-9593-e5354d4a0bcd -->

**Step 1:** 定义 `TOKENS` 与 `build_stylesheet(tokens)`，覆盖现有全部选择器（`QGroupBox`、`QPushButton#playBtn/stopBtn/importBtn/refreshBtn/clearBtn`、输入框、标签页、列表、滚动条、日志、`QFrame#leftPanel/rightPanel`、`creditLabel`）。

**Step 2:** `setup_style` 改成 `self.setStyleSheet(build_stylesheet())`；新增 `app/__init__.py`、`app/ui/__init__.py`。

**Step 3:** 测试：令牌必需键齐全、样式含 `#1677ff`、不含 `#3498DB`。

### Task 2: 线程与历史

**Files:** `app/workers/play_thread.py`、`app/workers/batch_import.py`、`app/history.py`、`gui.py`

<!-- comet-task-ref:81024c32-cf2e-4d59-a76a-943a10ad5531 -->
<!-- comet-task-ref:5f3b215a-9a77-4b5c-bb33-7f52e072ad3e -->

**Step 1:** 原样搬运 `PlayThread`、`BatchConversionWorker` 到 `app/workers/`，`gui.py` 导入使用。

**Step 2:** 把 `_snapshot_state`、`_states_equal`、`_record_history`、`_apply_history_state`、`undo_last_edit`、`redo_last_edit`、`_update_piano_dirty_indicator` 移入 `HistoryMixin`。

**Step 3:** `MidiConverterGUI` 继承 `HistoryMixin`；跑测试。

### Task 3: 播放控制

**Files:** `app/playback.py`、`gui.py`

<!-- comet-task-ref:08a9d0db-2f5b-46aa-886d-dd4b6a8c4215 -->

**Step 1:** 移动 `on_play_progress`、`toggle_play`、`start_playing`、`stop_playing`、`_drain_previous_play_thread`、`_cleanup_play_thread`、`on_play_finished` 到 `PlaybackMixin`。

**Step 2:** 保留 `closeEvent` 在窗口类（跨页协调）。

### Task 4: 页面拆分

**Files:** `app/ui/piano_page.py`、`app/ui/playlist_page.py`、`app/ui/log_page.py`、`app/main_window.py`、`gui.py`

<!-- comet-task-ref:099d21ae-93f9-40b2-9c67-686cdf0e6f82 -->
<!-- comet-task-ref:4ca3483e-1ccb-42f5-ae27-722cb48907b4 -->

**Step 1:** `PianoPageMixin`：`_setup_piano_roll_tab`、音域/BPM/量化、`_load_piano_roll`、`on_piano_roll_notes_changed`、`on_arpeggiate_clicked`、`_save_current_play_assets`、`save_piano_roll`、`_clear_piano_roll_cache`、相关辅助。

**Step 2:** `PlaylistPageMixin`：列表刷新/搜索/排序/行控件/选中/导入/新建/删除。

**Step 3:** `LogPageMixin`：日志页、`log`、`clear_log`、`toggle_topmost`。

**Step 4:** `app/main_window.py` 只留 `__init__`、`setup_ui`、`setup_style`、`closeEvent`、mixin 继承；`gui.py` 门面 re-export。

### Task 5: 铺面拆包

**Files:** `piano_roll/`（新建）、`piano_roll.py`（门面）

<!-- comet-task-ref:696579c4-e5ea-4d5b-a1fc-2234c807d078 -->
<!-- comet-task-ref:dd537c37-a7e9-4f02-9162-7522fa911c77 -->
<!-- comet-task-ref:b8a250fd-516c-4b88-9a14-edc8a708e519 -->

**Step 1:** `geometry.py`：常量、`clamp_pixels_per_second`、`anchored_scroll_value`、`pasted_starts`、`octave_shift_pitches`、`playback_notes_from_position`、BPM/网格函数。
**Step 2:** `painting.py` + `canvas.py`：绘制辅助与交互/状态分离。
**Step 3:** `ruler.py`、`widget.py`；`__init__.py` re-export；`piano_roll.py` 门面。

### Task 6: 音乐处理拆包

**Files:** `music/`（新建）、`build_music.py`（门面）

<!-- comet-task-ref:aed9a53e-e3b3-4e64-8263-a7cd1945fa5a -->
<!-- comet-task-ref:7f36a39d-5f18-4269-90b7-a645562a822d -->
<!-- comet-task-ref:5e1ceb41-5bd0-44fe-8d88-529294d65d58 -->

**Step 1:** `mapping.py`、`midi_io.py`、`analysis.py`。
**Step 2:** `playback.py`、`cli.py`。
**Step 3:** `converter.py` 薄委托；`build_music.py` 门面与 `__main__`。

### Task 7: 验证

<!-- comet-task-ref:7f009e83-d6f5-4e04-a3a0-b49b7342aad5 -->
<!-- comet-task-ref:e511b2ad-ffb8-4050-89a7-149b80a8e39f -->
<!-- comet-task-ref:b13f2819-1446-4368-8400-6a6585c3f5fa -->

**Step 1:** 结构冒烟测试（公开导入/名称、行数约束）。
**Step 2:** 全量测试。
**Step 3:** 截图逐页核对；重新打包并启动冒烟。

## Workflow follow-up

- `comet state complete-build` → `comet guard refactor-project-structure-and-antd-theme build --apply -- .venv\Scripts\python.exe -m unittest discover -s tests -v`。
