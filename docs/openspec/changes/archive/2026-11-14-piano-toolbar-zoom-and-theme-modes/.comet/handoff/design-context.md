# Comet Design Handoff

- Change: piano-toolbar-zoom-and-theme-modes
- Phase: design
- Mode: compact
- Context hash: a151ce48880baa65186f9d8a83b8b717fb5f746836f344632861b84df9fbddc7

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/proposal.md

- Source: docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/proposal.md
- Lines: 1-29
- SHA256: c7f15dfd98c207b1cb754d845b2d2710593caba1a8a9f09d26c6ad3e1b2ff112

```md
# 工具栏重排、钢琴窗纵向缩放与亮暗主题

## Why

- 铺面工具栏两行里塞了播放、保存、模式切换、两组建位映射、音域、量化与 BPM，功能位置不直观；「保存」和「弹奏」两个按钮在编辑/演奏模式下只有一个是常用操作。
- 钢琴窗只能横向缩放；音域框较高时播放看不到纵向全貌，播放辅助线的纵向焦点也不固定。
- 界面只有深色主题，缺少亮/暗切换；虽然已套用 antd 令牌，仍可进一步统一层次与间距。

## What Changes

- **工具栏改为三行**：
  - 第一行：「🎼 铺面编辑」标题 + 「演奏模式/编辑模式」切换，切换按钮固定在右侧。
  - 第二行：合并后的「保存/演奏」按钮、曲谱优化靠左；量化、BPM 靠右。
  - 第三行：演奏最低键位映射、演奏最高键位映射、钢琴音域绝对最低键、绝对最高键，全部靠左。
- **保存与弹奏合并**：编辑模式显示「💾 保存」并执行保存；切到演奏模式后显示「▶️ 演奏」，点击开始播放，播放中显示「⏹️ 停止」。编辑模式不再直接开始播放。
- **钢琴窗纵向缩放**：`Shift + 上下滚轮` 调整行高（约 6–24px），以鼠标位置为纵向锚点。
- **左侧键盘固定**：水平滚动时键盘始终贴在左侧（现有行为，补充回归测试）。
- **播放纵向聚焦**：播放时纵向滚动使黄色音域框的纵向中心位于视口中心。
- **亮/暗模式**：控制面板新增切换按钮，整个界面在 antd 深色/浅色令牌之间切换，本次运行内记住。
- **Ant Design 语言细化**：统一控件高度、圆角、间距、标题层级与选中态。

## Impact

- `app/ui/piano_page.py`：工具栏三行布局与合并按钮。
- `app/playback.py`、`app/ui/piano_page.py`：按钮状态与文案随模式/播放状态更新。
- `piano_roll/`：行高缩放、鼠标锚点、播放纵向聚焦；键盘固定回归。
- `app/ui/theme.py`、`app/main_window.py`、`app/ui/playlist_page.py`：亮/暗令牌与切换按钮。
- `tests/`：更新工具栏布局与按钮状态测试，新增纵向缩放、聚焦与主题切换测试。
- 不改变播放数据、撤销历史、曲谱优化、导入/删除与 play_code 生成。

```

## docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/design.md

- Source: docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/design.md
- Lines: 1-100
- SHA256: 54579a70f674177b87dd2a06087d62908c1b63ffeba4e37e43c794efeb2cf471

[TRUNCATED]

