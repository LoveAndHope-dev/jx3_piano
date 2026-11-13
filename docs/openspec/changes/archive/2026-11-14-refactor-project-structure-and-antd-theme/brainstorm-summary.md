# 设计探索摘要（Design）

change: `refactor-project-structure-and-antd-theme`

## 已确认（用户）

- 方案 A：拆包 + antd 令牌；功能与交互不变，不重排布局
- 主题：antd 深色令牌
- 工作区：`current`
- 痛点：改代码要在几千行文件里跳；界面杂乱不统一

## 现状事实

- `gui.py` 1,870 行、`piano_roll.py` 1,458 行、`build_music.py` 1,440 行
- 测试导入 `gui` / `piano_roll` / `build_music` 的公开名称，且 `gui` 暴露 Qt 类与路径函数供替换
- 打包入口固定 `gui.py`
- 主题是 280 行 QSS 字符串，颜色/间距硬编码

## 候选方案

1. 兼容门面：入口文件只 re-export，实现进包；导入路径零改动
2. GUI 按职责拆 mixin（窗口 API 被测试与信号广泛使用，纯组合需数百处转发）
3. `piano_roll` 包：geometry / painting / canvas / ruler / widget
4. `music` 包：mapping / midi_io / analysis / playback / converter / cli
5. `app/ui/theme.py` 深色令牌 + `build_stylesheet()`
6. 分 6 步迁移，每步全量测试

## 备选

| 备选 | 原因 |
| --- | --- |
| 完全组合式重构 | 数百处转发，回归风险与收益不匹配 |
| 只拆不改 UI / 只改 UI | 无法同时解决两个痛点 |
| 重排布局（侧栏卡片化） | 用户选择保持功能位置 |
| 浅色主题 | 用户选择深色 |

## 风险

- mixin 仍共享 self（比 1,870 行单类易定位，后续可提升 History 为对象）
- 导入循环 → 从具体模块导入，门面只向外 re-export
- PyInstaller 收集新包：必要时加 hidden-import
- QSS 选择器变化影响测试 → 保留全部 objectName
- 视觉对比度 → offscreen 截图逐页核对

## Spec Patch

无。

## 未决问题

无。
