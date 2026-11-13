# 清理未使用文件

## Why

仓库里残留了构建产物、缓存、旧工作流目录与未被引用的二进制/配置，增加体积与搜索噪音，也容易让人误用旧文件。

## What Changes

- 删除可再生成的构建产物与缓存：`build/`、`dist/`、`gui.spec`、各包 `__pycache__/`、`_uac_launch_stdout.log`、`.superpowers/`。
- 删除已跟踪但未被引用的文件：`dd.54900.dll`（代码只使用 `DD.dll`）、`build_config.json`（`build_exe.py` 不读取）。
- 保留：用户曲目数据（`midi/`、`play_code/`、`release/midi`、`release/play_code`）、`release/剑网三自动演奏工具.exe`、`build.bat`、`.venv`、`.idea`、`.claude`、`docs/`、`CLAUDE.md`、`skills-lock.json`。

## 非目标

- 不删除旧归档文档、不改变 `.gitignore`、不调整构建流程与程序行为。
- 不删除 `build.bat`（仍是可用的打包快捷入口）。
