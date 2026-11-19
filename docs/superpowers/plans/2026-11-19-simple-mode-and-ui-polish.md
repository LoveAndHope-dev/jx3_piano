---
change: simple-mode-and-ui-polish
design-doc: docs/openspec/changes/simple-mode-and-ui-polish/design.md
base-ref: 0ea6c4e
archived-with: 2026-11-19-simple-mode-and-ui-polish
---

<!-- comet-task-authority: docs/openspec/changes/simple-mode-and-ui-polish/tasks.md -->

# 控制面板重排、列表体验与简单模式 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans.

**Goal:** 四个按钮同排；左栏 438；勾选标记与悬停滚动；简单模式一键优化播放；亮色框线淡灰；向导分节。

**Spec:** `docs/openspec/changes/simple-mode-and-ui-polish/design.md`

## Global Constraints

- 简单模式进入时静默丢弃未保存修改（不写盘），退出重载原始 MIDI。
- 简单播放每次从原始 MIDI 重新优化，避免叠加。
- 既有 234 项测试保持通过。

## Review Focus

- 简单模式切换与播放的状态一致性；优化后资产与正常模式的覆盖关系。
- 自绘控件的主题跟随与定时器生命周期。
- 亮色下 centralWidget/panel 边框。

---

### Task 1: 控制面板与左侧栏

<!-- comet-task-ref:7a05b8ce-5135-41fe-825c-e39637ecb20b -->
<!-- comet-task-ref:6917d2af-d646-4fc6-89c7-f9f7fe9c9987 -->
<!-- comet-task-ref:210b611f-fb1c-4b70-b40f-2d3bcf32cd25 -->
<!-- comet-task-ref:f70d78eb-a304-4baf-b13b-81e0d6acbbd8 -->

**Files:** `app/main_window.py`、`app/ui/playlist_page.py`、`app/ui/theme.py`、`app/ui/widgets.py`

**Step 1:** 标题行只留标题；新增 `panel_actions` 行放四个按钮；guide 从按钮行移除。
**Step 2:** 左栏 350→438，splitter [438, 562]。
**Step 3:** `widgets.py` 增加 `AntCheckBox`、`MarqueeLabel`；列表行接入。
**Step 4:** `centralWidget` 背景 + 面板/分组框边框 `colorBorder`；主题切换刷新复选框。

### Task 2: 简单模式

<!-- comet-task-ref:3e90928c-0be4-4c74-9ad6-2e6f1787fc2d -->
<!-- comet-task-ref:1944219f-8bc3-4b1c-ad06-d14961a10aee -->
<!-- comet-task-ref:07a4b290-5940-43ea-90ba-074923eb2a37 -->
<!-- comet-task-ref:802c37ed-6a63-488c-be56-53ee169bb64f -->

**Files:** `app/main_window.py`、`app/ui/playlist_page.py`、`app/ui/piano_page.py`、`piano_roll/canvas.py`

**Step 1:** 简单模式切换（移除/恢复标签、清空、固定 Z/7 + C2/B5、显示播放按钮）。
**Step 2:** `arpeggiate_all`。
**Step 3:** `on_simple_play_clicked` 全流程。
**Step 4:** 退出重载原始 MIDI。

### Task 3: 向导

<!-- comet-task-ref:77e55179-493b-4851-b40c-2eb7e6bc29de -->

**Files:** `app/ui/guide.py`

**Step 1:** 简单/正常模式独立小节 + 新按钮与交互说明。

### Task 4: 验证

<!-- comet-task-ref:4b52897f-931e-47ae-afae-a0fcf02a63d7 -->
<!-- comet-task-ref:5bf80e54-d77f-4938-ae3b-69fe77944eb5 -->
<!-- comet-task-ref:fec11f8d-9569-485e-9cb9-4604d0759b08 -->

**Step 1:** 更新/新增测试。
**Step 2:** 全量测试。
**Step 3:** 截图与打包。

## Workflow follow-up

- `comet guard simple-mode-and-ui-polish build --apply -- .venv\Scripts\python.exe -m unittest discover -s tests -v`。