```md
# Design

行为需求以 `specs/piano-toolbar/spec.md`、`specs/piano-roll-view/spec.md`、`specs/ui-design-system/spec.md` 为准。

## Context

- 工具栏当前在 `app/ui/piano_page.py::_setup_piano_roll_tab`，两行 `QHBoxLayout`；播放按钮 `self.play_btn` 与保存按钮 `self.piano_save_btn` 分离。
- `PlaybackMixin` 在开始/停止/完成时直接改 `play_btn` 文案与 objectName；`HistoryMixin` 与列表页直接调用 `piano_save_btn.setEnabled`。
- `piano_roll/canvas.py` 的 `ROW_HEIGHT` 是模块常量，`canvas_paint.py`、`ruler.py`、`widget.py` 直接引用；滚轮事件位于 `canvas_input.py`。
- 左侧键盘 `_PianoKeyboardWidget` 是画布左侧的独立控件，纵向滚动时通过 `_on_canvas_scrolled` 同步；水平滚动不影响它（用户确认已固定）。
- 主题在 `app/ui/theme.py`，`TOKENS` 为深色；`main_window.setup_style` 直接生成一次样式。

## Decisions

### 1. 工具栏三行

```
[🎼 铺面编辑] ................................ [演奏模式/编辑模式]
[💾 保存/▶️ 演奏] [🪄 曲谱优化] [未保存标记] .. [量化 ▾] [BPM ▾]
[最低映射 ▾] [最高映射 ▾] [绝对最低 □] [绝对最高 □] ..........
```

- 第一行用 `QHBoxLayout`：标题 + `addStretch()` + 模式按钮。
- 第二行：主按钮、曲谱优化、脏标记靠左；`addStretch()`；量化标签+下拉、BPM 标签+微调靠右。
- 第三行：四个字段依次排列，行尾 `addStretch()`。
- 标题字号 16px/600，分组之间使用 `spaceMD`。

### 2. 合并主按钮

- 删除独立的保存按钮；`self.play_btn` 成为唯一主按钮（保留属性名以兼容现有测试与代码），新增 `_update_primary_btn()`：

```python
def _update_primary_btn(self):
    play_mode = self.range_toggle_btn.isChecked()
    if play_mode:
        if self.is_playing:
            text, obj = "⏹️ 停止", "stopBtn"
            enabled = True
        else:
            text, obj = "▶️ 演奏", "primaryBtn"
            enabled = bool(self.current_midi_path)
    else:
        text, obj = "💾 保存", "primaryBtn"
        enabled = bool(self.piano_roll_dirty) and bool(self.current_midi_path)
    self.play_btn.setText(text)
    self.play_btn.setObjectName(obj)
    self.play_btn.setStyleSheet("")
    self.play_btn.setEnabled(enabled)
```

- 点击处理 `on_primary_action()`：演奏模式 → `toggle_play()`；编辑模式 → `save_piano_roll()`。
- `piano_save_btn` 不再保留独立控件；所有 `piano_save_btn.setEnabled(...)` 改为 `_update_primary_btn()`（历史恢复、列表刷新、加载、编辑后）。
- 播放/停止/完成回调里改文案的地方统一调用 `_update_primary_btn()`。
- 模式切换（`_sync_roll_mode`/`on_range_toggle_clicked`）后调用 `_update_primary_btn()`。

### 3. 纵向缩放

- 画布新增 `self._row_height = ROW_HEIGHT`（默认 10）与属性 `row_height`。
- `set_row_height(value, anchor_scene_y=None, anchor_viewport_y=None)`：
  - 夹紧到 `MIN_ROW_HEIGHT=6`、`MAX_ROW_HEIGHT=24`；
  - 记录锚点音高位置、更新场景高度/背景/音符几何/键盘，最后按新行高恢复锚点对应的纵向滚动。
- `wheelEvent`：`Shift` 时按滚轮方向缩放（1.25 倍），使用鼠标位置作为纵向锚点；`Ctrl` 仍为横向缩放；普通滚轮保持纵向滚动。
- 键盘组件改用 `canvas.row_height` 绘制，缩放后 `update()`。
- 缩放不触发 `notesChanged`，不影响数据与撤销。

### 4. 播放纵向聚焦

- 画布新增 `focus_vertical_range_center()`：取黄色音域框上下边界的中点场景 y，设置纵向滚动条使该点位于视口中心（夹紧到滚动范围）。
- 在 `set_playhead_locked(True)` 时调用一次；播放过程中不持续强制滚动，避免和用户手动滚动冲突。
- 停止（`set_playhead_locked(False)`）不改变滚动位置。

### 5. 亮/暗主题

- `app/ui/theme.py`：`DARK_TOKENS`、`LIGHT_TOKENS`，保留 `TOKENS = DARK_TOKENS` 兼容；`build_stylesheet(tokens)` 已支持传入。
- 浅色令牌：`colorBgBase #f5f5f5`、`colorBgContainer #ffffff`、`colorBgElevated #ffffff`、`colorBorder #d9d9d9`、`colorBorderSecondary #f0f0f0`、`colorText rgba(0,0,0,0.88)`、`colorTextSecondary rgba(0,0,0,0.65)`、`colorTextTertiary rgba(0,0,0,0.45)`、`colorTextDisabled rgba(0,0,0,0.25)`、`colorTextLightSolid #ffffff`。
- 主窗口：`self.theme_mode = "dark"`，`apply_theme(mode)` 设置 `self.setStyleSheet(build_stylesheet(tokens))` 并更新按钮；`toggle_theme()` 切换；只在内存中保存。
- 控制面板标题行新增 `self.theme_btn`（在置顶按钮左侧），文案表示「目标模式」：深色时显示「☀️ 亮色」，浅色时显示「🌙 深色」。
- 切换时对已显示的铺面画布保持语义色（音域框黄色），其余控件随 QSS 更新。

