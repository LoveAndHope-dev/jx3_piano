"""
剑网三自动演奏播放器模块
负责读取数据文件并执行播放操作
"""

import time
import json
import os
import sys
from datetime import datetime
from typing import List, Optional, Callable


class JX3Player:
    """剑网三自动演奏播放器"""

    def __init__(self, log_callback: Optional[Callable] = None):
        """
        初始化播放器

        Args:
            log_callback: 日志回调函数，用于向GUI发送日志信息
        """
        self.log_callback = log_callback
        self.should_stop = False
        self.dd = None
        self.keyboard = None

        # 初始化DD驱动
        self._init_dd_driver()

        # 初始化keyboard模块
        self._init_keyboard()

    def _init_dd_driver(self):
        """初始化DD驱动"""
        try:
            from pydd import PyDD

            # 确定DLL路径
            if getattr(sys, "frozen", False):
                # 打包环境，DLL在临时目录
                dll_path = os.path.join(sys._MEIPASS, "DD.dll")
            else:
                # 开发环境
                dll_path = "./DD.dll"

            self.dd = PyDD(dll_path)
            self._log("✅ 按键模拟模块加载成功")

        except Exception as e:
            self._log(f"❌ 按键模拟模块加载失败: {e}")
            raise

    def _init_keyboard(self):
        """初始化keyboard模块"""
        try:
            import keyboard

            self.keyboard = keyboard
            self._log("✅ 键盘监听模块加载成功，按ESC可停止播放")
        except ImportError:
            self.keyboard = None
            self._log("⚠️ 警告: 找不到keyboard模块，无法使用ESC停止功能")

    def _log(self, message: str):
        """输出日志"""
        if self.log_callback:
            self.log_callback(message)
        else:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")

    def stop(self):
        """停止播放"""
        self.should_stop = True
        self._log("🛑 收到停止信号")

    def is_stop_requested(self) -> bool:
        """检查是否请求停止"""
        if self.should_stop:
            return True

        # 检查ESC键
        if self.keyboard and hasattr(self.keyboard, "is_pressed"):
            try:
                if self.keyboard.is_pressed("esc"):
                    self._log("🛑 检测到ESC键，停止播放")
                    return True
            except:
                pass

        return False

    def countdown(self, seconds: int = 3) -> bool:
        """
        播放前倒计时

        Args:
            seconds: 倒计时秒数

        Returns:
            bool: True表示倒计时完成，False表示被中断
        """
        self._log("🎵 准备开始播放...")
        self._log("💡 按ESC键可随时停止播放")
        self._log("")

        for i in range(seconds, 0, -1):
            if self.is_stop_requested():
                self._log("🛑 倒计时期间检测到停止信号，取消播放!")
                return False

            self._log(f"⏰ {i}秒后开始播放...")

            # 使用小步长sleep，以便及时响应停止信号
            for _ in range(10):  # 每秒分成10次检查
                if self.is_stop_requested():
                    self._log("🛑 倒计时期间检测到停止信号，取消播放!")
                    return False
                time.sleep(0.1)

        self._log("🎶 开始播放!")
        self._log("")
        return True

    def play_data_file(self, data_file_path: str) -> bool:
        """
        播放数据文件

        Args:
            data_file_path: 数据文件路径

        Returns:
            bool: True表示播放完成，False表示被中断或出错
        """
        try:
            # 读取数据文件
            with open(data_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 获取播放数据和元信息
            playback_data = data.get("playback_data", [])
            metadata = data.get("metadata", {})

            self._log(f"📊 曲目信息:")
            self._log(f"  🎵 名称: {metadata.get('filename', '未知')}")
            self._log(f"  🎼 移调: {metadata.get('transpose', 0)}半音")
            self._log(f"  🎹 音轨: {metadata.get('processed_tracks', [])}")
            self._log(f"  🔢 操作数: {len(playback_data)}")
            self._log("")

            # 倒计时
            if not self.countdown():
                return False

            # 开始播放
            return self._execute_playback_data(playback_data)

        except Exception as e:
            self._log(f"❌ 播放数据文件失败: {e}")
            return False

    def _execute_playback_data(self, playback_data: List) -> bool:
        """
        执行播放数据

        Args:
            playback_data: 播放数据列表

        Returns:
            bool: True表示播放完成，False表示被中断
        """
        if not playback_data:
            self._log("⚠️ 播放数据为空")
            return False

        start_time = time.time()
        key_count = 0
        delay_count = 0

        # 按键映射说明
        self._log("🎹 按键映射:")
        self._log("  高音12345 = 12345")
        self._log("  中音1234567 = QWERTYU")
        self._log("  低音1234567 = ASDFGHJ")
        self._log("  倍低音567 = BNM")
        self._log("  升半音 = +, 降半音 = -")
        self._log("")

        total_items = len(playback_data)

        for i, item in enumerate(playback_data):
            # 检查停止信号
            if self.is_stop_requested():
                self._log("🛑 播放被中断")
                return False

            # 进度显示（每100个操作显示一次）
            if i % 100 == 0:
                progress = (i / total_items) * 100
                self._log(f"⏳ 播放进度: {progress:.1f}% ({i}/{total_items})")

            if isinstance(item, (int, float)):
                # 延迟操作
                if item > 0:
                    delay_count += 1
                    # 使用小步长延迟，以便响应停止信号
                    remaining_delay = float(item)
                    while remaining_delay > 0 and not self.is_stop_requested():
                        step = min(0.01, remaining_delay)  # 最多10ms一步
                        time.sleep(step)
                        remaining_delay -= step

                    if self.is_stop_requested():
                        self._log("🛑 播放被中断")
                        return False

            elif isinstance(item, str):
                # 按键操作
                try:
                    key_count += 1
                    if len(item) > 1:
                        # 组合按键
                        for key in item:
                            self.dd.key_press(key)
                    else:
                        # 普通按键
                        self.dd.key_press(item)
                except Exception as e:
                    self._log(f"⚠️ 按键 {item} 执行失败: {e}")

        # 播放完成统计
        elapsed = time.time() - start_time
        self._log("✅ 播放完成")
        self._log(f"⏱️ 总播放时长: {elapsed:.1f}秒")
        self._log(f"🎹 共执行 {key_count} 个按键操作")
        self._log(f"⏰ 共处理 {delay_count} 个延迟操作")

        return True

    def play_from_json(self, json_file_path: str) -> bool:
        """
        从完整JSON文件开始播放

        Args:
            json_file_path: 完整数据文件路径 (xxx.json)

        Returns:
            bool: True表示播放完成，False表示被中断或出错
        """
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 检查文件格式
            if data.get("type") != "jx3_piano_complete" or data.get("version") != "2.0":
                self._log(f"❌ 不支持的文件格式: {json_file_path}")
                return False

            # 获取播放数据
            playback_data = data.get("playback_data", [])
            if not playback_data:
                self._log("❌ 播放数据为空")
                return False

            # 显示文件信息
            filename = data.get("filename", "未知")
            transpose = data.get("transpose", 0)
            stats = data.get("statistics", {})

            self._log(f"🎵 曲目: {filename}")
            if transpose != 0:
                self._log(f"� 移调: {transpose}半音")
            self._log(
                f"📊 统计: {stats.get('operation_count', 0)}个操作, {stats.get('key_count', 0)}个按键, {stats.get('delay_count', 0)}个延迟"
            )
            self._log("")

            # 倒计时
            if not self.countdown():
                return False

            # 执行播放
            return self._execute_playback_data(playback_data)

        except Exception as e:
            self._log(f"❌ 播放失败: {e}")
            return False

    def play_from_info(self, info_file_path: str) -> bool:
        """
        从信息文件开始播放（自动查找对应的数据文件）
        保留此方法用于向后兼容

        Args:
            info_file_path: 信息文件路径 (xxx_info.json)

        Returns:
            bool: True表示播放完成，False表示被中断或出错
        """
        try:
            # 计算数据文件路径
            data_file_path = info_file_path.replace("_info.json", "_data.json")

            if not os.path.exists(data_file_path):
                self._log(f"❌ 找不到数据文件: {data_file_path}")
                return False

            return self.play_data_file(data_file_path)

        except Exception as e:
            self._log(f"❌ 播放失败: {e}")
            return False


# 用于测试的主函数
if __name__ == "__main__":

    def test_log(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")

    # 创建播放器实例
    player = JX3Player(log_callback=test_log)

    # 测试播放
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if file_path.endswith(".json"):
            player.play_from_json(file_path)
        else:
            player.play_data_file(file_path)
    else:
        print("用法: python player.py <JSON文件路径>")
