# Design

- `app/ui/piano_page.py`：删除 `title_label` 的创建与添加，保留 `action_row.addStretch()` 与右侧模式按钮。
- `app/ui/log_page.py`：删除 `log_label`，保留 `addStretch()` 与「清空」按钮。
- `app/ui/theme.py`：删除 `QLabel#pageTitle` 规则。
- 测试：更新三行布局断言（第一行以弹性空白开头、模式按钮在末尾）；主题选择器测试移除 `pageTitle`。
