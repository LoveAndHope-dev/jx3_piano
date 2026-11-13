# 验收记录：refactor-project-structure-and-antd-theme

## 环境

- Windows + Python 3.14 + PyQt5
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 200 tests ... OK`（原 188 + 主题 7 + 结构 5）

## 结构拆分

| 原文件 | 行数 | 拆分后 |
| --- | --- | --- |
| `gui.py` | 1,870 | `gui.py` 76 行门面 + `app/`（main_window 192、piano_page 525、playlist_page 236、log_page 68、playback 196、history 91、theme 378、common 123、workers 161） |
| `piano_roll.py` | 1,458 | `piano_roll/`：geometry 135、ruler 191、canvas 488、canvas_input 410、canvas_paint 185、widget 125、`__init__` 9 |
| `build_music.py` | 1,440 | `build_music.py` 59 行门面 + `music/`：mapping 97、analysis 172、midi_io 224、playback 510、cli 246、converter 140、paths 54 |

- 所有包内模块均 ≤800 行（最大 525）。
- 公开导入保持不变：`import gui`、`from piano_roll import ...`、`from build_music import MidiToKeysConverter` 全部可用。
- 打包入口仍为 `gui.py`，exe 已重新打包并启动存活冒烟。

## Ant Design 深色主题

- 令牌集中在 `app/ui/theme.py`：主色 `#1677ff`、页面 `#141414`、容器 `#1f1f1f`、边框 `#424242`、成功/警告/错误色、间距 4/8/12/16/24、圆角 4/6/8、字号 12/14/16/20、控件高度 32。
- 全局 QSS 由令牌生成：按钮/输入框/下拉框统一 30px 内容高度（32px 外框）、6px 圆角、悬停主色边框；卡片式分组、下划线标签页、8px 滚动条。
- 旧的 `#3498DB` / `#2C3E50` 硬编码已从样式表移除（测试断言）。
- offscreen 截图核对：深色背景、主色按钮、绿色导入、卡片分区、标签页下划线均一致。

## 覆盖

| 能力 | 测试 |
| --- | --- |
| 公开导入与类名保持 | `test_project_structure.PublicImportTest` |
| 包内模块 ≤800 行 | `test_package_modules_stay_reviewable` |
| 令牌完整性与 antd 深色值 | `test_theme.ThemeTokenTest` |
| 样式表使用令牌且不含旧主色 | `test_stylesheet_uses_tokens` |
| 关键选择器仍存在 | `test_stylesheet_keeps_core_selectors` |
| 行为回归 | 既有 188 项 |

## 独立审查后的修复

- **Important**：①主色/成功/错误按钮补齐 `:pressed` / `:disabled` 选择器，禁用的「弹奏」「导入」不再看起来可用；②选中态、菜单高亮与悬停色改为从主色/成功/错误令牌派生（`rgba(primary, 0.22)`），新增浅色文字、滚动条悬停、`radiusXS` 令牌；③`gui.get_midi_dir_path` 明确为只读转发，文档标注唯一替换点是 `music.paths`，并新增测试确认补丁可同时影响 `app.common` 与批量导入线程。
- **Minor**：补充 `QMenu`/`QMessageBox`/`QDialog` 深色规则；署名标签改用 12px；`build_stylesheet` 去掉可变默认参数；`music/__init__` 与 `piano_roll/__init__` 补回公开名前向导出；入口函数移到 `app/entry.py`；新增令牌替换、按钮状态选择器、门面同一性、新解释器导入与路径提供者测试。
- 复验结果：`Ran 200 tests ... OK`；exe 已重新打包。

## 手动确认

- 主窗口、铺面页、日志页、播放列表布局与操作位置未变。
- 播放/停止、撤销/前进、曲谱优化、导入/新建/删除行为不变。
- 打包后的 exe 可启动并保持运行。

## 结论

结构拆分与主题替换完成，所有模块进入可维护规模；200 项测试通过，exe 重新打包并冒烟。
