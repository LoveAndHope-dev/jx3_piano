---
comet_change: editor-toolbar-layout-and-arpeggiate-script
role: technical-design
canonical_spec: openspec
archived-with: 2026-11-12-editor-toolbar-layout-and-arpeggiate-script
status: final
---

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

- 单元：`arpeggiate_runner` 的和弦展开、时长不变（结束时间随起点后移）、未选中不变、重复音符移除、无效拍长返回副本。
- 脚本一致性：断言根目录 `arpeggiate.py` 保留原脚本的结构与常量（shebang、`WINDOW_BEATS = 1 / 32`、`STEP_BEATS`、`def main(src, dst)`、四个辅助函数），且不再包含旧的重写实现。
- GUI：曲谱优化按钮仍进入撤销历史；无选中时提示且铺面不变；脚本异常时铺面不变。
- 布局：offscreen 下断言两行工具栏的首个控件 `x()` 与容器左内边距一致、末尾控件之后存在弹性空白；置顶按钮位于控制面板标题行且日志页不再包含它。
- 回归：现有 157 项测试。
