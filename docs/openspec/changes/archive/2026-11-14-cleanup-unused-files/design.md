# Design

- 删除前确认引用：`build_exe.py` 只引用 `gui.py`、`build_music.py`、`pydd.py`、`DD.dll`、`icon.ico`，不读取 `build_config.json`；`dd.54900.dll` 在所有源码中无引用。
- 生成物由 PyInstaller 在打包时重建，删除 `build/`、`dist/`、`gui.spec` 不影响源码。
- 保留用户数据目录与已提交的 `release/*.exe`。
- 验证：完整测试 214 项；`python -c "import gui, build_music, piano_roll"`；不重新打包（避免仅因时间戳产生 exe 差异），但保持 `build_exe.py` 入口未变。
