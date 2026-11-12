# Comet Design Handoff

- Change: editor-toolbar-layout-and-arpeggiate-script
- Phase: design
- Mode: compact
- Context hash: 3d828c32365e28aa82f16c4934a7bca3688b449ef39435a4ca8a6ed6870a7597

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/proposal.md

- Source: docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/proposal.md
- Lines: 1-22
- SHA256: 1730b45ef35daed2d7a6727a3cbd06fca4dd7645c26a3fde0689f1ddbc6cc608

```md
# 工具栏贴左、置顶按钮移位与曲谱优化接入原脚本

## Why

铺面编辑的工具栏被弹性空白撑开，窗口变宽后「保存」「演奏模式」「键位映射」等操作被推到右侧，与左侧的「弹奏」「曲谱优化」散成两片，操作时视线来回跳。窗口置顶按钮藏在「操作日志」页里，和它真正作用的窗口行为不在同一处。曲谱优化的实现是照着原脚本重写的内存版本，与用户手中的 `arpeggiate.py` 行为已经不一致（现版本保持时长不变，原脚本保持结束时间不变）。

## What Changes

- **工具栏贴左**：「铺面编辑」的两行工具栏全部从容器左边缘开始排列，去掉把控件推向右侧的弹性空白；窗口宽度变化时控件相对左边缘的位置不变，不被拉伸或重新分布。
- **置顶按钮移位**：从「操作日志」页移除，放到左侧「🎛️ 控制面板」标题行的右侧；按钮行为（切换置顶、文字切换、日志提示）不变。
- **曲谱优化接入原脚本**：把 `release/谱子/arpeggiate.py` 移到项目根目录 `arpeggiate.py`（保留脚本结构、参数与 `main`，删除原位置的副本），只做一处最小修正——展开时保持音符时长不变（起点与结束时间一起后移）。「曲谱优化」按钮改为对选中音符执行该脚本：以选中音符生成临时 MIDI，调用脚本的 `main(src, dst)`，读回结果并更新铺面；未选中音符不变。
- **其余随脚本**：1/32 四分音符的判定窗口与步长（tick 精度按脚本的 `ticks_per_beat=384` 约定）、组内按音高升序展开、同音高同起点去重、最小时值 1 tick。
- 脚本抛出异常时铺面不变，并在操作日志中提示。

## Impact

- `gui.py`：工具栏两行布局、控制面板标题行、曲谱优化调用与日志。
- `arpeggiate.py`：内容整体替换为原脚本（不再提供 `arpeggiate_notes`）。
- `piano_roll.py`：`arpeggiate_selected` 改为调用新的脚本执行模块；场景宽度与选中状态处理保持原样。
- 新增脚本执行模块（临时 MIDI 往返、读取结果、清理临时文件）。
- `tests/test_arpeggiate.py`：改为验证新执行路径与脚本语义。
- 播放、play_code、播放列表、撤销/前进与导出逻辑不变；曲谱优化仍会进入撤销历史。

```

## docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/design.md

- Source: docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/design.md
- Lines: 1-85
- SHA256: f55b8d4e3d82b8f063f5f37b32300b6b66a05d3e42bee4fc3dca0f97910c5e2c

[TRUNCATED]

```md
# Design

行为需求以 `specs/editor-toolbar-layout/spec.md` 与 `specs/arpeggiate-script/spec.md` 为准。

## Context

- `_setup_piano_roll_tab` 用两个 `QHBoxLayout` 组成工具栏；第一行在「曲谱优化」后插入 `addStretch()`，把「保存」「演奏模式」「键位映射」推到右侧。
- `_setup_log_tab` 把「📌 置顶」放在操作日志标题行；`toggle_topmost` 只依赖按钮状态。
- `release/谱子/arpeggiate.py` 是用户提供的 mido 脚本：`main(src, dst)` 读 MIDI、按 tick 展开音符、写回 MIDI；模块只在 `__main__` 下执行。
- 现项目根 `arpeggiate.py` 是照脚本重写的内存版（`arpeggiate_notes`，时长相较脚本行为不同）。
- 铺面音符为 `{id, pitch, start, duration, track, mapped}`，以秒为单位；`_PianoRollCanvas.arpeggiate_selected` 负责替换列表、重建图形、扩展场景并发出 `notesChanged`（撤销历史依赖该信号）。
- 运行环境包含 mido 1.3.3；打包为 `--windowed`，`sys.stdout` 可能为 `None`。

## Decisions

### 1. 工具栏：保留两行，弹性空白移到行尾

- 删除第一行「曲谱优化」之后的 `toolbar.addStretch()`，改为在整行末尾追加一个 stretch。
- 末尾 stretch 吸收多余宽度，控件按 sizeHint 依次贴左；窗口变宽时控件相对左边缘的位置不变（QComboBox/QSpinBox 的 Expanding 策略不会再被中间空白放大）。
- 第二行已有末尾 stretch，保持不变。
- 不引入 `setGeometry` 绝对坐标：控件高度随字体/DPI 变化，绝对坐标会重叠。

### 2. 控制面板标题行

- 把 `QGroupBox("🎛️ 控制面板")` 换成 `QFrame`（objectName `controlPanel`），内部纵向布局：
  1. 标题行：`QLabel("🎛️ 控制面板")`（objectName `panelTitle`）+ `addStretch()` + `self.topmost_btn`
  2. 导入/新建/刷新按钮行
  3. 作者信息
- QSS 为 `#controlPanel` 复用分组框的 2px 边框与 10px 圆角；`#panelTitle` 复用原分组框标题的渐变底、白字与内边距。
- 从操作日志标题行移除置顶按钮；`toggle_topmost` 逻辑不变。

