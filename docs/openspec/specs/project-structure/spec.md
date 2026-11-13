# project-structure Specification

## Purpose
让每个模块只承担一类职责，改代码时能在千行以内的文件里定位；公开入口保持不变。

## Requirements

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
