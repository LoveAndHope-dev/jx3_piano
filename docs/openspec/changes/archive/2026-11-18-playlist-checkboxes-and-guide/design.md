# Design

- `app/common.py`：补充 `QCheckBox`、`QDialog`、`QTextBrowser` 导入。
- `app/main_window.py`：
  - 播放列表恢复 `SingleSelection`（行点击只单选）。
  - 控制面板按钮行新增「❓ 向导」。
- `app/ui/playlist_page.py`：
  - `self._checked_play_paths: set[str]`（在窗口初始化时建立）保存勾选路径，刷新后按路径恢复。
  - `_make_play_row` 左侧加入 `QCheckBox`（objectName `rowCheck`），`toggled` 连接 `_on_play_row_checked(path, checked)`；行点击保持 `setCurrentItem`，不再处理 Ctrl/Shift。
  - `select_all_play_items()`：遍历 `self._row_checkboxes` 全部设为勾选。
  - `on_delete_selected_play_items()`：使用 `_checked_play_paths` 对应的条目；未勾选只提示；一次确认后逐个删除；删除后从勾选集合移除并刷新。
  - `_delete_play_track()` 同步从勾选集合移除。
- `app/ui/guide.py`：`GUIDE_SECTIONS`/`build_guide_html()` + `GuideDialog(QDialog)`（标题「使用向导」、`QTextBrowser` 富文本、底部「关闭」按钮）。
- `app/main_window.py::show_guide()`：创建并 `show()` 非模态窗口，保存引用避免被回收。
- `app/ui/theme.py`：补 `QCheckBox` 样式（14px 方框、主色勾选）与 `QTextBrowser` 文本区样式。

验证：
- 行点击/勾选互不影响；全选、批量删除、搜索后恢复勾选。
- 向导可打开/关闭，内容覆盖各区域；既有测试回归。
