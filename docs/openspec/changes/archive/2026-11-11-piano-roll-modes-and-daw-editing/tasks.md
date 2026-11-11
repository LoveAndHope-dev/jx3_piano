# Tasks

## 1. 模式切换

- [x] 1.1 `gui.on_range_toggle_clicked` 改为「演奏/编辑」：黄框可见 ⇔ 演奏模式，并同步 `piano_roll.set_read_only`；按钮文案改为「🎹 演奏模式 / ✏️ 编辑模式」 <!-- comet-task:b36f2527-04b8-4abd-95d6-18d32373370f -->
- [x] 1.2 标尺定位与只读解耦：`PianoRollWidget` 增加 `set_playhead_locked(bool)`，播放开始/停止时设置；标尺用该状态而非 `is_read_only` 决定是否响应鼠标 <!-- comet-task:8f30ba86-b6fb-4f61-b01b-88d25f1d652c -->
- [x] 1.3 手动验收：演奏模式下铺面不可编辑、标尺仍可定位、工具栏可用；编辑模式下全部恢复；播放中切模式不解锁只读 <!-- comet-task:0de529dd-54de-4bdf-b209-f45308dd571b -->

## 2. DAW 空白区域行为

- [x] 2.1 空白区域：单击清空选择、双击新建并选中、拖动框选；新增 `mouseDoubleClickEvent`，互不干扰 <!-- comet-task:b30b7093-398c-4fc7-96cb-ded536578053 -->
- [x] 2.2 offscreen UI 测试覆盖三种手势（音符数、选中集合断言） <!-- comet-task:7b45562d-5a98-43f3-9b42-b5e3bef4eeb1 -->

## 3. 左边缘调整起始时间

- [x] 3.1 命中测试区分左/右边缘（短音符优先右边缘）；新增 `resize-start` 拖拽：结束时间不变、起点吸附、钳制到最小时长 <!-- comet-task:5896f990-0f22-448c-96ea-fd304b4f2de9 -->
- [x] 3.2 UI 测试：左边缘拖动改变 start/end 关系；拖过结尾停在最小时长 <!-- comet-task:9ea42864-bdb8-4402-ac73-a718b83ce065 -->

## 4. 方向键微调

- [x] 4.1 新增方向键处理：←/→ 按量化步长（关闭时 0.1s）平移选中音符；↑/↓ 半音移调；Shift+↑/↓ 八度；越界跳过、无选中无变化 <!-- comet-task:fe8ee5e7-1230-4113-8dd3-1e8416af0c9d -->
- [x] 4.2 UI 测试：量化 1/8 步长、半音/八度、无选中 <!-- comet-task:730e6150-fbd6-4f72-af86-e8896206bb7e -->

## 5. Ctrl+滚轮缩放

- [x] 5.1 `wheelEvent` 由 Shift 改为 Ctrl 触发缩放；Shift+滚轮恢复普通滚动；更新既有缩放测试 <!-- comet-task:84210419-5582-4e9f-9ee6-98880309274b -->
- [x] 5.2 手动验收：Ctrl+滚轮锚点不漂移；Shift+滚轮不再缩放 <!-- comet-task:5bba82b8-7882-4a16-92ef-44b7b07342b4 -->

## 6. 按钮高度与页脚

- [x] 6.1 全局 QSS 让按钮上下高度与下拉框一致（约 26px），确认播放/保存/导入/新建/删除等按钮统一 <!-- comet-task:6634e911-8a74-4a7e-80b1-b7b7d21c3afc -->
- [x] 6.2 页脚文案改为 `created by 66maer updated by Loveanope_Dev` <!-- comet-task:0fa73f88-5cf8-438f-9d79-5b772d45a01c -->

## 7. 集成验证

- [x] 7.1 运行 `.venv\Scripts\python.exe -m unittest discover -s tests -v`，确认既有 99 项（含改为 Ctrl 的缩放测试）与本轮新增全部通过 <!-- comet-task:4691400d-86f8-49c6-afd4-4deb02ebf5ba -->
- [x] 7.2 手动走查：模式切换、空白三种手势、左右边缘、方向键、Ctrl/Shift+滚轮、按钮高度、页脚文字 <!-- comet-task:ffe4dbd3-9d09-4407-b1c1-2a7ab7e75bed -->

## Workflow follow-up

- 完成 Verify 后按 Comet 交付流程归档或交付，具体方式由用户确认。
