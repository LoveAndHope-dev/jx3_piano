# Tasks

## 1. 琶音算法

- [x] 1.1 新增 `arpeggiate.py`：`arpeggiate_notes(notes, selected_ids, seconds_per_beat)`，窗口/步长 = 1/32 拍，组内按音高展开，结束时间不变、过短钳制；新增 `tests/test_arpeggiate.py` 覆盖和弦展开、单音、两组独立、未选中不变、输入不变 <!-- comet-task:eadc5b36-ba7a-484e-92fa-53164fcd0e33 -->

## 2. 曲谱优化入口

- [x] 2.1 `_PianoRollCanvas.arpeggiate_selected(seconds_per_beat)` + `PianoRollWidget` 透传：替换音符、重排图元、扩展场景、发出 `notesChanged` <!-- comet-task:827e3343-c915-4100-b031-3ccb1ef50a93 -->
- [x] 2.2 工具栏上方新增「🪄 曲谱优化」按钮（含 tooltip）：无选中时日志提示；有选中时按当前 BPM/拍号计算拍长并调用；编辑模式可用、播放中禁用 <!-- comet-task:caeb6de3-d649-4ea6-8ebf-7ea74d950f64 -->

## 3. 弹奏按钮与模式

- [x] 3.1 `_sync_roll_mode` 增加弹奏按钮启用规则：编辑模式禁用、演奏模式启用、播放中保持可用；验证切模式与播放开始/停止 <!-- comet-task:42758c54-40a2-4003-b6b5-b17f697bebfa -->

## 4. 播放列表逐行删除

- [x] 4.1 `refresh_play_list` 改为每行 `QLabel + 🗑` 的 item widget，删除按钮定位到该行曲目；移除列表右侧删除按钮及其启用逻辑 <!-- comet-task:fb4a70cb-dee4-4f9b-bf29-9ec4ba98cf4e -->
- [x] 4.2 验证逐行删除：删除未加载/当前曲目、取消、刷新后仍隐藏、恢复全部 <!-- comet-task:d5db9f7f-2e68-464d-9660-966c13271a46 -->

## 5. 工具栏文案、两行布局、样式与默认值

- [x] 5.1 文案改为「演奏最低键位映射 / 演奏最高键位映射 / 钢琴音域绝对最低键 / 钢琴音域绝对最高键」 <!-- comet-task:6f18ef00-6814-4f90-9d4e-9ffb02afeacc -->
- [x] 5.2 工具栏拆两行：第一行到「演奏最高键位映射」，第二行放绝对键、量化、BPM；统一间距与高度 <!-- comet-task:a7516f85-2992-4690-831d-1dca2f70107a -->
- [x] 5.3 `QDoubleSpinBox` 增加与下拉框一致的深色 QSS（背景、边框、圆角、文字、focus） <!-- comet-task:49702f21-e44b-4187-8ba7-141143bf7541 -->
- [x] 5.4 默认映射改为 Z（36）/7（83）；黄框默认范围改为 C2～B2（36～47），切换曲目时同样重置 <!-- comet-task:e27f562d-415f-4a0c-b20f-0ed693d883d4 -->

## 6. 交互 UI 统一

- [x] 6.1 检查按钮 padding、控件间距、标签冒号与 tooltip 一致性；新按钮不遮挡既有控件 <!-- comet-task:36395a90-2c1f-494c-ad39-2025acbb794a -->
- [x] 6.2 手动走查：两行布局、BPM 样式、默认映射与黄框、逐行删除、曲谱优化、编辑模式弹奏禁用 <!-- comet-task:c34eac44-a038-47a1-9174-b80c706f7ad2 -->

## 7. 集成验证

- [x] 7.1 `.venv\Scripts\python.exe -m unittest discover -s tests -v`：既有 114 项 + 新增全部通过 <!-- comet-task:7c7aca3f-ffc5-433e-9d68-07318fec5e12 -->
- [x] 7.2 记录验收结果到 `docs/superpowers/reports/2026-11-11-editor-ui-and-arpeggiate-verification.md` <!-- comet-task:82ead7d3-8484-41da-9ae1-f0aa552d6a06 -->

## Workflow follow-up

- 完成 Verify 后按 Comet 交付流程归档或交付，具体方式由用户确认。
