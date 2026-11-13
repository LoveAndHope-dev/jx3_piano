"""兼容入口：实现位于 app/ 包，测试与打包脚本仍从这里进入。

注意：运行目录的唯一受支持替换点是 ``music.paths.get_midi_dir_path`` /
``music.paths.get_play_code_dir_path``；``gui.get_midi_dir_path`` 只是只读转发，
替换它不会影响运行时与后台线程。
"""

from app.common import *  # noqa: F401,F403
from app.entry import is_admin, main, run_as_admin
from app.main_window import MidiConverterGUI
from app.workers.batch_import import BatchConversionWorker
from app.workers.play_thread import PlayThread


if __name__ == "__main__":
    main()
