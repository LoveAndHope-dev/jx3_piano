# Comet Design Handoff

- Change: refactor-project-structure-and-antd-theme
- Phase: design
- Mode: compact
- Context hash: e480ed50d692c6808bf41241991c47e10bc609f66e6ecb5611180d2a345089db

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/refactor-project-structure-and-antd-theme/proposal.md

- Source: docs/openspec/changes/refactor-project-structure-and-antd-theme/proposal.md
- Lines: 1-23
- SHA256: d94b2b5863383b8e5114672be09518a2b0745135368d35a54618dbd7d2fb3bc1

```md
# 项目结构重构与 Ant Design 主题

## Why

- `gui.py`（1,870 行）、`piano_roll.py`（1,458 行）、`build_music.py`（1,440 行）把多种职责堆在同一文件里：改一个铺面交互要在 1,400 多行里定位，改播放逻辑要和界面代码混读。
- 界面样式全部是散落的硬编码颜色、间距和圆角，同类控件在不同页面高度/边框/留白不一致，视觉上显得杂乱。

## What Changes

- **代码分层**：把三个大文件拆成职责清晰的包，入口文件保留为薄门面，现有导入路径与公开类名不变。
  - `gui.py` → `app/`：主窗口装配、铺面页、日志页、播放列表页、播放控制、撤销历史、后台线程、主题。
  - `piano_roll.py` → 包：几何/时间轴换算、画布绘制与交互、组合控件。
  - `build_music.py` → `music/` 包：音高映射、MIDI 读写、播放数据生成、文件分析、CLI。
- **Ant Design 深色令牌**：新增 `app/ui/theme.py`，集中定义颜色、间距（4/8/12/16/24）、圆角（2/4/6/8）、字号（12/14/16/20）、控件高度（32）、边框与状态色，并用令牌生成全局 QSS。
- **视觉统一**：按钮/输入框/下拉框统一 32px 高度与 6px 圆角；分组改为 antd 卡片式分区（1px 边框、8px 圆角、16px 内边距）；标签页改为下划线式；滚动条收窄；危险按钮使用错误色；状态提示使用成功/警告/错误色。
- **行为不变**：所有播放、铺面编辑、撤销/前进、曲谱优化、播放列表与资产保存行为保持不变；188 项测试全部保留并通过。

## Impact

- 新增 `app/`、`music/` 包与 `piano_roll/` 包；`gui.py`、`piano_roll.py`、`build_music.py` 变为兼容门面。
- `tests/` 的导入路径不变（`import gui`、`from piano_roll import ...`、`from build_music import MidiToKeysConverter`）。
- `build_exe.py` 仍以 `gui.py` 为入口，打包内容相应增加包目录。
- 不改变 play_code JSON、MIDI 读写结果、按键映射与播放时序。

```

## docs/openspec/changes/refactor-project-structure-and-antd-theme/design.md

- Source: docs/openspec/changes/refactor-project-structure-and-antd-theme/design.md
- Lines: 1-134
- SHA256: 72f289981c218fcce5f695e4b8c39744ac23b92187412f7ccfb2e97beccd0332

[TRUNCATED]

```md
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

```

Full source: docs/openspec/changes/refactor-project-structure-and-antd-theme/design.md

## docs/openspec/changes/refactor-project-structure-and-antd-theme/tasks.md

- Source: docs/openspec/changes/refactor-project-structure-and-antd-theme/tasks.md
- Lines: 1-34
- SHA256: 4dc86c0f5064a175f0eefa9ced4b83871023dfcfbd59516b96891df113ebc4f3

```md
# Tasks

## 1. Ant Design 主题

- [ ] 1.1 新增 `app/ui/theme.py`：深色 antd 令牌 + `build_stylesheet(tokens)` <!-- comet-task:6498d221-7a48-4a34-870f-c566ba404a41 -->
- [ ] 1.2 `setup_style` 改用令牌生成样式；保留所有 objectName <!-- comet-task:f8df1d2a-e827-405e-8ab0-880d3016fa11 -->
- [ ] 1.3 统一按钮/输入框/下拉框 32px 高度、卡片分组、下划线标签页、8px 滚动条 <!-- comet-task:03d60010-0e5a-410b-8385-5fc32bc321e3 -->
- [ ] 1.4 主题测试：令牌完整性、样式包含主色、不含旧主色 `#3498DB` <!-- comet-task:bd619a14-8402-47e7-9593-e5354d4a0bcd -->

