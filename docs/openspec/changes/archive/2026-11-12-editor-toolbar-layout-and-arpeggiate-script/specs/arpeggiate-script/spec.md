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
