# 验收记录：piano-roll-editing-playback-tools

## 环境

- Windows + Python 3.14 + PyQt5（UI 测试使用 `QT_QPA_PLATFORM=offscreen`，并真实 `show()` 组件）
- 测试命令：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 最近一次结果：`Ran 51 tests ... OK`（既有 C6 边界用例 6 个 + 本 change 新增 45 个）

## 自动化覆盖

| 规格场景 | 覆盖测试 |
| --- | --- |
| 复制多个音符 / 快照不被后续编辑影响 | `test_note_clipboard.PastedStartsTest.test_does_not_mutate_input`、`test_piano_roll_ui.test_cut_removes_notes_and_keeps_clipboard` |
| 无选中时复制、空剪贴板粘贴无副作用 | `test_piano_roll_ui.test_paste_with_empty_clipboard_is_noop`、`test_keyboard_copy_and_paste_emit_notes_changed` |
| 剪切后原音符消失、可粘贴回来 | `test_piano_roll_ui.test_cut_removes_notes_and_keeps_clipboard`、`test_keyboard_cut_removes_selection` |
| 在播放辅助线处粘贴、相对时距保持、新音符成为选中集 | `test_piano_roll_ui.test_paste_lands_on_playhead_anchor` |
| 连续粘贴互不影响 | 同上的多次粘贴路径（`pasted_starts` 基准计算） |
| 八度移动、部分越界跳过、无选中不动 | `test_note_clipboard.OctaveShiftTest`（5 例）、`test_piano_roll_ui.test_octave_shift_*`、`test_octave_shift_with_empty_selection_does_nothing`、`test_keyboard_shift_up_moves_octave` |
| 键盘快捷键接线（Ctrl+C/X/V、Shift+↑/↓、只读忽略） | `test_piano_roll_ui.test_keyboard_*`、`test_read_only_canvas_ignores_paste_and_octave` |
| 播放起点过滤、恰好落在辅助线、跨线音符不重触发、空结果 | `test_playback_start.PlaybackNotesFromPositionTest`（6 例） |
| 播放起点落在休止符时的辅助线起点补偿 | `test_playback_start.FirstPlayableStartTest`（3 例） |
| 缩放比例夹紧、锚点时间不漂移（中途 / 末尾 / 真实滚轮事件） | `test_zoom_math.ZoomMathTest`（5 例）、`test_piano_roll_ui.test_wheel_zoom_keeps_anchor_*`、`test_zoom_is_clamped` |
| 场景比视口窄时视口↔时间映射仍正确（标尺对齐） | `test_viewport_mapping_matches_scene_when_zoomed_out`、`test_ruler_tick_stays_aligned_when_scene_is_narrow` |
| 纯横向滚轮不会误触发缩放 | `test_horizontal_wheel_with_shift_does_not_zoom_out` |
| 播放辅助线默认 0 秒、常驻、停止后回落到锚点 | `test_piano_roll_ui.test_playhead_defaults_to_zero`、`test_stopping_playback_falls_back_to_anchor` |
| 点击标尺定位、播放中忽略标尺 | `test_piano_roll_ui.test_ruler_click_sets_playhead_anchor`、`test_ruler_ignored_while_playing` |
| 切换曲目后辅助线归零 | `test_piano_roll_ui.test_switching_notes_resets_playhead_anchor` |
| 按钮空闲文案「弹奏」、播放中「停止(ESC)」 | 代码核对 `gui.py`（初始化 / `stop_playing` / `on_play_finished`），无自动化 UI 断言 |

## 独立审查结论

最终集成审查（review_mode: standard）覆盖 `5c2774d..3c963a5` 全量 diff，结论为「With fixes」。已修复项：

1. **Critical：视口↔时间换算依赖算术近似。** 场景比视口窄时 `QGraphicsView` 默认居中，导致标尺错位、点击定位偏移、缩放锚点算错。已改为 `mapToScene` / `mapFromScene` 映射，并在画布上设置 `AlignLeft | AlignTop`；标尺以画布边框为原点并按视口宽度裁切。
2. **Critical：缩放先设滚动值、后扩展场景范围。** 旧上限会夹紧滚动值，时间轴末段缩放会跳动最多一个视口。已改为先重排再设滚动值，并用真实 `QWheelEvent` 在中段与末尾回归验证。
3. **Important：起点落在休止符时辅助线整体落后于发声。** 播放数据会省略前导静音，已用 `first_playable_start` 把显示起点补偿到第一个可发声音符。
4. **Important：缩放测试未覆盖真实滚轮路径、键盘接线无测试。** 已补真实滚轮事件测试、`QTest.keyClick` 键盘测试与 `notesChanged` 断言。

接受的偏差（Minor，未在本次处理）：

- 标尺右侧 14px 与纵向滚动条重叠：已按视口宽度裁切刻度与点击范围，视觉上不再出现可点击刻度，但标尺控件本身仍与滚动条等宽。
- 标尺上不额外绘制播放辅助线标记（规格未要求；辅助线在画布内可见）。
- `set_pixels_per_second` 是程序化 1:1 设置接口，不做锚定；滚轮缩放走 `wheelEvent`。

## 仍需人工确认（视觉 / 音频）

- 标尺小节序号与小节线在水平滚动、缩放、改变窗口宽度后的逐像素观感（自动化只校验了坐标换算与刻度位置）。
- 真实发声：把辅助线放到 10s 点「弹奏」，确认首个音立即发声且辅助线落在该音上；播放中点击标尺不打断播放。
- 按钮三态文案与样式（`playBtn` / `stopBtn`）。
- 曲尾提示「当前位置之后没有可播放的音符」的实际弹出。

## 结论

三份 delta spec 中的行为均有实现与自动化覆盖；独立审查提出的 2 个 Critical 与 2 个 Important 已修复并有回归测试。上述 4 项视觉/音频检查需人工过一遍后才算最终交付确认。