## 2. GUI 拆分

- [ ] 2.1 抽出 `app/workers/`（PlayThread、BatchConversionWorker） <!-- comet-task:81024c32-cf2e-4d59-a76a-943a10ad5531 -->
- [ ] 2.2 抽出 `app/history.py`（快照、undo/redo、未保存标记） <!-- comet-task:5f3b215a-9a77-4b5c-bb33-7f52e072ad3e -->
- [ ] 2.3 抽出 `app/playback.py`（播放开始/停止/进度/完成、线程生命周期） <!-- comet-task:08a9d0db-2f5b-46aa-886d-dd4b6a8c4215 -->
- [ ] 2.4 抽出 `app/ui/piano_page.py`、`playlist_page.py`、`log_page.py` <!-- comet-task:099d21ae-93f9-40b2-9c67-686cdf0e6f82 -->
- [ ] 2.5 `app/main_window.py` 只保留装配与跨页协调；`gui.py` 变薄门面 <!-- comet-task:4ca3483e-1ccb-42f5-ae27-722cb48907b4 -->

## 3. 铺面拆包

- [ ] 3.1 `piano_roll/geometry.py`：时间/像素换算、缩放、音符数学 <!-- comet-task:696579c4-e5ea-4d5b-a1fc-2234c807d078 -->
- [ ] 3.2 `piano_roll/painting.py` 与 `canvas.py`：绘制与交互分离 <!-- comet-task:dd537c37-a7e9-4f02-9162-7522fa911c77 -->
- [ ] 3.3 `piano_roll/ruler.py`、`widget.py`；`piano_roll.py` 门面 re-export <!-- comet-task:b8a250fd-516c-4b88-9a14-edc8a708e519 -->

## 4. 音乐处理拆包

- [ ] 4.1 `music/mapping.py`、`midi_io.py`、`analysis.py` <!-- comet-task:aed9a53e-e3b3-4e64-8263-a7cd1945fa5a -->
- [ ] 4.2 `music/playback.py`、`cli.py` <!-- comet-task:7f36a39d-5f18-4269-90b7-a645562a822d -->
- [ ] 4.3 `music/converter.py` 薄委托类；`build_music.py` 门面 <!-- comet-task:5e1ceb41-5bd0-44fe-8d88-529294d65d58 -->

## 5. 验证

- [ ] 5.1 结构冒烟测试：公开导入与名称、单文件行数约束 <!-- comet-task:7f009e83-d6f5-4e04-a3a0-b49b7342aad5 -->
- [ ] 5.2 `.venv\Scripts\python.exe -m unittest discover -s tests -v` 全部通过 <!-- comet-task:e511b2ad-ffb8-4050-89a7-149b80a8e39f -->
- [ ] 5.3 offscreen 截图逐页核对视觉；重新打包 exe 并启动冒烟 <!-- comet-task:b13f2819-1446-4368-8400-6a6585c3f5fa -->

```

## docs/openspec/changes/refactor-project-structure-and-antd-theme/.openspec.yaml

- Source: docs/openspec/changes/refactor-project-structure-and-antd-theme/.openspec.yaml
- Lines: 1-2
- SHA256: 2e91af4681be83038a92e715cfb64d8067b4c8399c2b25074da27a778869f3aa

```md
schema: spec-driven
created: 2026-11-14

```

## docs/openspec/changes/refactor-project-structure-and-antd-theme/specs/project-structure/spec.md

- Source: docs/openspec/changes/refactor-project-structure-and-antd-theme/specs/project-structure/spec.md
- Lines: 1-35
- SHA256: ee57ff08d736bc6b2f92aee64d64c647aec5d2db6b27bfa61c05fcbc8d0c4d62

```md
# Spec Delta：项目结构

## Purpose

让每个模块只承担一类职责，改代码时能在千行以内的文件里定位；公开入口保持不变。