### 6. Ant Design 细化

```

Full source: docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/design.md

## docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/tasks.md

- Source: docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/tasks.md
- Lines: 1-34
- SHA256: 5f0a3fdde727671b2a3e60594a99c42ce0a9ec527f0fed6f4cbd392781f4acd4

```md
# Tasks

## 1. 工具栏三行与合并按钮

- [ ] 1.1 第一行改为标题 + 模式切换（右侧固定） <!-- comet-task:1f2eedd2-dbf8-4069-b28d-e8f685b2720c -->
- [ ] 1.2 第二行：合并主按钮与曲谱优化靠左，量化/BPM 靠右 <!-- comet-task:ef0a020a-6c8d-402d-9741-cd597bb3850a -->
- [ ] 1.3 第三行：最低映射、最高映射、绝对最低、绝对最高全部靠左 <!-- comet-task:0a9a3739-5229-42f7-8dda-f1b584ee3e26 -->
- [ ] 1.4 合并按钮：编辑模式保存、演奏模式播放/停止，文案与可用状态随模式更新 <!-- comet-task:4b0a1700-e465-4484-afd9-3d25678f7b58 -->
- [ ] 1.5 替换所有 `piano_save_btn` 引用并保持保存/播放行为不变 <!-- comet-task:fbbc64ab-beed-4b0f-bc51-511629f24a38 -->

## 2. 钢琴窗纵向缩放与聚焦

- [ ] 2.1 画布行高改为实例状态，提供夹紧的 `set_row_height` <!-- comet-task:35b82f42-c5ca-48ba-8645-69321bfcf6a5 -->
- [ ] 2.2 `Shift + 滚轮` 纵向缩放，以鼠标位置为锚点；不触发 `notesChanged` <!-- comet-task:a0993a60-cff8-4c80-b698-388257aa4935 -->
- [ ] 2.3 键盘与背景随行高重绘，场景高度同步 <!-- comet-task:8a43c5ec-c81c-477b-8057-63b625cdf34d -->
- [ ] 2.4 播放开始时黄框纵向居中 <!-- comet-task:6118deed-755b-4e8c-94e8-59fe76499a29 -->
- [ ] 2.5 左侧键盘固定回归测试 <!-- comet-task:41119a85-2be9-4f5e-9063-3fb9d45f71fc -->

## 3. 亮暗主题

- [ ] 3.1 主题模块提供深色/浅色两套令牌 <!-- comet-task:2067332f-6c46-4bce-a4fd-155466621e98 -->
- [ ] 3.2 控制面板新增主题切换按钮，切换整站样式并更新文案 <!-- comet-task:00e4aa1b-57bb-4a45-a92f-07511c652af8 -->
- [ ] 3.3 会话内记忆；重启回到深色 <!-- comet-task:0ebad794-4c09-4eaa-a91c-d5000dfdbfc7 -->

## 4. Ant Design 细化

- [ ] 4.1 标题/分组/辅助文字层级与间距统一 <!-- comet-task:28cf8611-c0c8-4e87-b85a-fae8ba5dba1e -->
- [ ] 4.2 主按钮、危险按钮与状态色在两套主题下一致 <!-- comet-task:f9b2b823-3672-4a81-abde-293c90ad04d1 -->

