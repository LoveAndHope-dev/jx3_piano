# 设计探索摘要（Design）

change: `piano-roll-follow-and-undo`

## 已确认（用户）

- 撤销覆盖所有铺面内容变更（含 BPM 缩放），保留 50 步
- 播放跟随采用翻页式（80% → 20%）
- 演奏模式与播放中禁用撤销/前进
- 工作区：`current`（沿用既有选择）

## 现状事实

- 所有内容变更最终都会触发 `_PianoRollCanvas.notesChanged`
- BPM/拍号/量化保存在 GUI，撤销需同步恢复
- 播放进度经 `on_play_progress → set_playhead` 驱动
- 画布已有 `_read_only` 与横向滚动条

## 候选方案

1. 历史放 GUI：快照 {notes, bpm, signature, playhead}，50 步；`notesChanged` 后记录，应用时抑制记录
2. 画布只发 `undoRequested` / `redoRequested` 信号，只读时不发
3. 翻页跟随：`follow_playhead()` 在播放期由 `set_playhead` 调用，超过 80% 视口即整页前滚到 20%
4. 未保存标记按基线快照重算

## 备选

| 备选 | 原因 |
| --- | --- |
| 差量命令栈（command pattern） | 实现面更大，当前 50 步快照已足够 |
| 画布内维护历史 | 无法同步 BPM 与网格状态 |
| 居中锁定滚动 | 用户已选翻页式 |

## 风险

- 快照内存（大曲目 ×50）→ 50 步上限；后续可换差量
- 撤销不恢复选择 → 规格未要求，避免选中态不一致
- 播放中禁用避免音画不同步

## Spec Patch

无。

## 未决问题

无。
