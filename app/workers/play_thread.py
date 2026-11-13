"""播放线程：在内存中把 play_code 数据交给 JX3Player。"""

from PyQt5.QtCore import QThread, pyqtSignal


class PlayThread(QThread):
    """使用新播放器模块的播放线程；播放数据在内存中生成，不经过任何文件"""

    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(float)  # 距实际播放开始的已耗时秒数
    finished_signal = pyqtSignal(bool)  # True=正常完成, False=被中断

    def __init__(self, data: dict):
        super().__init__()
        self.data = data
        self.player = None
        self.should_stop = False

    def run(self):
        try:
            # 导入播放器模块
            from player import JX3Player

            # 创建播放器实例，设置日志回调与进度回调
            self.player = JX3Player(
                log_callback=self.log_signal.emit,
                progress_callback=self.progress_signal.emit,
            )

            # 开始播放（直接使用内存数据，不读取文件）
            success = self.player.play_from_data(
                self.data, start_at=float(self.data.get("start_at", 0.0))
            )

            self.finished_signal.emit(success)

        except Exception as e:
            self.log_signal.emit(f"❌ 播放器启动失败: {e}")
            self.finished_signal.emit(False)

    def stop(self):
        """停止播放"""
        self.should_stop = True
        if self.player:
            self.player.stop()

        self.log_signal.emit("🛑 正在停止播放...")

        # 等待线程结束
        if self.isRunning():
            self.wait(3000)  # 等待最多3秒
            if self.isRunning():
                self.terminate()  # 强制终止
