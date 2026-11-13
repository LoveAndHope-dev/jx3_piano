# 验收记录：play-assets-fresh-at-play

## 环境

- Windows + Python 3.14
- 测试：`.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 结果：`Ran 218 tests ... OK`

## 行为

- GUI 维护 `_play_assets_stale` 标记：
  - 音符编辑与 BPM 缩放（`notesChanged`）→ 过期；
  - 黄色音域框拖动、最低/最高映射下拉（`instrumentRangeChanged`）→ 过期；
  - 撤销/前进应用快照 → 过期；
  - 曲目加载失败、删除曲目 → 过期。
- `_save_current_play_assets()` 成功写盘后清除标记并返回是否成功。
- `_ensure_play_assets_current()`：过期或 JSON 缺失时重建 `edited/<曲目>.mid` 与 `play_code/<曲目>.json`，否则直接复用；重建失败返回 `None`，避免播放旧数据。
- `start_playing` 改为调用该函数，点击「演奏」即保证数据与界面一致。

## 覆盖

| 场景 | 测试 |
| --- | --- |
| 黄框变化标记过期 | `test_range_change_marks_play_assets_stale` |
| 映射下拉变化标记过期 | `test_combo_change_marks_play_assets_stale` |
| BPM 变化标记过期 | `test_bpm_change_marks_play_assets_stale` |
| 无变化不重复生成 / 变化后重建 | `test_ensure_play_assets_only_regenerates_when_stale` |
| 既有行为 | 其余 214 项 |

## 手动确认

- 进入演奏模式 → 拖动黄框 → 点击演奏：JSON 按新范围重建，播放范围正确。
- 演奏模式改 BPM → 点击演奏：按新速度重建。
- 不做修改连续播放：不重复写盘。

## 备注

- 打包并提交 exe（`3f982fc`）后，再次清理了 `build/`、`dist/`、`gui.spec` 与 `__pycache__`，保持仓库整洁。
