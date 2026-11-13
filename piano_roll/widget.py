"""铺面组合控件：键盘参照 + 标尺 + 画布。"""

from typing import Dict, List, Optional, Set, Tuple

from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .canvas import _PianoRollCanvas
from .geometry import KEYBOARD_WIDTH, RULER_HEIGHT
from .ruler import _PianoKeyboardWidget, _TimeRulerWidget


class PianoRollWidget(QWidget):
    """钢琴卷帘铺面编辑视图：左侧纯视觉钢琴键盘 + 右侧可编辑画布的容器；
    对外方法与信号透传给内部画布，保持与旧版本一致的公开接口。"""

    def __init__(self, mapped_pitches: Set[int], parent=None):
        super().__init__(parent)
        self._canvas = _PianoRollCanvas(mapped_pitches, parent=self)
        self._keyboard = _PianoKeyboardWidget(self._canvas, mapped_pitches, parent=self)
        self._ruler = _TimeRulerWidget(self._canvas, parent=self)

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        content.addWidget(self._keyboard)
        content.addWidget(self._canvas)

        ruler_row = QHBoxLayout()
        ruler_row.setContentsMargins(0, 0, 0, 0)
        ruler_row.setSpacing(0)
        ruler_row.addSpacing(KEYBOARD_WIDTH)
        ruler_row.addWidget(self._ruler)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(ruler_row)
        layout.addLayout(content, 1)

        # 标尺定位请求 → 播放辅助线锚点
        self._ruler.playheadRequested.connect(self._canvas.set_playhead_anchor)

        # 透传信号：直接引用内部画布的已绑定信号对象，外部 connect/emit 行为不变
        self.notesChanged = self._canvas.notesChanged
        self.instrumentRangeChanged = self._canvas.instrumentRangeChanged
        self.zoomChanged = self._canvas.zoomChanged
        self.undoRequested = self._canvas.undoRequested
        self.redoRequested = self._canvas.redoRequested

    def set_notes(self, notes: List[Dict]) -> None:
        self._canvas.set_notes(notes)

    def get_notes(self) -> List[Dict]:
        return self._canvas.get_notes()

    def set_default_track(self, track_idx: int) -> None:
        self._canvas.set_default_track(track_idx)

    def set_read_only(self, read_only: bool) -> None:
        self._canvas.set_read_only(read_only)

    def set_playhead(self, seconds: Optional[float]) -> None:
        self._canvas.set_playhead(seconds)

    def set_playhead_anchor(self, seconds: float) -> None:
        """把播放辅助线定位到指定秒数（粘贴与播放起点以此为基准）"""
        self._canvas.set_playhead_anchor(seconds)

    def get_playhead_position(self) -> float:
        """返回播放辅助线的锚点时间（秒）"""
        return self._canvas.get_playhead_position()

    def set_playhead_locked(self, locked: bool) -> None:
        """播放期间锁定标尺定位"""
        self._canvas.set_playhead_locked(locked)

    def set_beat_grid(
        self, seconds_per_beat: Optional[float], beats_per_measure: int
    ) -> None:
        """把每拍秒数与每小节拍数传给顶部标尺"""
        self._ruler.set_beat_grid(seconds_per_beat, beats_per_measure)

    def rescale_times(self, factor: float) -> None:
        """按 factor 缩放全部音符时间与播放辅助线（BPM 变更使用）"""
        self._canvas.rescale_times(factor)

    def arpeggiate_selected(self, seconds_per_beat: float) -> int:
        """对选中音符执行 1/32 拍琶音展开；返回被处理的音符数"""
        return self._canvas.arpeggiate_selected(seconds_per_beat)

    def clipboard_notes(self) -> List[Dict]:
        """返回内部剪贴板副本"""
        return self._canvas.clipboard_notes()

    def restore_clipboard(self, notes: List[Dict]) -> None:
        """恢复内部剪贴板"""
        self._canvas.restore_clipboard(notes)

    def set_instrument_range(self, low_pitch: int, high_pitch: int) -> None:
        self._canvas.set_instrument_range(low_pitch, high_pitch)

    def set_instrument_span(self, span_idx: int) -> None:
        self._canvas.set_instrument_span(span_idx)

    def set_instrument_range_visible(self, visible: bool) -> None:
        self._canvas.set_instrument_range_visible(visible)

    def get_instrument_range(self) -> Tuple[int, int]:
        return self._canvas.get_instrument_range()

    def set_quantize_grid(self, seconds: Optional[float]) -> None:
        """设置拖动量化网格间距（秒）；传 None 表示关闭量化（自由拖动）"""
        self._canvas.set_quantize_grid(seconds)

    def set_measure_grid(self, seconds_per_measure: Optional[float]) -> None:
        """设置背景小节线间距（秒）；传 None 表示不画小节线"""
        self._canvas.set_measure_grid(seconds_per_measure)
