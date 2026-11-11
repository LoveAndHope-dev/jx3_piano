# 验收记录：piano-roll-modes-and-daw-editing

## 环境

- Windows + Python 3.14 + PyQt5
- 测试命令：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 最近一次结果：`Ran 114 tests ... OK`（上一轮 99 项 + 本轮 15 项）

## 独立审查后的修复

最终集成审查（review_mode: standard）覆盖 `515d96f..7b7fba4`，结论「With fixes」。已修复项：

1. **Critical：停止播放/播放结束后演奏模式被解锁。** 新增 `_sync_roll_mode()`（勾选、文案、映射框、只读四处原子同步），停止、播放结束、开始播放、切换曲目、删除当前曲目全部走同一入口。
2. **Critical：演奏模式下切换曲目会卡在只读。** `_load_piano_roll` 在 `_reset_instrument_range()` 之后统一调用 `_sync_roll_mode()`，模式重置与只读状态一致。
3. **Important：演奏模式下黄色映射框无法拖动。** 只读时若按在可见音域框内，仍允许 `range` 拖动；音符编辑依旧全部拒绝。
4. **Important：边界移调破坏音程。** `_transpose_selected` 改为整组判断：任一音符会越界则整组不动；八度移动按既有需求保持逐音符跳过。
5. **Important：测试缺口。** 只读测试改为先选中音符并断言 Delete/Ctrl+V 无效；新增 Shift+滚轮不缩放、左边缘拖过结尾保留最小时长、无选中方向键无信号、整组平移保持间距、边界移调整组不动；GUI 集成测试覆盖「停止后仍锁定」与「切换曲目恢复编辑模式」。
6. **Minor：** 更新模块文档说明；`_clear_piano_roll_cache` 先取消勾选再同步模式。

## 自动化覆盖

| 能力 | 覆盖测试 |
| --- | --- |
| 单击空白清空选择且不新建 | `test_piano_roll_ui.test_click_empty_clears_selection_without_creating` |
| 双击空白新建并选中 | `test_double_click_empty_creates_note` |
| 拖动空白框选不新建 | `test_drag_empty_marquee_selects_without_creating` |
| 左边缘调整起始时间、结束时间不变 | `test_drag_left_edge_trims_start_and_keeps_end` |
| 方向键按量化步长移动、半音/八度移调 | `test_arrow_keys_nudge_and_transpose`、既有 `test_keyboard_shift_up_moves_octave` |
| Ctrl+滚轮缩放、Ctrl 横向滚轮不缩放 | `test_wheel_zoom_keeps_anchor_*`、`test_horizontal_wheel_with_shift_does_not_zoom_out`（改用 Ctrl） |
| 只读（演奏模式）阻止编辑但标尺仍可定位 | `test_read_only_blocks_editing_but_ruler_still_seeks` |
| 播放锁定标尺 | `test_playhead_lock_ignores_ruler`、`test_ruler_ignored_while_playing` |
| 模式切换按钮与只读联动 | `test_playlist_gui.test_mode_toggle_locks_roll` |

## 仍需人工确认（真实窗口）

- 「🎹 演奏模式 / ✏️ 编辑模式」文案与黄框显隐；演奏模式下铺面不可编辑、工具栏与标尺可用。
- 播放中切换模式仍保持只读，停止后按模式恢复。
- 按钮高度与下拉框一致、页脚显示 `created by 66maer updated by Loveanope_Dev`。
- 双击/拖动/左边缘在真实鼠标下的手感。

## 结论

模式切换、DAW 基础编辑、Ctrl 缩放与锁定逻辑均有 offscreen UI 测试覆盖；剩余为真实窗口观感与手感确认。
