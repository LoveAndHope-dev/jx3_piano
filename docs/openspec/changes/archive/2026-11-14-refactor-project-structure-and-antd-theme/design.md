---
comet_change: refactor-project-structure-and-antd-theme
role: technical-design
canonical_spec: openspec
archived-with: 2026-11-14-refactor-project-structure-and-antd-theme
status: final
---

# Design

行为需求以 `specs/project-structure/spec.md` 与 `specs/ui-design-system/spec.md` 为准。

## Context

- 三个大文件：`gui.py` 1,870 行、`piano_roll.py` 1,458 行、`build_music.py` 1,440 行。
- 测试通过 `import gui`、`from piano_roll import ...`、`from build_music import MidiToKeysConverter` 使用公开名称；`gui` 还暴露 Qt 控件类与 `get_midi_dir_path` 等路径函数供测试替换。
- 打包入口固定为 `gui.py`（`build_exe.py` 的 pyinstaller 参数）。
- 主题是 `setup_style()` 里一段 280 行 QSS，颜色与间距散落。

## Decisions

### 1. 兼容门面，导入路径不变

- `gui.py`、`piano_roll.py`、`build_music.py` 保留为薄门面，只做 re-export，并保留测试会替换的模块级名字（`QPushButton`、`QMessageBox`、`get_midi_dir_path` 等）。
- 这样 188 项测试与 `build_exe.py` 不需要改导入；真正实现放在包里。

### 2. GUI 拆分为 mixin 页面 + 控制器

`gui.py` 的 `MidiConverterGUI` 有 60 多个方法，且大量方法互相引用窗口控件。完全改为组合需要数百处转发，风险和收益不成比例；采用按职责拆 mixin：

```
app/
  __init__.py
  main_window.py        # MidiConverterGUI(Mixin..., QMainWindow)：状态初始化、装配、closeEvent
  history.py            # HistoryMixin：快照、undo/redo、未保存标记
  playback.py           # PlaybackMixin：start/stop/progress/finished、线程生命周期
  ui/
    __init__.py
    theme.py            # 令牌 + build_stylesheet()
    piano_page.py       # PianoPageMixin：铺面页装配、加载、BPM、量化、音域、曲谱优化、保存
    playlist_page.py    # PlaylistPageMixin：搜索/排序/列表行/导入/新建/删除/选中
    log_page.py         # LogPageMixin：日志页、日志写入、置顶
  workers/
    __init__.py
    play_thread.py      # PlayThread
    batch_import.py     # BatchConversionWorker
```

- mixin 仅通过 `self` 访问共享状态，不引入新的间接层。
- 每个文件目标 ≤ 500 行；`main_window.py` 只保留装配与跨页协调。

### 3. piano_roll 拆包

```
piano_roll/
  __init__.py    # re-export 公开名称（PianoRollWidget、*_math、常量）
  geometry.py    # 时间/像素换算、缩放、音符数学（纯函数）
  painting.py    # 画布绘制辅助
  canvas.py      # _PianoRollCanvas：状态、鼠标/键盘交互、剪贴板、信号
  ruler.py       # _TimeRuler
  widget.py      # PianoRollWidget：组合、缩放/滚动、对外 API
```

- 纯函数先搬 `geometry.py`，再由 `piano_roll.py` re-export，保证测试导入不变。
- 绘制与交互分离：`painting.py` 接收画布状态，不反向依赖交互。

### 4. music 拆包

```
music/
  __init__.py    # re-export MidiToKeysConverter 等
  mapping.py     # 键位阶梯、midi_note_to_key_sequence、音名、移调
  analysis.py    # 文件分析、速度/拍号、自动选轨与移调
  midi_io.py     # extract_notes / write_notes_to_midi
  playback.py    # convert_to_playback_data / regenerate / generate_code / complete_data
  converter.py   # MidiToKeysConverter：同名方法薄委托，保持调用方不变
  cli.py         # convert_midi、print_analysis_summary、__main__ 入口
```