### 3. 原脚本移入并做一处最小修正

- 把 `release/谱子/arpeggiate.py` 的内容写到项目根 `arpeggiate.py`，覆盖旧的 `arpeggiate_notes` 实现，并删除 `release/谱子/arpeggiate.py`。
- 保留 shebang、模块文档、参数常量、`extract_notes`/`dedupe`/`rebuild`/`main` 与 `__main__` 入口。
- 唯一算法修正：`arpeggiate()` 展开时保持时长不变（起点与结束时间同步后移），不再固定结束时间：

```python
delta = anchor + k * step - n['on']
n['on'] += delta
n['off'] += delta
if n['off'] - n['on'] < MIN_DUR_TICKS:
    n['off'] = n['on'] + MIN_DUR_TICKS
```

### 4. 新增 `arpeggiate_runner.py` 做 MIDI 往返

公开接口与旧实现保持一致，便于铺面层最小改动：

```python
def arpeggiate_notes(notes, selected_ids, seconds_per_beat) -> List[Dict]
```

流程：

1. 复制输入音符；没有选中或 `seconds_per_beat <= 0` 时直接返回副本。
2. 在 `tempfile.TemporaryDirectory()` 内生成输入 MIDI：
   - `ticks_per_beat = 384`，与脚本注释中的换算一致（1/32 拍 = 12 tick）
   - 每个选中音符一条独立音轨，起始 tick = `round(start / seconds_per_beat * 384)`，时值 tick = `max(1, round(duration / seconds_per_beat * 384))`
   - 用音轨索引回读结果，避免同音高音符无法区分
3. `contextlib.redirect_stdout/redirect_stderr` 包住 `arpeggiate.main(src, dst)`；脚本的 `print` 在 windowed 打包下不会写入 `None`。
4. 用脚本自带的 `extract_notes` 读取输出音轨：音轨为空表示该音符被去重移除；否则取 `on/off` 换算回秒。
5. 保持原始顺序返回新列表；临时目录由上下文管理器清理。
6. 异常原样抛出（由 GUI 捕获并记录日志），此时铺面尚未修改。

### 5. 铺面与 GUI 接线

- `_PianoRollCanvas.arpeggiate_selected` 改为调用 `arpeggiate_runner.arpeggiate_notes`，其余（变化计数、`_update_item_geometry`、场景扩展、`notesChanged`）保持原逻辑。
- `on_arpeggiate_clicked` 以四分音符为单位传入 `60.0 / current_bpm`（脚本以四分音符计 1/32 拍），并用 `try/except` 捕获脚本异常后写日志、不修改铺面。

## Risks / Trade-offs

- **临时文件 I/O**：每次点击生成并读取一个临时 MIDI，耗时在毫秒级；换取脚本逻辑原样复用。
- **tick 量化**：384 tick/拍使起点精度约 1/384 拍（120 BPM 时约 2.6 ms），与脚本自身注释的换算一致。
- **脚本被修改一处**：时长语义由「结束时间不变」改为「时长不变」；结构、参数与其它算法保持原样，并用测试固定。
- **去重会删音符**：同音高同起点重复音符会被移除；这是脚本 `DEDUPE=True` 的既定行为。
- **打包**：mido 已是依赖，无需新增第三方包；脚本随 `gui.py` 一并被 PyInstaller 收集（需确认 `--hidden-import` 或 import 关系）。

## Test Strategy


```

Full source: docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/design.md

## docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/tasks.md

- Source: docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/tasks.md
- Lines: 1-30
- SHA256: 2e8ec7a009f2fbe0dcfa8d83abbbe5520c71be922bd0618d5d4a13c9bbfb3cee

```md
# Tasks

## 1. 工具栏贴左

