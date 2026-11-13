# 验收记录：remove-page-headers

## 环境

- Windows + Python 3.14
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 218 tests ... OK`

## 变更

- 铺面编辑页：删除第一行左侧 `🎼 铺面编辑` 标题；该行现在只保留右侧「演奏模式 / 编辑模式」切换。
- 操作日志页：删除头部 `📋 操作日志` 标题；头部只保留右侧「清空」按钮。
- 移除不再使用的 `QLabel#pageTitle` 样式。
- 标签页名称保持不变。

## 覆盖

| 场景 | 测试 |
| --- | --- |
| 第一行以弹性空白开头、模式按钮在末尾 | `test_piano_toolbar_three_rows` |
| 主题选择器不再包含 pageTitle | `test_stylesheet_keeps_core_selectors` |
| 其余行为 | 216 项既有测试 |

## 手动确认

- 铺面页顶部不再出现大标题，模式切换仍固定在右侧。
- 日志页顶部不再出现标题，清空按钮仍在右侧。
