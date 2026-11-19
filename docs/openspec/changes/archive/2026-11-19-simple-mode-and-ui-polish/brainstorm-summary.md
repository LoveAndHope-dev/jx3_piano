# 设计探索摘要（Design）

change: `simple-mode-and-ui-polish`

## 已确认（用户）

- 主题/置顶/向导 + 简单模式按钮放到标题下方同一行
- 左栏加宽 25%（350 → 438）
- 复选框需要勾选标记；歌名悬停缓慢向左循环，移出恢复
- 简单模式：隐藏铺面编辑标签、静默丢弃未保存修改并清空；映射固定 Z/7，绝对音域固定 C2/B5；删除选中旁显示播放；播放前全量曲谱优化并保存再播放；退出重载原始 MIDI
- 向导中简单/正常模式分开
- 亮色下两个大面板背后背景与框线改淡灰

## 现状事实

- 控制面板标题行有主题/置顶，向导在按钮行
- 列表行为 `QCheckBox + QLabel`，勾选指示器为实心填充
- 简单模式不存在；播放走 `start_playing` → `_ensure_play_assets_current`
- 优化入口 `PianoRollCanvas.arpeggiate_selected` 只处理选中音符
- 亮色 `QFrame#leftPanel/rightPanel` 边框用 `colorBorderSecondary`，主窗口背景由 `QMainWindow` 提供

## 候选方案

1. 控制面板新增 `panel_actions` 行，四个按钮同排
2. `widgets.py`：`AntCheckBox` 自绘勾选、`MarqueeLabel` 定时滚动
3. 简单模式状态 + 标签页移除/恢复；`arpeggiate_all` 复用现有算法
4. 简单播放每次重读原始 MIDI → 全量优化 → 保存 → 播放
5. 亮色：`centralWidget` 背景 + 面板/分组框边框改用 `colorBorder`

## 备选

| 备选 | 原因 |
| --- | --- |
| QSS 图片勾选 | 需额外资源文件与打包路径处理 |
| 简单模式缓存优化结果 | 重复点击会叠加优化，改用每次重读 |
| 保留编辑标签只禁用 | 用户要求标签消失 |

## 风险

- 简单模式丢弃未保存修改（用户确认）
- 每次简单播放多一次 MIDI 解析
- 自绘控件需在主题切换时重绘
- 亮色边框统一后深色主题边框更明显

## Spec Patch

无。

## 未决问题

无。
