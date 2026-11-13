"""钢琴键盘参照与顶部时间标尺。"""

from typing import Optional, Set

from PyQt5.QtCore import QPoint, QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QSizePolicy, QWidget

from .geometry import (
    KEYBOARD_WIDTH,
    MAX_PITCH,
    MIN_MEASURE_SECONDS,
    MIN_PITCH,
    PITCH_COUNT,
    ROW_HEIGHT,
    RULER_HEIGHT,
    _is_black_key,
)


class _PianoKeyboardWidget(QWidget):
    """铺面左侧的竖直钢琴键盘：纯视觉参照，固定贴在视图左边缘，随铺面纵向滚动
    一起滚动，不随铺面横向（时间轴）滚动移动；不接受任何鼠标事件。"""

    def __init__(self, canvas: "_PianoRollCanvas", mapped_pitches: Set[int], parent=None):
        super().__init__(parent)
        self._canvas = canvas
        self._mapped_pitches = mapped_pitches
        self.setFixedWidth(KEYBOARD_WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        canvas.verticalScrollBar().valueChanged.connect(self._on_canvas_scrolled)

    def _on_canvas_scrolled(self, _value=None) -> None:
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        width = self.width()
        height = self.height()
        painter.fillRect(0, 0, width, height, QColor("#F5F2EA"))

        top_scene_y = self._canvas.mapToScene(QPoint(0, 0)).y()
        first_index = max(0, int(top_scene_y // ROW_HEIGHT))

        i = first_index
        while True:
            pitch = MAX_PITCH - i
            if pitch < MIN_PITCH:
                break
            row_top_scene_y = i * ROW_HEIGHT
            y = row_top_scene_y - top_scene_y
            if y > height:
                break

            if _is_black_key(pitch):
                color = QColor("#1B1B1B")
                if pitch not in self._mapped_pitches:
                    color = color.lighter(150)
                bx = int(width * 0.42)
                bw = width - bx
                by = int(y) + 1
                bh = max(1, ROW_HEIGHT - 2)
                painter.fillRect(bx, by, bw, bh, color)

            i += 1

        painter.setPen(QPen(QColor("#0F1720"), 1))
        painter.drawLine(width - 1, 0, width - 1, height)
        painter.end()


class _TimeRulerWidget(QWidget):
    """钢琴窗顶部的固定拍数标尺：显示小节/拍刻度，点击或拖动定位播放辅助线。"""

    playheadRequested = pyqtSignal(float)

    def __init__(self, canvas: "_PianoRollCanvas", parent=None):
        super().__init__(parent)
        self._canvas = canvas
        self._seconds_per_beat: Optional[float] = None
        self._beats_per_measure = 4
        self.setFixedHeight(RULER_HEIGHT)
        self.setMouseTracking(True)
        canvas.zoomChanged.connect(self._on_canvas_changed)
        canvas.horizontalScrollBar().valueChanged.connect(self._on_canvas_changed)
        canvas.horizontalScrollBar().rangeChanged.connect(self._on_canvas_changed)

    def _on_canvas_changed(self, *_args) -> None:
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self.update()
        super().resizeEvent(event)

    def _viewport_origin(self) -> float:
        """画布视口左边缘在本标尺坐标系中的 x。

        标尺与画布在 `PianoRollWidget` 中左边缘对齐（同一 KEYBOARD_WIDTH 缩进），
        因此这里只需补上画布自身的边框宽度；调用 QWidget.mapTo 在绘制期间
        会导致 PyQt 崩溃，不能用它做实时换算。
        """
        return float(self._canvas.frameWidth())

    def _viewport_width(self) -> float:
        return float(self._canvas.viewport().width())

    def _tick_x(self, seconds: float) -> float:
        return self._viewport_origin() + self._canvas.viewport_x_for_time(seconds)

    def _time_at_x(self, x: float) -> float:
        local = max(0.0, min(float(x) - self._viewport_origin(), self._viewport_width()))
        return self._canvas.time_at_viewport_x(local)

    def set_beat_grid(
        self, seconds_per_beat: Optional[float], beats_per_measure: int
    ) -> None:
        """设置每拍秒数与每小节拍数；缺少节拍信息时标尺退化为按秒标注。"""
        self._seconds_per_beat = (
            seconds_per_beat if (seconds_per_beat and seconds_per_beat > 0) else None
        )
        self._beats_per_measure = max(1, int(beats_per_measure))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1B2631"))
        pps = self._canvas.pixels_per_second()
        if pps <= 0 or self.width() <= 0 or self._viewport_width() <= 0:
            painter.end()
            return

        start_time = self._canvas.time_at_viewport_x(0.0)
        end_time = self._canvas.time_at_viewport_x(self._viewport_width())
        seconds_per_measure = (
            self._seconds_per_beat * self._beats_per_measure
            if self._seconds_per_beat
            else None
        )

        if seconds_per_measure:
            measure = int(start_time // seconds_per_measure)
            # 安全上限：避免异常 BPM/拍号画出海量刻度
            count = 0
            while measure * seconds_per_measure <= end_time and count < 5000:
                self._draw_tick(
                    painter, measure * seconds_per_measure, str(measure + 1), tall=True
                )
                if self._seconds_per_beat:
                    base = measure * seconds_per_measure
                    for beat in range(1, self._beats_per_measure):
                        self._draw_tick(
                            painter, base + beat * self._seconds_per_beat, "", tall=False
                        )
                measure += 1
                count += 1
        else:
            second = int(start_time)
            while second <= end_time and second - int(start_time) < 5000:
                self._draw_tick(painter, float(second), f"{second}s", tall=True)
                second += 1

        painter.end()

    def _draw_tick(self, painter: QPainter, seconds: float, text: str, tall: bool) -> None:
        origin = self._viewport_origin()
        right = origin + self._viewport_width()
        x = self._tick_x(seconds)
        if x < origin - 40 or x > right + 40:
            return
        top = 0 if tall else RULER_HEIGHT - 8
        painter.setPen(QPen(QColor("#85929E" if tall else "#4D5656"), 1))
        painter.drawLine(int(x), top, int(x), RULER_HEIGHT - 1)
        if text:
            painter.setPen(QPen(QColor("#D5D8DC"), 1))
            painter.drawText(int(x) + 3, 12, text)

    def _should_ignore_mouse(self) -> bool:
        # 只在播放期间锁定标尺定位；演奏模式（只读）仍允许定位播放辅助线
        return self._canvas.is_playhead_locked()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or self._should_ignore_mouse():
            return
        self.playheadRequested.emit(self._time_at_x(float(event.pos().x())))

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self._should_ignore_mouse():
            return
        self.playheadRequested.emit(self._time_at_x(float(event.pos().x())))
