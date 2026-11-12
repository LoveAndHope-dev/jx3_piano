# piano-roll-playback-assets Specification

## Purpose
TBD - created by archiving change fix-json-seek-and-assets. Update Purpose after archive.

## Requirements

### Requirement: play_code 数据时间轴从 0 开始

生成的 play_code JSON 中 `playback_data` SHALL 用整首曲子的绝对时间轴表示：若第一个可播放按键不在 0 秒，序列开头 MUST 先放入相应时长的延迟。这样按绝对时间裁剪后仍能保持与铺面时间轴一致。

#### Scenario: 首音不在 0 秒

- **WHEN** 曲目第一个可播放音符位于第 5 秒
- **THEN** JSON 的 `playback_data` 以约 5 秒的延迟开头，随后才是按键

### Requirement: 任意位置开始播放且辅助线同步

演奏时 SHALL 从播放辅助线所在绝对时间开始：丢弃该时间之前的按键；若起播点落在某个延时内部，MUST 保留该延时未走完的剩余部分（`原延时 - 已走过的时间`）作为序列开头的延时，随后按原相对时间播放其余按键。播放辅助线 MUST 从辅助线位置开始，并按已播放时长同步推进，不得因裁剪丢失延时导致按键提前。

#### Scenario: 从曲中开始

- **WHEN** 辅助线位于第 10 秒并点击弹奏
- **THEN** 只播放第 10 秒及之后的按键，辅助线从第 10 秒起与声音同步移动

#### Scenario: 起播点落在延时中间

- **WHEN** 播放数据为 `[1.0, 'Q', 1.0, 'W', 2.0, 'E']`，从 2.6 秒起播
- **THEN** 序列以 1.4 秒延时开头再接 `'E'`，按键不会提前触发

#### Scenario: 起播点正好落在延时结束

- **WHEN** 从 2.0 秒起播（第二个延时在此结束）
- **THEN** 序列为 `['W', 2.0, 'E']`，不额外插入延时

#### Scenario: 辅助线在首音之前

- **WHEN** 辅助线位于第 1 秒、首个音符在第 5 秒
- **THEN** 播放后先等待约 4 秒，辅助线同步从第 1 秒移动到第 5 秒后才开始发声

#### Scenario: 辅助线在末尾之后

- **WHEN** 辅助线位于最后一个按键之后
- **THEN** 提示当前位置之后没有可播放的按键，不开始播放

### Requirement: 自动保存与删除联动

进入演奏模式或导入曲目时 SHALL 自动保存工作 MIDI（`midi/edited/<曲目>.mid`）与 play_code JSON（`play_code/<曲目>.json`）；删除播放列表曲目时 MUST 一并删除这两份文件。

#### Scenario: 切到演奏模式保存

- **WHEN** 在编辑模式修改音符后点击「演奏模式」
- **THEN** 两份文件按当前音符与映射范围更新

#### Scenario: 删除曲目清理文件

- **WHEN** 删除某曲目
- **THEN** 它的工作 MIDI 与 play_code JSON 一并被删除

### Requirement: 吞音可见性

保存 play_code 时 SHALL 统计黄色映射框外的音符数量并在日志中提示；框内音符 MUST 全部参与按键生成（含边界 ±1 半音扩展），不得静默丢弃。

#### Scenario: 存在框外音符

- **WHEN** 曲目有音符落在黄色映射框外
- **THEN** 日志提示被跳过的音符数量与调整方法
