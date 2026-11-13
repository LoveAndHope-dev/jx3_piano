# Tasks

## 1. 工具栏三行与合并按钮

- [x] 1.1 第一行改为标题 + 模式切换（右侧固定） <!-- comet-task:1f2eedd2-dbf8-4069-b28d-e8f685b2720c -->
- [x] 1.2 第二行：合并主按钮与曲谱优化靠左，量化/BPM 靠右 <!-- comet-task:ef0a020a-6c8d-402d-9741-cd597bb3850a -->
- [x] 1.3 第三行：最低映射、最高映射、绝对最低、绝对最高全部靠左 <!-- comet-task:0a9a3739-5229-42f7-8dda-f1b584ee3e26 -->
- [x] 1.4 合并按钮：编辑模式保存、演奏模式播放/停止，文案与可用状态随模式更新 <!-- comet-task:4b0a1700-e465-4484-afd9-3d25678f7b58 -->
- [x] 1.5 替换所有 `piano_save_btn` 引用并保持保存/播放行为不变 <!-- comet-task:fbbc64ab-beed-4b0f-bc51-511629f24a38 -->

## 2. 钢琴窗纵向缩放与聚焦

- [x] 2.1 画布行高改为实例状态，提供夹紧的 `set_row_height` <!-- comet-task:35b82f42-c5ca-48ba-8645-69321bfcf6a5 -->
- [x] 2.2 `Shift + 滚轮` 纵向缩放，以鼠标位置为锚点；不触发 `notesChanged` <!-- comet-task:a0993a60-cff8-4c80-b698-388257aa4935 -->
- [x] 2.3 键盘与背景随行高重绘，场景高度同步 <!-- comet-task:8a43c5ec-c81c-477b-8057-63b625cdf34d -->
- [x] 2.4 播放开始时黄框纵向居中 <!-- comet-task:6118deed-755b-4e8c-94e8-59fe76499a29 -->
- [x] 2.5 左侧键盘固定回归测试 <!-- comet-task:41119a85-2be9-4f5e-9063-3fb9d45f71fc -->

## 3. 亮暗主题

- [x] 3.1 主题模块提供深色/浅色两套令牌 <!-- comet-task:2067332f-6c46-4bce-a4fd-155466621e98 -->
- [x] 3.2 控制面板新增主题切换按钮，切换整站样式并更新文案 <!-- comet-task:00e4aa1b-57bb-4a45-a92f-07511c652af8 -->
- [x] 3.3 会话内记忆；重启回到深色 <!-- comet-task:0ebad794-4c09-4eaa-a91c-d5000dfdbfc7 -->

## 4. Ant Design 细化

- [x] 4.1 标题/分组/辅助文字层级与间距统一 <!-- comet-task:28cf8611-c0c8-4e87-b85a-fae8ba5dba1e -->
- [x] 4.2 主按钮、危险按钮与状态色在两套主题下一致 <!-- comet-task:f9b2b823-3672-4a81-abde-293c90ad04d1 -->

## 5. 验证

- [x] 5.1 更新工具栏布局与按钮状态测试，新增缩放/聚焦/主题测试 <!-- comet-task:5f8f1e15-355b-4ae1-a404-c01a7b34f743 -->
- [x] 5.2 `.venv\Scripts\python.exe -m unittest discover -s tests -v` 全部通过 <!-- comet-task:b31ecc88-7c44-4623-ba12-4ad0ff4c6e17 -->
- [x] 5.3 offscreen 截图核对深/浅两套界面；重新打包 exe 并启动冒烟 <!-- comet-task:07fc9dae-4f7f-4970-aa71-2ed504bb4a13 -->