- [ ] 1.1 第一行工具栏去掉中段 stretch，改为行尾 stretch，两行控件全部贴左 <!-- comet-task:47f60a2a-54f0-4e45-82a9-83c3eb18ae70 -->
- [ ] 1.2 确认 QComboBox / QSpinBox 不再被中间空白拉伸（窗口变宽后位置不变） <!-- comet-task:0e84764a-986f-4f22-a9d7-7758d559e321 -->
- [ ] 1.3 UI 测试：两行首个控件贴左，末尾存在弹性空白 <!-- comet-task:d75bce6b-12f2-478c-bfca-c9502b7bd7f4 -->

## 2. 置顶按钮移位

- [ ] 2.1 控制面板改为 QFrame + 标题行（标题 + stretch + 置顶按钮），补齐 QSS <!-- comet-task:d1c7375a-d80d-4eaf-a130-2c02ed1a08d7 -->
- [ ] 2.2 从操作日志标题行移除置顶按钮；`toggle_topmost` 保持原行为 <!-- comet-task:914d18d3-bcd2-409c-83f6-90bba6adbfbc -->
- [ ] 2.3 UI 测试：置顶按钮在控制面板标题行、日志页不存在；置顶切换仍更新文字 <!-- comet-task:4e0a0d7b-4157-4719-be39-1ed715f50b1b -->

## 3. 原脚本移入（含一处最小修正）

- [ ] 3.1 `release/谱子/arpeggiate.py` 内容移入项目根 `arpeggiate.py`，删除原件 <!-- comet-task:fb50a81d-aaa9-4438-8190-508c75db0adc -->
- [ ] 3.2 仅修正展开时的时长语义：起点与结束时间同步后移，保留脚本结构、参数与 `main` <!-- comet-task:b82aa085-8fc9-4688-8152-46f52e130cd4 -->

## 4. 脚本执行与新接线

- [ ] 4.1 新增 `arpeggiate_runner.py`：tpb=384 的临时 MIDI 往返、每音符独立音轨、重定向 stdout、清理临时目录 <!-- comet-task:d71c4007-074f-4982-bc5b-56ba3e4e1ef3 -->
- [ ] 4.2 `piano_roll.arpeggiate_selected` 改用 runner，保持场景扩展与 `notesChanged` <!-- comet-task:3c3815cf-c8a0-4b9d-a523-5440cace36a8 -->
- [ ] 4.3 GUI 以四分音符传入拍长，捕获脚本异常并记录日志 <!-- comet-task:a532832f-753b-4724-b858-92c56e5b3654 -->
- [ ] 4.4 测试：和弦展开、时长不变、未选中不变、重复音符移除、异常不改铺面 <!-- comet-task:370c67e2-27db-4a12-958f-0c6aa9770fc5 -->

## 5. 集成验证

- [ ] 5.1 `.venv\Scripts\python.exe -m unittest discover -s tests -v` 全部通过 <!-- comet-task:fec3a52f-1e16-4409-b459-71c98af298fc -->
- [ ] 5.2 手动：窗口变宽后工具栏仍贴左；置顶按钮位置与行为；选中和弦执行曲谱优化后撤销/前进 <!-- comet-task:8500d5bd-e3a6-4378-9a2d-9eba86390c9b -->

```

## docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/.openspec.yaml

- Source: docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/.openspec.yaml
- Lines: 1-2
- SHA256: 81efc95b309487579cc63ceff200744cbd9fab2401597cbbdcf38d0cb54bace8

```md
schema: spec-driven
created: 2026-11-12

```

## docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/specs/arpeggiate-script/spec.md

- Source: docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/specs/arpeggiate-script/spec.md
- Lines: 1-68
- SHA256: ff2845f2bacbb1a13f024891b01e4cf7772495045c50de07e3fc19526ea4f85b

```md
# Spec Delta：曲谱优化执行项目内脚本

## Purpose

「曲谱优化」不再使用重写版算法，而是对选中音符执行项目内的 `arpeggiate.py` 原脚本，且脚本文件保持零改动。

## ADDED Requirements

### Requirement: 原脚本移入项目并仅做最小修正

项目根目录的 `arpeggiate.py` SHALL 基于用户提供的 `release/谱子/arpeggiate.py`，保留其 shebang、模块文档、参数常量（`WINDOW_BEATS`、`STEP_BEATS`、`CROSS_TRACK`、`MIN_DUR_TICKS`、`DEDUPE`）、辅助函数、`main` 与 `__main__` 入口。唯一的算法修正是：展开后保持音符时长不变——起点后移多少，结束时间也后移多少。原 `release/谱子/arpeggiate.py` MUST 被移除。

#### Scenario: 结构与参数保留

- **WHEN** 查看项目根 `arpeggiate.py`
- **THEN** 仍能看到原脚本的 shebang、五个参数常量、`extract_notes`/`dedupe`/`arpeggiate`/`rebuild`/`main` 与 `__main__` 入口