## ADDED Requirements

### Requirement: 职责拆分

项目 SHALL 按职责拆分为包：界面（`app/ui`）、后台线程（`app/workers`）、状态与流程（`app/core` 或页面模块）、音乐处理（`music`）、铺面（`piano_roll`）。单个模块文件 SHOULD 不超过 800 行；超过时 MUST 说明其单一职责并给出后续拆分方向。

#### Scenario: 修改铺面交互

- **WHEN** 需要调整画布拖拽或绘制
- **THEN** 只需查看 `piano_roll/` 内对应模块，不需要在主窗口文件里搜索

#### Scenario: 修改播放流程

- **WHEN** 需要调整播放开始/结束/进度
- **THEN** 只需查看 `app/` 中播放控制模块，界面装配与播放逻辑分离

### Requirement: 公开入口保持兼容

`gui.py`、`piano_roll.py`、`build_music.py` SHALL 继续导出原有公开名称（`MidiConverterGUI`、`PianoRollWidget`、`MidiToKeysConverter` 等），测试与打包脚本的导入路径 MUST 不需要修改。

#### Scenario: 既有测试导入

- **WHEN** 运行现有 188 项测试
- **THEN** 所有 `import gui`、`from piano_roll import ...`、`from build_music import ...` 仍然有效

#### Scenario: 打包入口

- **WHEN** 执行 `build_exe.py`
- **THEN** 仍以 `gui.py` 为入口，打包成功且程序可启动

```

## docs/openspec/changes/refactor-project-structure-and-antd-theme/specs/ui-design-system/spec.md

- Source: docs/openspec/changes/refactor-project-structure-and-antd-theme/specs/ui-design-system/spec.md
- Lines: 1-44
- SHA256: 55080cb2cf5a06cf01c8c217d00c350aa091646e66b801fa29f540f6c99d95a0

```md
# Spec Delta：Ant Design 主题

## Purpose

用一套集中管理的设计令牌替换散落的硬编码样式，使界面在深色基调下符合 Ant Design 的尺寸、间距与状态规范。

## ADDED Requirements

### Requirement: 集中式设计令牌

界面样式 SHALL 由 `app/ui/theme.py` 的令牌生成，令牌至少包含：主色、容器/浮层背景、边框、三级文字色、成功/警告/错误色、间距（4/8/12/16/24）、圆角（2/4/6/8）、字号（12/14/16/20）、控件高度（32）。界面代码 MUST NOT 直接硬编码颜色值（铺面画布的语义色除外）。

#### Scenario: 调整主题色

- **WHEN** 修改主题中的主色令牌
- **THEN** 所有按钮、选中态、焦点边框与标签页指示条随之更新，无需逐处改样式

#### Scenario: 新控件样式

- **WHEN** 新增按钮或输入框
- **THEN** 默认继承统一的 32px 高度、6px 圆角、悬停/按下/禁用状态

### Requirement: 深色 Ant Design 视觉规则

界面 SHALL 采用 antd 深色令牌：容器背景 `#1f1f1f`、页面背景 `#141414`、主色 `#1677ff`、边框 `#424242`、主文字 `rgba(255,255,255,0.85)`。分组 SHALL 使用卡片式分区（1px 边框、8px 圆角、16px 内边距）；标签页 SHALL 使用下划线选中态；滚动条 SHOULD 收窄为 8px。

#### Scenario: 分组区域

- **WHEN** 打开「铺面编辑」与「操作日志」
- **THEN** 两页的分组、按钮、输入框使用同一套颜色、圆角、间距与高度

#### Scenario: 状态色

- **WHEN** 出现成功、警告或失败日志
- **THEN** 对应提示使用 antd 深色的成功/警告/错误色，而不是随意取色

### Requirement: 视觉改动不影响功能

主题重构 MUST NOT 改变控件数量、功能位置、快捷键、播放与编辑行为；只允许调整颜色、间距、圆角、字号、控件高度与边框。

#### Scenario: 功能回归

- **WHEN** 完成主题替换后运行完整测试
- **THEN** 188 项测试全部通过，播放、撤销、曲谱优化与播放列表行为不变

```
