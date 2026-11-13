"""Ant Design（深色）设计令牌与全局样式。

界面只从这里取颜色、间距、圆角、字号与控件高度，避免样式散落在各处。
"""

from __future__ import annotations

from typing import Dict

TOKENS: Dict[str, object] = {
    # 颜色
    "colorPrimary": "#1677ff",
    "colorPrimaryHover": "#4096ff",
    "colorPrimaryActive": "#0958d9",
    "colorBgBase": "#141414",
    "colorBgContainer": "#1f1f1f",
    "colorBgElevated": "#262626",
    "colorBorder": "#424242",
    "colorBorderSecondary": "#303030",
    "colorText": "rgba(255,255,255,0.85)",
    "colorTextSecondary": "rgba(255,255,255,0.65)",
    "colorTextTertiary": "rgba(255,255,255,0.45)",
    "colorTextDisabled": "rgba(255,255,255,0.25)",
    "colorSuccess": "#49aa19",
    "colorWarning": "#d89614",
    "colorError": "#dc4446",
    "colorInfo": "#1677ff",
    # 圆角与尺寸
    "radiusSM": 4,
    "radius": 6,
    "radiusLG": 8,
    "controlHeight": 32,
    "fontSizeSM": 12,
    "fontSize": 14,
    "fontSizeLG": 16,
    "fontSizeHeading": 20,
    "spaceXS": 4,
    "spaceSM": 8,
    "spaceMD": 12,
    "spaceLG": 16,
    "spaceXL": 24,
}

REQUIRED_TOKEN_KEYS = (
    "colorPrimary",
    "colorBgBase",
    "colorBgContainer",
    "colorBorder",
    "colorText",
    "colorSuccess",
    "colorWarning",
    "colorError",
    "radius",
    "controlHeight",
    "fontSize",
    "spaceLG",
)


