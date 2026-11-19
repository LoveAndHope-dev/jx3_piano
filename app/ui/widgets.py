"""自绘控件：带勾选标记的复选框、悬停滚动标签。"""

from app.common import *  # noqa: F401,F403
from app.ui import theme


def _token_color(value) -> QColor:
    """把主题令牌（#rrggbb 或 rgba()）转成 QColor。"""
    text = str(value).strip()
    if text.startswith("rgba(") and text.endswith(")"):
        parts = [part.strip() for part in text[5:-1].split(",")]
        if len(parts) == 4:
            red, green, blue = (int(float(part)) for part in parts[:3])
            alpha = int(round(float(parts[3]) * 255))
            return QColor(red, green, blue, alpha)
    return QColor(text)


class AntCheckBox(QCheckBox):
    """14px 方框 + 白色勾选折线，颜色跟随当前主题令牌。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QCheckBox::indicator { width: 0px; height: 0px; }")

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        tokens = theme.current_tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        checked = self.isChecked()
        box = QRectF(2.0, 2.0, 14.0, 14.0)
        if checked:
            fill = QColor(str(tokens["colorPrimary"]))
            border = fill
        else:
            fill = QColor(str(tokens["colorBgBase"]))
            border = QColor(str(tokens["colorBorder"]))

        painter.setPen(QPen(border, 1))
        painter.setBrush(fill)
        painter.drawRoundedRect(box, 2.0, 2.0)

        if checked:
            pen = QPen(QColor(str(tokens["colorTextLightSolid"])), 2)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(5.0, 9.2)
            path.lineTo(8.0, 12.0)
            path.lineTo(13.0, 6.5)
            painter.drawPath(path)

        painter.end()


class MarqueeLabel(QLabel):
    """文字超出宽度时，悬停后缓慢向左循环滚动。"""

    STEP_MS = 40
    GAP = 48
    PAUSE_TICKS = 25  # 1s

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._offset = 0
        self._pause_ticks = 0
        self._timer = QTimer(self)
        self._timer.setInterval(self.STEP_MS)
        self._timer.timeout.connect(self._tick)

    def is_scrolling(self) -> bool:
        return self._timer.isActive()

    def start_marquee(self) -> None:
        if self._timer.isActive():
            return
        if self.fontMetrics().horizontalAdvance(self.text()) <= self.width():
            return
        self._offset = 0
        self._pause_ticks = 0
        self._timer.start()
        self.update()

    def stop_marquee(self) -> None:
        self._timer.stop()
        if self._offset:
            self._offset = 0
            self.update()

    def _tick(self) -> None:
        if self._pause_ticks > 0:
            self._pause_ticks -= 1
            return
        width = self.fontMetrics().horizontalAdvance(self.text())
        if self._offset >= width + self.GAP:
            self._offset = 0
            self._pause_ticks = self.PAUSE_TICKS
        else:
            self._offset += 1
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if not self._timer.isActive() and self._offset == 0:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setPen(_token_color(theme.current_tokens()["colorText"]))
        metrics = self.fontMetrics()
        width = metrics.horizontalAdvance(self.text())
        flags = Qt.AlignVCenter | Qt.AlignLeft
        painter.drawText(
            QRectF(-self._offset, 0, width, self.height()), flags, self.text()
        )
        painter.drawText(
            QRectF(self.width() + self.GAP - self._offset, 0, width, self.height()),
            flags,
            self.text(),
        )
        painter.end()
