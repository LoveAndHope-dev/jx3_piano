# Design

## Context

见 proposal.md - Why。涉及 `gui.py` 中 `_setup_piano_roll_tab` 构建的两行工具栏（`toolbar` + `range_toolbar`），以及 `piano_roll.py` 中 `PianoRollWidget`/`_PianoRollCanvas` 已有的 `get_instrument_range()` 方法和 `instrumentRangeChanged` 信号（此前未被连接）。

## Goals / Non-Goals

**Goals:**
- 新增两个只读字段展示音域框当前真实的最低/最高键标签，来源统一为 `piano_roll.get_instrument_range()`，不单独维护一份状态。
- 把两行工具栏合并为一行。

**Non-Goals:**
- 不改变音域框拖动、下拉框联动跨度计算等既有行为逻辑。
- 不让只读字段反向驱动下拉框选中项（只做单向展示）。

## Decisions

- **只读字段取值来源**：统一通过一个 `_refresh_range_display()` 方法读取 `self.piano_roll.get_instrument_range()` 并换算为音名；在 `_reset_instrument_range`、`on_range_low_combo_changed`、`on_range_high_combo_changed` 末尾调用，并把 `piano_roll.instrumentRangeChanged` 信号连接到同一方法。理由：这三处是当前所有会改变音域框实际边界的入口，统一走一个刷新函数避免显示状态和框体状态分叉。
- **只读字段控件类型**：使用 `QLineEdit` 并 `setReadOnly(True)`，而不是 `QLabel`。理由：视觉上与旁边的下拉框保持一致的「字段」外观，且 `QLineEdit.setReadOnly` 比用 `QLabel` 更明确地表达「本应是输入控件但当前不可编辑」的语义。
- **音名换算**：新增 `_note_name_for_pitch(pitch)`，复用已有的 `MidiToKeysConverter.get_note_name(pitch)`（项目里调试日志等场景已用它把 MIDI 音高换算成标准音名），不单独维护第二份音高/音名映射表。**不**复用 `self.key_ladder`/`_pitch_for_label`：那套标签是「最低映射/最高映射」下拉框专用的游戏按键字母（如 `A`、`J`），与用户想看到的标准钢琴音名（如 `C4`）是两套不同的命名体系。
- **单行布局**：直接把 `range_toolbar` 的全部 `addWidget` 调用迁移进原 `toolbar`（同一个 `QHBoxLayout`），删除 `range_toolbar` 这个布局对象本身；控件先后顺序沿用两行时的相对顺序（标题 → stretch → 未保存提示 → 播放 → 保存 → 显示映射 → 最低映射 → 最高映射 → 当前最低键 → 当前最高键 → 量化），不引入 `QFormLayout` 或额外的分组容器。

## Risks / Trade-offs

- [合并为一行后，控件总数变多，窄窗口下可能需要横向滚动或遮挡] → 这是用户明确要求的布局改动，范围内不额外处理响应式换行；如果后续需要可另起改动处理。
- [只读字段与下拉框显示的值可能不同（设计目的）] → 在两个只读字段的标签前缀中明确写「当前最低键/当前最高键」，与下拉框的「最低映射/最高映射」措辞区分，避免用户误以为是同一个值重复展示。