## 5. 验证

- [ ] 5.1 更新工具栏布局与按钮状态测试，新增缩放/聚焦/主题测试 <!-- comet-task:5f8f1e15-355b-4ae1-a404-c01a7b34f743 -->
- [ ] 5.2 `.venv\Scripts\python.exe -m unittest discover -s tests -v` 全部通过 <!-- comet-task:b31ecc88-7c44-4623-ba12-4ad0ff4c6e17 -->
- [ ] 5.3 offscreen 截图核对深/浅两套界面；重新打包 exe 并启动冒烟 <!-- comet-task:07fc9dae-4f7f-4970-aa71-2ed504bb4a13 -->

```

## docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/.openspec.yaml

- Source: docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/.openspec.yaml
- Lines: 1-2
- SHA256: 2e91af4681be83038a92e715cfb64d8067b4c8399c2b25074da27a778869f3aa

```md
schema: spec-driven
created: 2026-11-14

```

## docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/specs/piano-roll-view/spec.md

- Source: docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/specs/piano-roll-view/spec.md
- Lines: 1-48
- SHA256: b0785dfaffc009026bb5dddb1b438e4ecedd3a0013946525c29f391731a22cd2

```md
# Spec Delta：钢琴窗视图

## Purpose

让钢琴窗可以按需纵向缩放，并保证播放时键盘与音域焦点保持可见。

## ADDED Requirements

### Requirement: 纵向缩放

钢琴窗 SHALL 支持 `Shift + 鼠标滚轮` 调整纵向行高：

- 行高范围约 6–24px，缩放步长约 1.25 倍；
- 以鼠标所在音高为锚点：缩放前后该音高在视口中的纵向位置保持不变；
- 不改变横向缩放、播放线位置或音符数据。

#### Scenario: 放大行高

- **WHEN** 光标停在 C4 附近并向上滚动 `Shift + 滚轮`
- **THEN** 行高变大，C4 仍在光标附近，音符数据不变

#### Scenario: 缩小到下限

- **WHEN** 连续向下滚动 `Shift + 滚轮`
- **THEN** 行高停在约 6px，不再继续缩小

### Requirement: 左侧键盘固定

水平滚动铺面时，左侧钢琴键盘 SHALL 始终贴住视口左侧，并保持与当前音高行对齐。

#### Scenario: 横向滚动

- **WHEN** 把铺面横向滚动到任意位置
- **THEN** 左侧键盘仍然可见且贴左，键位与行高对应

### Requirement: 播放纵向聚焦音域框

播放进行中 SHALL 自动调整纵向滚动，使黄色音域框的纵向中心位于视口中心；未播放或用户手动调整时 MUST NOT 强制滚动。

#### Scenario: 播放时音域框居中

- **WHEN** 从曲中开始播放
- **THEN** 黄色音域框的纵向中心与视口纵向中心重合

#### Scenario: 停止后不再强制

- **WHEN** 播放停止
- **THEN** 纵向滚动位置保持不变，不再自动调整

```

## docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/specs/piano-toolbar/spec.md

- Source: docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/specs/piano-toolbar/spec.md
- Lines: 1-55
- SHA256: 528537db09534ac3dc1b059dd754e8f3df18a186202a641a307d59e8ae407a93

```md
# Spec Delta：铺面工具栏

## Purpose

让铺面编辑页的操作按使用频率分层排列，并让保存与播放共用一个主按钮。

## ADDED Requirements

### Requirement: 工具栏三行布局

铺面编辑页 SHALL 使用三行布局：

- 第一行：`🎼 铺面编辑` 标题与「演奏模式 / 编辑模式」切换按钮，切换按钮 MUST 固定在行的右侧（标题靠左、中间留白吸收多余宽度）。
- 第二行：合并后的主按钮与「曲谱优化」靠左；「量化」与「BPM」靠右（两者紧邻右边缘，中间留白）。
- 第三行：演奏最低键位映射、演奏最高键位映射、钢琴音域绝对最低键、钢琴音域绝对最高键，按此顺序全部靠左。

