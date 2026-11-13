# repository-hygiene Specification

## Purpose
仓库只保留运行、构建与协作所需的文件。

## Requirements

### Requirement: 不保留未使用的生成物与未引用文件

仓库 SHALL NOT 包含可再生成的构建产物与缓存（`build/`、`dist/`、`gui.spec`、`__pycache__`、启动日志、旧工作流残留），也 SHALL NOT 包含代码未引用的 `dd.54900.dll` 与 `build_config.json`。删除后 MUST 保证程序导入、测试与打包流程仍然可用。

#### Scenario: 清理后测试通过

- **WHEN** 删除上述文件后运行完整测试
- **THEN** 所有测试通过，`import gui`、`build_music`、`piano_roll` 正常

#### Scenario: 构建可重新生成

- **WHEN** 之后执行 `build_exe.py`
- **THEN** `build/`、`dist/` 与 `gui.spec` 会重新生成，发布 exe 正常产出
