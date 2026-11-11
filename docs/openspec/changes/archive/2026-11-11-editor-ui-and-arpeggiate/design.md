---
comet_change: editor-ui-and-arpeggiate
role: technical-design
canonical_spec: openspec
archived-with: 2026-11-11-editor-ui-and-arpeggiate
status: final
---

# Design

行为需求以 `specs/piano-roll-arpeggiate`、`specs/piano-roll-toolbar-layout` 以及两份 MODIFIED spec 为准。

## Context

- 工具栏目前是单行 `QHBoxLayout`，控件拥挤；BPM 使用 `QDoubleSpinBox` 默认浅色样式。
- 播放列表使用 `QListWidget`，删除按钮在列表右侧；`refresh_play_list` 重建条目。
- 演奏/编辑模式由 `_sync_roll_mode()` 统一同步；`play_btn` 目前始终可用。
- 映射下拉框来自 `get_natural_key_ladder()`，标签含 Z/A/J/7；`_pitch_for_label` 找不到时回退到最低音高。
- 黄框范围由 `set_instrument_range(low, high)` 控制，当前默认取自映射下拉框。
- `release/谱子/arpeggiate.py` 是文件级 MIDI 琶音脚本，逻辑可直接移植为内存函数。

## Decisions

### 1. 新增 `arpeggiate.py`（内存版）

```python
MIN_NOTE_DURATION = 0.05

def arpeggiate_notes(notes, selected_ids, seconds_per_beat):
    """对选中音符按 1/32 拍窗口与步长展开琶音，返回新列表。"""
```

- `window = step = seconds_per_beat / 32`。
- 选中音符按 `start` 排序；以组内第一个为锚点，`start < anchor + window` 归入同组；级联规则与脚本一致（`start < anchor + (count)*step`）。
- 组内按 `pitch` 升序，第 k 个音符 `start = anchor + k*step`。
- 时长保持不变：只修改起始时间，结束时间随之后移；不改音高。极短音符（<0.05s）同样只后移，不做时长补足。
- 未选中音符原样返回副本；不修改输入。

### 2. 画布接口与按钮

- `_PianoRollCanvas.arpeggiate_selected(seconds_per_beat)`：调用上述函数、替换 `_notes`、更新图元与场景宽度、`notesChanged`。
- `PianoRollWidget` 透传。
- GUI 在工具栏上方新增一行，放「🪄 曲谱优化」按钮；点击时若 `selected_ids` 为空则写日志提示并返回，否则按当前 `seconds_per_beat = (60/BPM)*(4/分母)` 调用。
- 按钮启用条件：编辑模式（非只读）；播放中自动禁用。每次点击后由 `notesChanged` 触发未保存标记。

### 3. 弹奏按钮与模式绑定

- `_sync_roll_mode()` 追加：`self.play_btn.setEnabled(play_mode or self.is_playing)`。
- 播放中保持可用（文本为「停止」）；停止后按当前模式恢复。

### 4. 播放列表逐行删除

- `refresh_play_list` 为每个条目 `setItemWidget(item, row_widget)`：`QLabel(名称)` + `QPushButton("🗑")`，按钮回调 `on_delete_play_item(item)`。
- 删除按钮改为接收条目参数；`on_delete_play_item` 不再读取 `currentItem`（保留兼容：无参数时取当前项）。
- 移除原列表右侧删除按钮；`play_delete_btn` 相关启用逻辑删除。
- 条目仍保存路径与原始文件名到 `Qt.UserRole`、`Qt.UserRole + 1`，选中恢复逻辑不变。

### 5. 工具栏两行与文案

- `_setup_piano_roll_tab` 改为 `QVBoxLayout`：
  - 顶部动作行：`🪄 曲谱优化`
  - 第一行：标题、未保存、弹奏、保存、模式、最低映射、最高映射
  - 第二行：绝对最低键、绝对最高键、量化、BPM
- 文案按 spec 更新；`QLabel("…:")` 的冒号统一为中文全角。

### 6. 样式

- 为 `QDoubleSpinBox` 增加与 `QComboBox` 相同的 `background/border/color/padding` 规则（含 `:focus`、`::up-button`、`::down-button` 的简化处理）。
- 统一按钮 `padding: 2px 10px`，保持上一轮高度。
- 新按钮加 tooltip：「对选中音符做琶音整理（1/32 拍展开）」。

### 7. 默认值

- `_populate_range_combos` 与 `_reset_instrument_range`：映射默认 Z（36）与 7（83）。
- 黄框默认范围：`set_instrument_range(36, 47)`（C2～B2），与映射下拉框解耦；切换曲目时同样重置为该范围。
- 保持 `_refresh_range_display` 显示当前框体的绝对键名。

## Risks / Trade-offs

- **琶音只能作用于选中**：未选中时按钮无效果并提示；符合需求但可能被误认为无响应。→ 日志提示明确。
- **逐行删除误触**：每行都有按钮，点错会隐藏该曲目；保留确认框，且磁盘文件不删、可一键恢复。
- **黄框默认与映射解耦**：播放时的音域筛选由黄色框（`get_instrument_range()`，默认 C2～B2）决定；映射下拉框只决定移调锚点与目标最低键。两者含义不同，文档与提示中需说明。
- **两行布局在窄窗口下**：仍可能挤压；允许窗口变窄时控件收缩，必要时后续加滚动区。
- **1/32 拍在极慢 BPM 下步长较大**：按公式计算，不做额外限制。

## Test Strategy

- `tests/test_arpeggiate.py`：三音和弦展开、单音不变、两组独立、结束时间不变、时过短钳制、未选中不变、输入不被修改。
- `tests/test_piano_roll_ui.py` / GUI 测试：画布 `arpeggiate_selected` 的结果与未保存信号；编辑模式弹奏禁用、演奏模式启用。
- UI 手动验收：文案、两行布局、BPM 深色样式、默认 Z/7、黄框 C2–B2、每行删除、曲谱优化按钮。
- 回归：既有 114 项测试。

## Migration Plan

无数据迁移；新增 `arpeggiate.py` 为源码文件。

## Open Questions

无。