#### Scenario: 第一行右侧固定

- **WHEN** 主窗口变宽
- **THEN** 「🎼 铺面编辑」保持在左边缘，「演奏模式 / 编辑模式」保持在右边缘，两者之间距离随窗口增大

#### Scenario: 第二行左右分组

- **WHEN** 查看第二行
- **THEN** 主按钮与曲谱优化紧靠左边缘，量化与 BPM 紧靠右边缘

#### Scenario: 第三行全部靠左

- **WHEN** 查看第三行
- **THEN** 四个键位/音域字段从左到右依次排列，右侧没有前置控件

### Requirement: 保存与演奏合并为一个主按钮

主按钮 SHALL 根据当前模式与播放状态显示并执行：

- 编辑模式：显示「💾 保存」，点击保存铺面；
- 演奏模式且未播放：显示「▶️ 演奏」，点击开始播放；
- 演奏模式且播放中：显示「⏹️ 停止」，点击停止播放。

编辑模式下 MUST NOT 通过该按钮开始播放。按钮的可用状态 SHALL 与当前模式匹配（编辑模式跟随未保存状态，演奏模式跟随曲目是否可播放）。

#### Scenario: 编辑模式保存

- **WHEN** 在编辑模式修改音符后点击主按钮
- **THEN** 铺面保存，按钮文字仍为「💾 保存」

#### Scenario: 演奏模式播放与停止

- **WHEN** 切到演奏模式后点击主按钮
- **THEN** 开始播放且按钮变为「⏹️ 停止」；再次点击停止并恢复「▶️ 演奏」

#### Scenario: 切换模式更新文案

- **WHEN** 在编辑与演奏模式之间切换
- **THEN** 主按钮在「💾 保存」与「▶️ 演奏」之间同步变化

```

## docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/specs/ui-design-system/spec.md

- Source: docs/openspec/changes/piano-toolbar-zoom-and-theme-modes/specs/ui-design-system/spec.md
- Lines: 1-40
- SHA256: 4d869f7cbad33c3b4c1c5d483189c53dbac54398e11cd893ea260df1f4073cda

```md
# Spec Delta：界面主题

## Purpose

在现有 antd 深色令牌之上增加浅色令牌与切换按钮，并进一步统一界面层次。

## ADDED Requirements

### Requirement: 亮/暗主题切换

控制面板 SHALL 提供一个主题切换按钮；点击后整个界面在 antd 深色与 antd 浅色令牌之间切换，且只在本次运行内记住选择（重启回到深色）。

- 深色令牌：页面 `#141414`、容器 `#1f1f1f`、边框 `#424242`、主文字 `rgba(255,255,255,0.85)`；
- 浅色令牌：页面 `#f5f5f5`、容器 `#ffffff`、边框 `#d9d9d9`、主文字 `rgba(0,0,0,0.88)`；
- 两套主题共用主色 `#1677ff` 与同一套间距、圆角、字号、控件高度；
- 切换 MUST 更新所有已显示页面（铺面页、播放列表、操作日志、弹窗与菜单）。

#### Scenario: 切到浅色

- **WHEN** 在控制面板点击「亮色」按钮
- **THEN** 所有页面背景变亮、文字变深，主色与控件尺寸保持不变

#### Scenario: 切回深色

- **WHEN** 再次点击该按钮
- **THEN** 界面恢复深色令牌

#### Scenario: 重启恢复默认

- **WHEN** 切到浅色后重启程序
- **THEN** 界面回到深色（会话内记忆）

### Requirement: Ant Design 层次细化

铺面编辑页 SHALL 使用 antd 的层次规则：页面标题 16px/600、分组标题 14px/600、辅助文字 12px/次要色；控件统一 32px 高、6px 圆角；主按钮使用主色、危险操作使用错误色。

#### Scenario: 标题层级

- **WHEN** 查看铺面编辑页
- **THEN** 「🎼 铺面编辑」比其他标签文字更醒目，工具栏分组之间留白一致

```
