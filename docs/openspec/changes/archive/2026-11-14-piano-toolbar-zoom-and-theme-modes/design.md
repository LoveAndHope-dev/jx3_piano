---
comet_change: piano-toolbar-zoom-and-theme-modes
role: technical-design
canonical_spec: openspec
archived-with: 2026-11-14-piano-toolbar-zoom-and-theme-modes
status: final
---

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

- 标题 16px/600；分组标签 14px；辅助文字 12px 次要色。
- 新增 `:pressed`/`:disabled` 已覆盖；浅色主题使用相同的状态派生逻辑。

## Risks / Trade-offs

- **合并按钮改变播放入口**：编辑模式不再直接播放，需先切到演奏模式；这是用户确认的行为。
- **测试修改**：现有测试以 `play_btn` 判断可用性、位置与文案，需要按新模式更新；`piano_save_btn` 不再存在，内部引用一并替换。
- **行高可变**：画布场景高度、键盘绘制、背景重建都依赖行高，需要统一走 `canvas.row_height`，避免尺寸错位。
- **纵向聚焦只在播放开始时执行**：持续强制会妨碍用户查看其他音域；若用户希望持续居中，可后续增加开关。
- **浅色主题对比度**：铺面画布仍为深色语义，需要检查黄框与音符在浅色界面下的可读性。

## Test Strategy

- 工具栏：三行结构与左右分组、第一行右侧固定、主按钮文案/可用状态随模式与脏标记变化、编辑模式点击调用保存。
- 纵向缩放：`set_row_height` 夹紧范围、Shift+滚轮缩放、鼠标锚点保持、缩放不触发 `notesChanged`。
- 纵向聚焦：`set_playhead_locked(True)` 后音域框中心对齐视口中心；停止后滚动不变。
- 键盘固定：水平滚动后键盘控件几何不变。
- 主题：浅色/深色令牌切换、切换后按钮文案、QSS 更新。
- 既有 200 项回归。
