"""程序入口：管理员权限检查与应用启动。"""

import ctypes
import sys

from app.common import QApplication, QFont
from app.main_window import MidiConverterGUI


def is_admin():
    """检查程序是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    """请求以管理员权限重新运行程序"""
    if is_admin():
        return True
    try:
        if getattr(sys, "frozen", False):
            script = sys.executable
        else:
            script = sys.argv[0]
        params = " ".join(sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", script, params, None, 1)
        return False
    except Exception:
        return False


def main():
    """主程序入口"""
    if not is_admin():
        if run_as_admin():
            return
        sys.exit(1)

    from build_music import ensure_directories_exist

    ensure_directories_exist()

    app = QApplication(sys.argv)
    app.setApplicationName("剑网三自动演奏工具")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Jx3 Piano")
    app.setFont(QFont("Microsoft YaHei UI", 10))

    window = MidiConverterGUI()
    window.show()
    sys.exit(app.exec_())
