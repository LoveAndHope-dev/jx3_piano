# 验收记录：guide-indent-and-checkbox-fix

## 环境

- Windows + Python 3.14 + PyQt5
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 251 tests ... OK`

## 变更

### 复选框点击修复

- 根因：`AntCheckBox` 为隐藏原生指示器设置 `width:0; height:0`，Qt 的 `QCheckBox::hitButton` 依赖 indicator 的点击矩形，导致命中区域为空。
- 修复：重写 `AntCheckBox.hitButton(pos)`，返回 `self.rect().contains(pos)`，整个 18×18 控件均可点击。
- 实测：点击中心与边框位置均能切换勾选，`_checked_play_paths` 同步更新，当前曲目不变。

### 向导缩进

- 「铺面编辑工具栏」与「钢琴窗」两个 `<ul>` 增加 `style="margin-left: 24px;"`。
- 每行说明相对小节标题整体缩进，内容与顺序不变。

## 覆盖

| 场景 | 测试 |
| --- | --- |
| 点击复选框中心与边框都能切换 | `test_checkbox_click_toggles_from_any_position` |
| 勾选不改变当前曲目 | `test_checkbox_toggles_without_changing_current` |
| 向导两个子小节带缩进样式 | `test_guide_opens_and_covers_areas` |
| 其余回归 | 既有 249 项 |

## 备注

- exe 已重新打包（`cd2605d`），构建产物已清理。