#### Scenario: 原件不再残留

- **WHEN** 查看 `release/谱子/`
- **THEN** 不再存在 `arpeggiate.py`

### Requirement: 对选中音符执行脚本

点击「曲谱优化」时，系统 SHALL 以选中音符构造临时 MIDI（每个选中音符单独一条音轨以便回读），调用脚本的 `main(src, dst)`，再把结果读回铺面；未选中的音符 MUST 保持不变。演奏模式、播放中或没有选中音符时不执行。

#### Scenario: 和弦展开

- **WHEN** 选中同一时刻的三个不同音高音符并点击「曲谱优化」
- **THEN** 三个音符按音高从低到高分别后移 0、1、2 个 1/32 拍步长，低音保持原位

#### Scenario: 未选中音符不变

- **WHEN** 只选中一小节内的和弦执行曲谱优化
- **THEN** 其它未选中音符的起点与时长完全不变

#### Scenario: 没有选中音符

- **WHEN** 铺面没有选中任何音符时点击「曲谱优化」
- **THEN** 铺面不变，日志提示先选中音符

### Requirement: 结果遵循脚本语义

读回结果后，音符的起点与时长 SHALL 与脚本输出一致：组内按音高从低到高依次后移 0、1、2… 个步长，时长保持不变（结束时间随起点后移）、展开后最小时值为 1 tick、同一音高且同一始点的重复音符只保留一个（其余从铺面移除）。展开窗口与步长均为四分音符的 1/32，tick 精度沿用脚本的 `ticks_per_beat=384` 约定。

#### Scenario: 时长不变

- **WHEN** 两个同始点、时长为 2 秒的音符被展开
- **THEN** 两个音符的时长仍为 2 秒，结束时间各自随起点后移

#### Scenario: 去除重复音符

- **WHEN** 选中两个音高与始点都相同的音符并执行曲谱优化
- **THEN** 铺面只保留一个，另一个被移除

#### Scenario: 脚本失败不改动铺面

- **WHEN** 脚本执行抛出异常或输出无法读取
- **THEN** 铺面保持原样，操作日志记录失败原因，临时文件被清理

### Requirement: 可撤销

曲谱优化的结果 SHALL 作为一次内容变更进入撤销历史，可用 Ctrl+Z 撤销、Ctrl+Shift+Z 前进。

#### Scenario: 撤销曲谱优化

- **WHEN** 执行曲谱优化后按 Ctrl+Z
- **THEN** 选中音符恢复到优化前的起点与时长，未选中音符不受影响

```

## docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/specs/editor-toolbar-layout/spec.md

- Source: docs/openspec/changes/editor-toolbar-layout-and-arpeggiate-script/specs/editor-toolbar-layout/spec.md
- Lines: 1-35
- SHA256: bf0a63421d5401dec4640987aed2e71f9f44df12c0d84b9bd6dbf29ec7914b79

```md
# Spec Delta：铺面编辑工具栏与控制面板

## Purpose

让「铺面编辑」的操作固定在容器左侧，并把「置顶」放到它所属的控制面板标题旁。

## ADDED Requirements

### Requirement: 工具栏控件贴左排列

「铺面编辑」的两行工具栏 SHALL 从容器左边缘开始依次排列：第一行的弹奏、曲谱优化、未保存标记、保存、演奏模式、演奏最低/最高键位映射，第二行的钢琴音域绝对最低/最高键、量化、BPM。两行 MUST NOT 出现把控件推向容器右侧的弹性空白。

#### Scenario: 窗口变宽

- **WHEN** 主窗口变宽
- **THEN** 工具栏控件保持贴左，相对容器左边缘的位置不变，不被拉伸或重新分布到右侧

#### Scenario: 第二行仍然贴左

- **WHEN** 打开铺面编辑
- **THEN** 钢琴音域、量化与 BPM 从容器左边缘开始排列，其后没有把控件推走的空白

### Requirement: 置顶按钮位于控制面板标题行

「置顶」按钮 SHALL 显示在左侧「🎛️ 控制面板」标题所在行的右侧，MUST NOT 再出现在「操作日志」页。点击后仍切换窗口置顶状态、按钮文字在「📌 置顶」与「📌 取消置顶」之间切换，并写入操作日志。

#### Scenario: 置顶按钮位置

- **WHEN** 打开主窗口
- **THEN** 「📌 置顶」出现在「🎛️ 控制面板」标题行右侧，操作日志页不再有该按钮

#### Scenario: 置顶行为不变

- **WHEN** 点击控制面板标题行右侧的「📌 置顶」
- **THEN** 窗口保持在其他窗口之上，按钮文字变为「📌 取消置顶」，日志记录窗口已置顶；再次点击恢复

```
