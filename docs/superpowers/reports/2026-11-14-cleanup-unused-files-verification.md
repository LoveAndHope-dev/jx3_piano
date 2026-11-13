# 验收记录：cleanup-unused-files

## 环境

- Windows + Python 3.14
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 214 tests ... OK`

## 删除内容

| 类型 | 文件/目录 | 说明 |
| --- | --- | --- |
| 构建产物 | `build/`（14 个文件）、`dist/gui.exe` | PyInstaller 打包时重新生成 |
| 构建配置 | `gui.spec` | 每次打包自动生成 |
| 缓存 | 根目录及 `app/`、`app/ui/`、`app/workers/`、`music/`、`piano_roll/`、`tests/` 的 `__pycache__` | Python 自动重建 |
| 日志 | `_uac_launch_stdout.log` | UAC 启动残留 |
| 旧工作流 | `.superpowers/sdd/.gitignore` | 已废弃的 Superpowers 目录 |
| 未引用二进制 | `dd.54900.dll`（4.7 MB） | 源码无引用，实际使用 `DD.dll` |
| 未引用配置 | `build_config.json` | `build_exe.py` 硬编码参数，不读取 |

## 保留内容

- 用户曲目数据：`midi/`、`play_code/`、`release/midi`、`release/play_code`
- `release/剑网三自动演奏工具.exe`
- `build.bat`（打包快捷入口）、`build_exe.py`、`DD.dll`、`icon.ico`
- `.venv`、`.idea`、`.claude`、`.comet`、`docs/`、`CLAUDE.md`、`skills-lock.json`

## 验证

- 完整测试 214 项通过（删除缓存后重新编译）。
- `import gui, build_music, piano_roll, music` 正常。
- `build_exe.py` 所需文件（`gui.py`、`build_music.py`、`pydd.py`、`DD.dll`、`icon.ico`）均存在，后续打包可重新生成 `build/`、`dist/`、`gui.spec`。
- 工作区无残留的构建/缓存文件。

## 备注

- 提交 `7047034` 同时带入了此前工作区中未提交的 `.comet/config.yaml`（移除 native 工作流配置）；该修改与当前 classic-only 配置一致，已一并提交。
- 未删除 2026-11-11 的旧归档文档（按用户选择保留）。
