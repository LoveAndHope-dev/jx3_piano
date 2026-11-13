"""操作日志页。"""

from app.common import *  # noqa: F401,F403


class LogPageMixin:
    def _setup_log_tab(self):
        """构建「操作日志」标签页"""
        log_tab = QWidget()
        log_tab_layout = QVBoxLayout(log_tab)
        log_tab_layout.setContentsMargins(0, 0, 0, 0)

        # 日志标题和功能按钮
        log_header = QHBoxLayout()

        log_label = QLabel("📋 操作日志")
        log_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        log_header.addWidget(log_label)

        log_header.addStretch()

        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.setObjectName("clearBtn")
        self.clear_btn.clicked.connect(self.clear_log)
        log_header.addWidget(self.clear_btn)

        log_tab_layout.addLayout(log_header)

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_tab_layout.addWidget(self.log_text)

        self.right_tabs.addTab(log_tab, "📋 操作日志")

    def log(self, message: str):
        """添加日志信息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        # 添加到日志框
        self.log_text.append(log_message)

        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.log("📋 日志已清空")

    def toggle_topmost(self):
        """切换窗口置顶状态"""
        if self.topmost_btn.isChecked():
            # 设置窗口置顶
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.show()
            self.topmost_btn.setText("📌 取消置顶")
            self.log("📌 窗口已置顶")
        else:
            # 取消窗口置顶
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.show()
            self.topmost_btn.setText("📌 置顶")
            self.log("📌 窗口已取消置顶")
