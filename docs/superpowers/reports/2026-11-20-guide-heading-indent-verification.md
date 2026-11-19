# 验收记录：guide-heading-indent

## 环境

- Windows + Python 3.14 + PyQt5
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 251 tests ... OK`

## 变更

- 「铺面编辑工具栏」与「钢琴窗」两个 `<h3>` 标题增加 `style="margin-left: 24px;"`。
- 两个子小节列表保持相同的 24px 左缩进，标题、项目符号与说明文字现在共用同一左边界。
- 测试同时断言两个 `<h3>` 与两个 `<ul>` 带有缩进样式，且位于正常模式小节之后。

## 备注

- exe 已重新打包（`b3b460b`），构建产物已清理。
