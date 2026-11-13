# Spec Delta：播放资产一致性

## Purpose

保证点击「演奏」时使用的 `play_code` 数据与当前铺面、黄框、BPM 一致。

## ADDED Requirements

### Requirement: 播放前按需重建 play_code

点击「演奏」时，若自上次生成后发生过以下任一变化，SHALL 先重新生成 `midi/edited/<曲目>.mid` 与 `play_code/<曲目>.json` 再开始播放：

- 音符内容变化（新增/删除/移动/时长/移调/曲谱优化，以及 BPM 缩放）；
- 黄色音域框边界或演奏最低/最高键位映射变化；
- 曲目切换后尚未生成；
- JSON 文件缺失。

未发生变化时 MUST 直接复用现有文件，不得重复写盘。

#### Scenario: 黄框在演奏模式内被拖动

- **WHEN** 进入演奏模式后拖动黄框，再点击「演奏」
- **THEN** 先按新的黄框范围重新生成 JSON，再开始播放

#### Scenario: 演奏模式内修改 BPM

- **WHEN** 进入演奏模式后修改 BPM，再点击「演奏」
- **THEN** 重新生成 JSON，播放使用新的时间轴

#### Scenario: 无变化时直接播放

- **WHEN** 进入演奏模式后未做任何修改，直接点击「演奏」
- **THEN** 复用现有 JSON，不产生额外写盘