- `MidiToKeysConverter` 的公开方法签名与返回值不变，内部委托到模块函数。
- `build_music.py` 门面 re-export 并保留 `if __name__ == "__main__"`。

### 5. Ant Design 深色令牌

`app/ui/theme.py` 定义：

```python
TOKENS = {
  "colorPrimary": "#1677ff",
  "colorPrimaryHover": "#4096ff",
  "colorPrimaryActive": "#0958d9",
  "colorBgBase": "#141414",
  "colorBgContainer": "#1f1f1f",
  "colorBgElevated": "#262626",
  "colorBorder": "#424242",
  "colorBorderSecondary": "#303030",
  "colorText": "rgba(255,255,255,0.85)",
  "colorTextSecondary": "rgba(255,255,255,0.65)",
  "colorTextTertiary": "rgba(255,255,255,0.45)",
  "colorSuccess": "#49aa19",
  "colorWarning": "#d89614",
  "colorError": "#dc4446",
  "radiusSM": 4, "radius": 6, "radiusLG": 8,
  "controlHeight": 32,
  "fontSize": 14, "fontSizeSM": 12, "fontSizeLG": 16, "fontSizeHeading": 20,
  "spaceXS": 4, "spaceSM": 8, "spaceMD": 12, "spaceLG": 16, "spaceXL": 24,
}
```

`build_stylesheet(tokens)` 生成全局 QSS：窗口/面板背景、卡片分组、按钮（默认/主色/危险/禁用）、输入框与下拉框（32px、6px 圆角、焦点主色边框）、标签页下划线、列表行、滚动条（8px）、日志文本、分组标题。

- 铺面画布内部的语义色（小节线、拍线、选中框、音域框）保留在 `piano_roll`，不进入 QSS。
- 布局尺寸（左侧面板宽度、工具栏间距）改用令牌值，但不改变控件顺序与功能区位置。

### 6. 迁移顺序（每步保持测试绿）

1. 新增 `app/ui/theme.py`，`setup_style` 改为调用 `build_stylesheet`，跑测试 + 截图检查。
2. 抽出 `app/workers/`、`app/history.py`，窗口改为继承 mixin。
3. 拆 `app/ui/` 三个页面 mixin。
4. 拆 `piano_roll/` 包（先几何、再绘制/交互、最后 widget）。
5. 拆 `music/` 包与 `build_music.py` 门面。
6. 视觉复查（间距/对齐/控件高度）+ 重新打包 exe。

### 7. 行数与依赖约束

- 单文件 > 800 行视为拆分未完成；`canvas.py` 若超出，继续把绘制分支移到 `painting.py`。
- 禁止 `app → gui` 反向导入；`piano_roll` 不依赖 `app`；`music` 不依赖界面。

## Risks / Trade-offs

- **mixin 不是纯组合**：共享 `self` 仍有耦合，但比 1,870 行单类更易定位；后续可把 History 提升为独立对象。
- **导入循环**：`app.ui.piano_page` 需要 `PianoRollWidget`，`gui` 门面需要 `app.main_window`；通过从具体模块导入、门面只向外 re-export 避免循环。
- **PyInstaller 收集**：新增包目录需要随入口自动收集；若漏收，在 `build_exe.py` 增加 `--hidden-import` 或 `--collect-submodules`。
- **QSS 选择器变化**：现有 objectName 保留，避免测试与运行时样式失效。
- **视觉回归**：主题替换后需要 offscreen 截图逐页核对，避免出现不可读的对比度。

## Test Strategy

- 既有 188 项测试作为行为回归；每一步迁移后全量运行。
- 新增结构冒烟测试：`import gui` / `piano_roll` / `build_music` 仍可用，公开名称存在，`build_stylesheet` 含主色与控件高度。
- 主题测试：令牌完整性（必需键）、QSS 不含旧的硬编码主色 `#3498DB`。
- 打包后启动 exe 冒烟。
