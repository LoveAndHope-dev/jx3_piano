# 验收记录：piano-roll-editing-playback-tools

## 环境

- Windows + Python 3.14 + PyQt5（UI 测试使用 `QT_QPA_PLATFORM=offscreen`）
- 测试命令：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 最近一次结果：`Ran 39 tests ... OK`（既有 C6 边界用例 6 个 + 新增 33 个）

## 自动化覆盖

| 规格场景 | 覆盖测试 |
| --- | --- |
| 复制多个音符 / 快照不被后续编辑影响 | `test_note_clipboard.PastedStartsTest.test_does_not_mutate_input`、`test_piano_roll_ui.test_cut_removes_notes_and_keeps_clipboard` |
| 无选中时复制、空剪贴板粘贴无副作用 | `test_piano_roll_ui.test_paste_with_empty_clipboard_is_noop` |
| 剪切后原音符消失、可粘贴回来 | `test_piano_roll_ui.test_cut_removes_notes_and_keeps_clipboard` |
| 在播放辅助线处粘贴、相对时距保持、新音符成为选中集 | `test_piano_roll_ui.test_paste_lands_on_playhead_anchor` |
| 连续粘贴互不影响 | 同上的多次粘贴路径（`pasted_starts` 基准计算） |
| 八度移动、部分越界跳过、无选中不动 | `test_note_clipboard.OctaveShiftTest`（5 例）、`test_piano_roll_ui.test_octave_shift_*` |
| 播放起点过滤、恰好落在辅助线、跨线音符不重触发、空结果 | `test_playback_start.PlaybackNotesFromPositionTest`（6 例） |
| 缩放比例夹紧、锚点时间不漂移 | `test_zoom_math.ZoomMathTest`（5 例）、`test_piano_roll_ui.test_zoom_keeps_anchor_time_under_cursor`、`test_zoom_is_clamped` |
| 播放辅助线默认 0 秒、常驻、停止后回落到锚点 | `test_piano_roll_ui.test_playhead_defaults_to_zero`、`test_stopping_playback_falls_back_to_anchor` |
| 点击标尺定位、播放中忽略标尺 | `test_piano_roll_ui.test_ruler_click_sets_playhead_anchor`、`test_ruler_ignored_while_playing` |
| 切换曲目后辅助线归零 | `test_piano_roll_ui.test_switching_notes_resets_playhead_anchor` |
| 按钮空闲文案「弹奏」、播放中「停止(ESC)」 | 代码核对 `gui.py`（初始化 / `stop_playing` / `on_play_finished`），无自动化 UI 断言 |

## 仍需人工确认（视觉 / 音频）

以下项目依赖真实窗口渲染与实际发声，未在本机自动化：

1. 顶部标尺的小节序号与小节线在水平滚动、缩放、改变窗口宽度后是否逐像素对齐（纵向滚动时标尺不动）。
2. Shift+滚轮的实际缩放手感，以及缩放后拖动音符、调整时长、开启量化后落点仍准确。
3. 实际点击「弹奏」从播放辅助线位置发声、辅助线随进度移动；播放中点击标尺不打断播放。
4. 按钮三态文案与样式（`playBtn` / `stopBtn`）在真实窗口中正常。
5. 提示文案「当前位置之后没有可播放的音符」在辅助线位于曲尾时的实际弹出。

## 结论

代码与自动化测试已满足三份 delta spec 的行为约定；上述 5 项视觉/音频检查在 Verify 阶段由人工过一遍后即可确认交付。
