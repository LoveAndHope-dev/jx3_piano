---
change: piano-toolbar-zoom-and-theme-modes
design-doc: docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/design.md
base-ref: 961757b
archived-with: 2026-11-14-piano-toolbar-zoom-and-theme-modes
---

<!-- comet-task-authority: docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/tasks.md -->

# 工具栏重排、纵向缩放与亮暗主题 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans. 任务状态以 tasks.md 为准；本计划只用 `comet-task-ref` 引用任务 ID。

**Goal:** 三行工具栏 + 合并主按钮；钢琴窗 Shift+滚轮纵向缩放与播放纵向聚焦；控制面板亮/暗切换。

**Architecture:** 工具栏在 `app/ui/piano_page.py`；按钮状态集中在 `_update_primary_btn`；行高改为画布实例状态；主题令牌与 `apply_theme` 在 `app/ui/theme.py` 与 `app/main_window.py`。

**Spec:** `docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/design.md`

## Global Constraints

- 播放、撤销、曲谱优化、导入/删除行为不变（除编辑模式不再直接播放）。
- 公开测试入口 `play_btn` / `range_toggle_btn` 等保留。
- 200 项既有测试按新结构更新后全绿。

## Review Focus

- 三行布局在窗口缩放时的左右分组是否正确。
- 合并按钮状态在模式切换、播放开始/结束、保存后是否一致。
- 纵向缩放是否保持鼠标锚点且不触发 `notesChanged`。
- 播放聚焦是否只在锁定时执行一次。
- 浅色主题下按钮/文字/边框对比度与语义色。

---

### Task 1: 工具栏三行与合并按钮

<!-- comet-task-ref:1f2eedd2-dbf8-4069-b28d-e8f685b2720c -->
<!-- comet-task-ref:ef0a020a-6c8d-402d-9741-cd597bb3850a -->
<!-- comet-task-ref:0a9a3739-5229-42f7-8dda-f1b584ee3e26 -->
<!-- comet-task-ref:4b0a1700-e465-4484-afd9-3d25678f7b58 -->
<!-- comet-task-ref:fbbc64ab-beed-4b0f-bc51-511629f24a38 -->

**Files:** `app/ui/piano_page.py`、`app/playback.py`、`app/history.py`、`app/ui/playlist_page.py`

**Step 1:** 第一行标题+模式按钮（右侧），第二行主按钮/优化靠左 + 量化/BPM 靠右，第三行四个字段靠左。
**Step 2:** 主按钮 `on_primary_action` 与 `_update_primary_btn`；删除 `piano_save_btn` 引用。
**Step 3:** 播放/停止/完成/历史/列表统一调用 `_update_primary_btn`。

### Task 2: 纵向缩放与聚焦

<!-- comet-task-ref:35b82f42-c5ca-48ba-8645-69321bfcf6a5 -->
<!-- comet-task-ref:a0993a60-cff8-4c80-b698-388257aa4935 -->
<!-- comet-task-ref:8a43c5ec-c81c-477b-8057-63b625cdf34d -->
<!-- comet-task-ref:6118deed-755b-4e8c-94e8-59fe76499a29 -->
<!-- comet-task-ref:41119a85-2be9-4f5e-9063-3fb9d45f71fc -->

**Files:** `piano_roll/canvas.py`、`canvas_input.py`、`canvas_paint.py`、`ruler.py`

**Step 1:** 行高实例化（6–24px）并让绘制/交互/键盘读取 `canvas.row_height`。
**Step 2:** Shift+滚轮缩放，鼠标音高为锚点；`set_row_height` 重建背景并恢复滚动。
**Step 3:** `focus_vertical_range_center()` 在 `set_playhead_locked(True)` 时执行。
**Step 4:** 键盘在水平滚动时几何不变（回归测试）。

### Task 3: 亮暗主题

<!-- comet-task-ref:2067332f-6c46-4bce-a4fd-155466621e98 -->
<!-- comet-task-ref:00e4aa1b-57bb-4a45-a92f-07511c652af8 -->
<!-- comet-task-ref:0ebad794-4c09-4eaa-a91c-d5000dfdbfc7 -->

**Files:** `app/ui/theme.py`、`app/main_window.py`

**Step 1:** `DARK_TOKENS` / `LIGHT_TOKENS` 与 `apply_theme`。
**Step 2:** 控制面板标题行新增切换按钮（置顶左侧），文案显示目标模式。
**Step 3:** 仅会话内记忆。

### Task 4: antd 细化

<!-- comet-task-ref:28cf8611-c0c8-4e87-b85a-fae8ba5dba1e -->
<!-- comet-task-ref:f9b2b823-3672-4a81-abde-293c90ad04d1 -->

**Step 1:** `pageTitle` 16/600、`primaryBtn` 主色/状态、弹窗与菜单表面。
**Step 2:** 两套主题复用同一状态派生逻辑。

### Task 5: 验证

<!-- comet-task-ref:5f8f1e15-355b-4ae1-a404-c01a7b34f743 -->
<!-- comet-task-ref:b31ecc88-7c44-4623-ba12-4ad0ff4c6e17 -->
<!-- comet-task-ref:07fc9dae-4f7f-4970-aa71-2ed504bb4a13 -->

**Step 1:** 更新工具栏测试，新增合并按钮、缩放、聚焦、键盘固定、主题切换测试。
**Step 2:** 全量测试。
**Step 3:** 深/浅截图核对；重新打包并启动冒烟。

## Workflow follow-up

- `comet guard piano-toolbar-zoom-and-theme-modes build --apply -- .venv\Scripts\python.exe -m unittest discover -s tests -v`。
