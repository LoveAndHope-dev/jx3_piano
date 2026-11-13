# Design

- `PianoPageMixin` 新增 `self._play_assets_stale = True`：
  - `on_piano_roll_notes_changed`（含 BPM 缩放触发的 notesChanged）置 True；
  - 音域框变化置 True：让 `set_instrument_range` / `set_instrument_span` 也发出 `instrumentRangeChanged`，GUI 统一在 `_on_instrument_range_changed` 里刷新显示并置 True；
  - 曲目加载失败、清空缓存时置 True。
- `_save_current_play_assets()` 成功写盘后置 False，并返回是否成功。
- 新增 `_ensure_play_assets_current()`：过期或文件缺失时调用保存；返回可用的 `play_data`（或 None）。
- `start_playing` 用 `_ensure_play_assets_current()` 取代「读取 + 缺失兜底」，保证使用最新数据。
- 不引入哈希：以 GUI 内已知的变更事件驱动脏标记，开销最低；所有内容变更都经过 `notesChanged`，范围变更集中到 `instrumentRangeChanged`。

验证：
- 黄框拖动/下拉变化 → 脏标记为 True；再次保存后为 False。
- 未变化时确保函数不重复调用保存。
- 完整测试回归。
