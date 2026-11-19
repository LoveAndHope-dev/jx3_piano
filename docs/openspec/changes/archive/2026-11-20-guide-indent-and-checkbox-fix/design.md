# Design

行为需求以 `specs/playlist-selection/spec.md`、`specs/usage-guide/spec.md` 为准。

## Context

- `app/ui/widgets.py::AntCheckBox` 用 `QCheckBox::indicator { width:0; height:0 }` 隐藏原生指示器，再在 `paintEvent` 中自绘方框与勾选。
- Qt 的 `QCheckBox::hitButton` 依赖 indicator 的点击矩形；indicator 尺寸为 0 后，点击命中区域为空，导致点击无反应。
- 向导中两个 `<h3>` 子小节下的 `<ul>` 没有额外缩进。

## Decisions

### 1. 复选框点击

- 在 `AntCheckBox` 中重写 `hitButton(pos)`，返回 `self.rect().contains(pos)`，让整个 18×18 控件都可点击。
- 不改动 `toggled` 信号、勾选集合或行布局。

### 2. 向导缩进

- 给「铺面编辑工具栏」与「钢琴窗」两个 `<ul>` 增加 `style="margin-left: 24px;"`，使每行说明相对小节标题缩进。
- 保持文字内容与顺序不变。

## Risks

- 整个控件可点击后，复选框的命中区域略大于绘制方框，但不会影响行点击或批量选择逻辑。

## Test Strategy

- 用 `QTest.mouseClick` 点击复选框中心与边框位置，断言 `isChecked` 与 `_checked_play_paths` 正确切换。
- 向导 HTML 中两个子小节的 `<ul>` 带缩进样式。
- 既有 250 项回归。
