"""兼容入口：实现位于 app/ 包，测试与打包脚本仍从这里进入。"""

import sys

from app.common import *  # noqa: F401,F403
from app.main_window import MidiConverterGUI
from app.workers.batch_import import BatchConversionWorker
from app.workers.play_thread import PlayThread


def is_admin():
    """检查程序是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """请求以管理员权限重新运行程序"""
    if is_admin():
        return True
    else:
        try:
            # 获取当前脚本路径
            if getattr(sys, "frozen", False):
                # 如果是打包后的exe
                script = sys.executable
                params = " ".join(sys.argv[1:])
            else:
                # 如果是Python脚本
                script = sys.argv[0]
                params = " ".join(sys.argv[1:])

            # 使用ShellExecute以管理员权限运行
            ctypes.windll.shell32.ShellExecuteW(None, "runas", script, params, None, 1)
            return False
        except:
            return False

def main():
    """主程序入口"""
    # 检查管理员权限
    if not is_admin():
        # 如果不是管理员权限，请求重新以管理员权限运行
        if run_as_admin():
            return  # 如果已经是管理员权限，继续执行
        else:
            sys.exit(1)  # 重新启动程序或用户拒绝，退出当前实例

    # 检查并创建必要的文件夹
    from build_music import ensure_directories_exist

    ensure_directories_exist()

    app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("剑网三自动演奏工具")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Jx3 Piano")

    # 设置全局字体
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)

    # 创建并显示主窗口
    window = MidiConverterGUI()
    window.show()

    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
