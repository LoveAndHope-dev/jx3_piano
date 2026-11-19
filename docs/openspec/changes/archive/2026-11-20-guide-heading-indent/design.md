# Design

行为需求以 `specs/usage-guide/spec.md` 为准。

## Decision

- 在 `app/ui/guide.py` 中给两个 `<h3>`（铺面编辑工具栏、钢琴窗）增加 `style="margin-left: 24px;"`。
- 列表已使用相同的 24px，标题与列表因此对齐。

## Test Strategy

- 向导 HTML 中两个 `<h3>` 带缩进样式。
- 既有 251 项回归。
