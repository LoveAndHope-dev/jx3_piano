# Tasks

## 1. Ant Design 主题

- [x] 1.1 新增 `app/ui/theme.py`：深色 antd 令牌 + `build_stylesheet(tokens)` <!-- comet-task:6498d221-7a48-4a34-870f-c566ba404a41 -->
- [x] 1.2 `setup_style` 改用令牌生成样式；保留所有 objectName <!-- comet-task:f8df1d2a-e827-405e-8ab0-880d3016fa11 -->
- [x] 1.3 统一按钮/输入框/下拉框 32px 高度、卡片分组、下划线标签页、8px 滚动条 <!-- comet-task:03d60010-0e5a-410b-8385-5fc32bc321e3 -->
- [x] 1.4 主题测试：令牌完整性、样式包含主色、不含旧主色 `#3498DB` <!-- comet-task:bd619a14-8402-47e7-9593-e5354d4a0bcd -->

## 2. GUI 拆分

- [x] 2.1 抽出 `app/workers/`（PlayThread、BatchConversionWorker） <!-- comet-task:81024c32-cf2e-4d59-a76a-943a10ad5531 -->
- [x] 2.2 抽出 `app/history.py`（快照、undo/redo、未保存标记） <!-- comet-task:5f3b215a-9a77-4b5c-bb33-7f52e072ad3e -->
- [x] 2.3 抽出 `app/playback.py`（播放开始/停止/进度/完成、线程生命周期） <!-- comet-task:08a9d0db-2f5b-46aa-886d-dd4b6a8c4215 -->
- [x] 2.4 抽出 `app/ui/piano_page.py`、`playlist_page.py`、`log_page.py` <!-- comet-task:099d21ae-93f9-40b2-9c67-686cdf0e6f82 -->
- [x] 2.5 `app/main_window.py` 只保留装配与跨页协调；`gui.py` 变薄门面 <!-- comet-task:4ca3483e-1ccb-42f5-ae27-722cb48907b4 -->

## 3. 铺面拆包

- [x] 3.1 `piano_roll/geometry.py`：时间/像素换算、缩放、音符数学 <!-- comet-task:696579c4-e5ea-4d5b-a1fc-2234c807d078 -->
- [x] 3.2 `piano_roll/painting.py` 与 `canvas.py`：绘制与交互分离 <!-- comet-task:dd537c37-a7e9-4f02-9162-7522fa911c77 -->
- [x] 3.3 `piano_roll/ruler.py`、`widget.py`；`piano_roll.py` 门面 re-export <!-- comet-task:b8a250fd-516c-4b88-9a14-edc8a708e519 -->

## 4. 音乐处理拆包

- [x] 4.1 `music/mapping.py`、`midi_io.py`、`analysis.py` <!-- comet-task:aed9a53e-e3b3-4e64-8263-a7cd1945fa5a -->
- [x] 4.2 `music/playback.py`、`cli.py` <!-- comet-task:7f36a39d-5f18-4269-90b7-a645562a822d -->
- [x] 4.3 `music/converter.py` 薄委托类；`build_music.py` 门面 <!-- comet-task:5e1ceb41-5bd0-44fe-8d88-529294d65d58 -->

## 5. 验证

- [x] 5.1 结构冒烟测试：公开导入与名称、单文件行数约束 <!-- comet-task:7f009e83-d6f5-4e04-a3a0-b49b7342aad5 -->
- [x] 5.2 `.venv\Scripts\python.exe -m unittest discover -s tests -v` 全部通过 <!-- comet-task:e511b2ad-ffb8-4050-89a7-149b80a8e39f -->
- [x] 5.3 offscreen 截图逐页核对视觉；重新打包 exe 并启动冒烟 <!-- comet-task:b13f2819-1446-4368-8400-6a6585c3f5fa -->