def build_stylesheet(tokens: Dict[str, object] = TOKENS) -> str:
    """按令牌生成全局 QSS。"""
    t = tokens
    return f"""
        QMainWindow {{
            background-color: {t['colorBgBase']};
        }}

        QWidget {{
            background-color: transparent;
            color: {t['colorText']};
            font-family: 'Microsoft YaHei UI', 'Segoe UI', Arial;
            font-size: {t['fontSize']}px;
        }}

        QPushButton {{
            background-color: {t['colorBgContainer']};
            border: 1px solid {t['colorBorder']};
            border-radius: {t['radius']}px;
            color: {t['colorText']};
            font-weight: normal;
            font-size: {t['fontSize']}px;
            padding: 0 {t['spaceMD']}px;
            min-height: {t['controlHeight'] - 2}px;
            max-height: {t['controlHeight'] - 2}px;
        }}

        QPushButton:hover {{
            border-color: {t['colorPrimary']};
            color: {t['colorPrimary']};
        }}

        QPushButton:pressed {{
            border-color: {t['colorPrimaryActive']};
            color: {t['colorPrimaryActive']};
        }}

        QPushButton:disabled {{
            color: {t['colorTextDisabled']};
            border-color: {t['colorBorderSecondary']};
            background-color: transparent;
        }}

        QPushButton#importBtn {{
            background-color: {t['colorSuccess']};
            border-color: {t['colorSuccess']};
            color: #ffffff;
            font-weight: 600;
        }}

        QPushButton#importBtn:hover {{
            background-color: #5cb824;
            border-color: #5cb824;
            color: #ffffff;
        }}

        QPushButton#playBtn {{
            background-color: {t['colorPrimary']};
            border-color: {t['colorPrimary']};
            color: #ffffff;
            min-width: 56px;
            font-size: {t['fontSize']}px;
            font-weight: 600;
        }}

        QPushButton#playBtn:hover {{
            background-color: {t['colorPrimaryHover']};
            border-color: {t['colorPrimaryHover']};
            color: #ffffff;
        }}

        QPushButton#stopBtn {{
            background-color: {t['colorError']};
            border-color: {t['colorError']};
            color: #ffffff;
            font-weight: 600;
        }}

        QPushButton#stopBtn:hover {{
            background-color: #e05a5c;
            border-color: #e05a5c;
            color: #ffffff;
        }}

        QPushButton#refreshBtn {{
            min-width: {t['controlHeight'] - 2}px;
            max-width: {t['controlHeight'] - 2}px;
            padding: 0;
            font-size: {t['fontSize']}px;
        }}

        QPushButton#clearBtn {{
            min-height: 24px;
            max-height: 24px;
            padding: 0 {t['spaceSM']}px;
            font-size: {t['fontSizeSM']}px;
            color: {t['colorTextSecondary']};
        }}

        QPushButton#clearBtn:hover {{
            color: {t['colorError']};
            border-color: {t['colorError']};
        }}

        QListWidget {{
            background-color: {t['colorBgContainer']};
            border: 1px solid {t['colorBorderSecondary']};
            border-radius: {t['radiusLG']}px;
            padding: {t['spaceXS']}px;
            font-size: {t['fontSize']}px;
            outline: none;
        }}

        QListWidget::item {{
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: {t['radius']}px;
            padding: {t['spaceSM']}px;
            margin: 2px;
            color: {t['colorText']};
        }}

        QListWidget::item:hover {{
            background-color: {t['colorBgElevated']};
        }}

        QListWidget::item:selected {{
            background-color: rgba(22, 119, 255, 0.22);
            border: 1px solid {t['colorPrimary']};
            color: {t['colorText']};
        }}

        QTextEdit {{
            background-color: {t['colorBgContainer']};
            border: 1px solid {t['colorBorderSecondary']};
            border-radius: {t['radiusLG']}px;
            padding: {t['spaceMD']}px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: {t['fontSizeSM']}px;
            color: {t['colorTextSecondary']};
            selection-background-color: {t['colorPrimary']};
        }}

        QLabel {{
            color: {t['colorText']};
            font-weight: normal;
            font-size: {t['fontSize']}px;
        }}

        QLabel#creditLabel {{
            color: {t['colorTextTertiary']};
            font-size: {t['fontSizeSM'] - 2}px;
            font-style: italic;
        }}

        QGroupBox {{
            border: 1px solid {t['colorBorderSecondary']};
            border-radius: {t['radiusLG']}px;
            margin-top: {t['spaceMD']}px;
            padding: {t['spaceLG']}px {t['spaceMD']}px {t['spaceMD']}px {t['spaceMD']}px;
            font-weight: 600;
            color: {t['colorText']};
            background-color: {t['colorBgContainer']};
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: {t['spaceMD']}px;
            padding: 0 {t['spaceSM']}px;
            background-color: {t['colorPrimary']};
            border-radius: {t['radiusSM']}px;
            color: #ffffff;
        }}

        QFrame#controlPanel {{
            border: 1px solid {t['colorBorderSecondary']};
            border-radius: {t['radiusLG']}px;
            background-color: {t['colorBgContainer']};
        }}

        QLabel#panelTitle {{
            padding: 2px {t['spaceSM']}px;
            background-color: {t['colorPrimary']};
            border-radius: {t['radiusSM']}px;
            color: #ffffff;
            font-weight: 600;
        }}

        QFrame#leftPanel {{
            background-color: {t['colorBgContainer']};
            border: 1px solid {t['colorBorderSecondary']};
            border-radius: {t['radiusLG']}px;
            margin: {t['spaceXS']}px;
        }}

        QFrame#rightPanel {{
            background-color: {t['colorBgContainer']};
            border: 1px solid {t['colorBorderSecondary']};
            border-radius: {t['radiusLG']}px;
            margin: {t['spaceXS']}px;
        }}

        QSplitter::handle {{
            background-color: {t['colorBorderSecondary']};
            width: {t['spaceXS']}px;
            border-radius: 2px;
        }}

        QSplitter::handle:hover {{
            background-color: {t['colorPrimary']};
        }}

        QTabWidget::pane {{
            background-color: transparent;
            border: none;
            border-top: 1px solid {t['colorBorderSecondary']};
        }}

        QTabBar::tab {{
            background-color: transparent;
            color: {t['colorTextSecondary']};
            border: none;
            border-bottom: 2px solid transparent;
            padding: {t['spaceSM']}px {t['spaceLG']}px;
            margin-right: {t['spaceXS']}px;
            font-size: {t['fontSize']}px;
        }}

        QTabBar::tab:selected {{
            color: {t['colorPrimary']};
            border-bottom: 2px solid {t['colorPrimary']};
            font-weight: 600;
        }}

        QTabBar::tab:hover:!selected {{
            color: {t['colorText']};
        }}

        QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {{
            background-color: {t['colorBgBase']};
            border: 1px solid {t['colorBorder']};
            border-radius: {t['radius']}px;
            padding: 0 {t['spaceSM']}px;
            color: {t['colorText']};
            font-size: {t['fontSize']}px;
            min-height: {t['controlHeight'] - 2}px;
            max-height: {t['controlHeight'] - 2}px;
            min-width: 48px;
        }}

        QLineEdit:hover, QComboBox:hover, QDoubleSpinBox:hover, QSpinBox:hover {{
            border-color: {t['colorPrimaryHover']};
        }}

        QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
            border-color: {t['colorPrimary']};
        }}

        QLineEdit:disabled, QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled {{
            color: {t['colorTextDisabled']};
            background-color: transparent;
            border-color: {t['colorBorderSecondary']};
        }}

        QComboBox QAbstractItemView {{
            background-color: {t['colorBgElevated']};
            color: {t['colorText']};
            selection-background-color: {t['colorPrimary']};
            border: 1px solid {t['colorBorder']};
            outline: none;
        }}

        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
        QSpinBox::up-button, QSpinBox::down-button {{
            width: 0px;
            border: none;
        }}

        QScrollBar:vertical {{
            background: transparent;
            width: {t['spaceSM']}px;
            margin: 0;
        }}

        QScrollBar::handle:vertical {{
            background: {t['colorBorder']};
            border-radius: {t['radiusSM']}px;
            min-height: 24px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: #595959;
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        QScrollBar:horizontal {{
            background: transparent;
            height: {t['spaceSM']}px;
            margin: 0;
        }}

        QScrollBar::handle:horizontal {{
            background: {t['colorBorder']};
            border-radius: {t['radiusSM']}px;
            min-width: 24px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background: #595959;
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        """
