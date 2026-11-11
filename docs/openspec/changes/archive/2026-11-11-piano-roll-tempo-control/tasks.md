# Tasks

## 1. 纯逻辑与测试

- [x] 1.1 在 `piano_roll.py` 新增 `bpm_scale_factor(old_bpm: float, new_bpm: float) -> float` 与 `tempo_us_from_bpm(bpm: float) -> int`，非法 BPM（<=0）抛 `ValueError`；新增 `tests/test_tempo.py` 覆盖 120→60、60→120、同值、非法输入，运行通过 <!-- comet-task:2696a302-cadb-4871-b3b8-70d50e82978f -->
- [x] 1.2 新增 `scaled_note_times(notes: List[Dict], factor: float) -> List[Dict]`：返回深拷贝且 `start`/`duration` 乘 factor，不改输入；补充升速、降速、连续缩放可逆（1e-6）的断言并运行通过 <!-- comet-task:69ff741b-153d-4819-ad13-aeb75eedf877 -->

## 2. 画布时间缩放

- [x] 2.1 在 `_PianoRollCanvas` 新增 `rescale_times(factor: float) -> None`：缩放全部音符 `start`/`duration` 与播放辅助线锚点/显示位置（钳制 >=0），重排图元、扩展场景宽度并发出 `notesChanged`；`PianoRollWidget` 透传；用 `tests/test_piano_roll_ui.py` 断言音符与锚点按比例变化 <!-- comet-task:19d6d18f-9c09-4c8e-809a-f48bcc44094c -->
- [x] 2.2 验证连续缩放可逆：UI 测试中 1.0→0.75→1.25→1.0 后音符时间与初始一致（1e-6 容差） <!-- comet-task:45bf94ad-b7cb-4be1-99fe-c50cb2a8fe2d -->

## 3. 工具栏 BPM 控件

- [x] 3.1 在 `gui.py` 工具栏「量化」旁新增「BPM」`QDoubleSpinBox`（20.0～300.0、1 位小数、步进 1、`keyboardTracking(False)`）；无曲目与播放中禁用，随 `_set_range_controls_enabled` 一起切换 <!-- comet-task:a9142c56-4d43-48ca-8137-8a5b2185fdee -->
- [x] 3.2 `_load_piano_roll` 中用 `converter.get_tempo_and_time_signature` 的 BPM 回填数值框，并用 `_updating_bpm` 保护位避免触发重算；切换曲目时必须覆盖旧值 <!-- comet-task:b158f98c-f99e-4745-94ac-2ee7f3c6f1a0 -->
- [x] 3.3 连接 `valueChanged`：按 `factor = 旧/新` 调 `piano_roll.rescale_times`，再用新 BPM 重算 `set_measure_grid`、`set_beat_grid` 与量化网格，最后更新 `current_bpm` 并标记未保存；播放中直接返回 <!-- comet-task:fb81e917-d556-44c9-8aa2-7108b9193713 -->

## 4. 标尺与网格联动验证

- [x] 4.1 验证 BPM 变更后顶部标尺小节序号、背景小节线、量化吸附三者使用同一 `60/BPM` 拍长（手动：4/4 曲目 120→60 时小节线每 4 秒一条、标尺序号对齐） <!-- comet-task:161103a5-afc0-4053-934b-6a038c836017 -->
- [x] 4.2 验证量化档位 1/4 下改 BPM 后拖动音符仍吸附到正确节拍点（手动） <!-- comet-task:b8c61abf-783b-4f56-84ba-432045e5d7f3 -->

## 5. MIDI 导出写入 BPM

- [x] 5.1 `build_music.write_notes_to_midi` 增加可选 `tempo_bpm: Optional[float] = None`：提供时把所有 `set_tempo` 事件改写为 `tempo_us_from_bpm`，缺失则在 0 号音轨插入；秒数→tick 使用新 tempo；新增 `tests/test_midi_tempo_export.py` 用 mido 构造 120 BPM 两音轨文件，导出 90 BPM 后断言 tempo=90、处理音轨 tick 不变、未处理音轨等价 <!-- comet-task:19590cb1-6e7b-46d6-abee-9adb87b1fda8 -->
- [x] 5.2 `gui.save_piano_roll` 传入 `self.current_bpm`；验证改 BPM 后另存的文件读回速度为当前 BPM（手动或用第 5.1 组测试覆盖的同一入口） <!-- comet-task:bc2fee92-a541-4a55-b53b-8264336bbd5e -->

## 6. 集成验证

- [x] 6.1 运行 `.venv\Scripts\python.exe -m unittest discover -s tests -v`，确认上一轮 51 项与本轮新增测试全部通过 <!-- comet-task:18093b5c-1e59-4b3c-aa5b-2048d7de33f8 -->
- [x] 6.2 手动走查：导入显示 BPM、修改后播放变快/变慢、标尺与小节线对齐、连续改回原值、播放中禁用、另存 MIDI 速度为当前 BPM <!-- comet-task:d3bed8ba-4811-448e-88f2-ae5b2aff946b -->

## Workflow follow-up

- 完成 Verify 后按 Comet 交付流程归档或交付，具体方式由用户确认。
