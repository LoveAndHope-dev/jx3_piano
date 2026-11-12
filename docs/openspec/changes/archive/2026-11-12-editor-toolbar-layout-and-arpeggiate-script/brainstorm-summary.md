# 设计探索摘要（Design）

change: `editor-toolbar-layout-and-arpeggiate-script`

## 已确认（用户）

- 工具栏：两行都保留，全部贴左，窗口变宽时不漂移（不采用逐像素坐标）
- 置顶按钮：控制面板标题行右侧
- 曲谱优化：临时 MIDI 往返执行原脚本；脚本移入项目，只修正「展开后时长不变」（起点与结束时间同步后移），tick 精度沿用脚本的 `ticks_per_beat=384` 约定；保留去重；原 `release/谱子/arpeggiate.py` 真正移动（删除原件）

## 现状事实

- 第一行工具栏在「曲谱优化」后 `addStretch()`，把保存/演奏模式/键位映射推到右侧
- 置顶按钮在 `_setup_log_tab` 的标题行；`toggle_topmost` 只依赖按钮状态
- `release/谱子/arpeggiate.py` 是 mido 脚本，`main(src, dst)` 读写 MIDI，模块只在 `__main__` 下执行
- 现项目根 `arpeggiate.py` 是重写版 `arpeggiate_notes`（时长不变语义）
- 音符为 `{id, pitch, start, duration, track, mapped}`（秒）；`arpeggiate_selected` 负责重建图形、扩展场景、发 `notesChanged`
- mido 1.3.3 已是依赖；windowed 打包下 `sys.stdout` 可能为 None

## 候选方案

1. 行尾 stretch：控件按 sizeHint 贴左，多余宽度由行尾空白吸收；不写死坐标
2. 控制面板改 QFrame + 标题行（标题 + stretch + 置顶按钮），QSS 复用分组框风格
3. 原脚本移入并做一处最小修正（时长不变），删除原件
4. 新增 `arpeggiate_runner.py`：tpb=384（脚本约定），每个选中音符独立音轨以便回读；重定向 stdout；临时目录自动清理
5. 铺面只替换 `arpeggiate_notes` 来源；GUI 传四分音符拍长并捕获异常

## 备选

| 备选 | 原因 |
| --- | --- |
| setGeometry 绝对坐标 | DPI/字体变化会重叠 |
| 合并成一行 | 控件过多，窄窗口显示不全 |
| 调用脚本内部函数而非 main | 需要构造 mido 轨道，等价但代码更多 |
| 保留 release 副本 | 与「移动」冲突，且会出现两份权威版本 |

## 风险

- tick 量化约 1/384 拍（120 BPM 时约 2.6 ms），与脚本约定一致
- 脚本只改时长语义一处；结构与参数保留，用测试固定
- 同音高同起点会被去重删除
- 打包需确认脚本被收集（gui 直接 import runner，runner import arpeggiate）

## Spec Patch

无。

## 未决问题

无。
