# Tasks

## 1. 修复裁剪逻辑

- [x] 1.1 `split_playback_at` 在起播点落在延时内部时保留剩余延时 <!-- comet-task:14b6fe9b-e839-4fc8-8a0f-c6d4f43d5792 -->
- [x] 1.2 起播点恰好落在延时结束、超出尾部、0 起点的边界行为保持正确 <!-- comet-task:9ae13cbc-f8b2-4a93-adff-8504d6150e33 -->

## 2. 回归测试

- [x] 2.1 更新 `tests/test_play_assets.py` 中把错误行为写成期望的用例 <!-- comet-task:2aa64e24-6fe4-41b4-addf-cb0f9662b7cb -->
- [x] 2.2 覆盖延时中间、延时边界、按键间与超尾场景 <!-- comet-task:40de6ffc-2adf-478b-a03d-b2d990539453 -->

## 3. 验证

- [x] 3.1 `.venv\Scripts\python.exe -m unittest discover -s tests -v` 全部通过 <!-- comet-task:3820f221-a859-44b6-b247-afe31ab73db7 -->
- [x] 3.2 复现脚本确认起播点 2.6 秒时返回 `[1.4, 'E']` <!-- comet-task:a364c177-be3f-4abe-8680-f01787f03bea -->
