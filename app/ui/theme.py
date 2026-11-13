"""Ant Design（深色）设计令牌与全局样式。

界面只从这里取颜色、间距、圆角、字号与控件高度，避免样式散落在各处。
"""

from __future__ import annotations

from typing import Dict, Optional

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
    "colorTextLightSolid": "#ffffff",
    "colorSuccess": "#49aa19",
    "colorSuccessHover": "#5cb824",
    "colorSuccessActive": "#3c8618",
    "colorWarning": "#d89614",
    "colorError": "#dc4446",
    "colorErrorHover": "#e05a5c",
    "colorErrorActive": "#b03a3c",
    "colorInfo": "#1677ff",
    "colorScrollbarHover": "#595959",
    # 圆角与尺寸
    "radiusXS": 2,
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


def _rgba(hex_color: str, alpha: float) -> str:
    """把 #rrggbb 转成 rgba()，用于派生选中态底色。"""
    value = hex_color.lstrip("#")
    if len(value) != 6:
        return hex_color
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return f"rgba({red}, {green}, {blue}, {alpha})"


def build_stylesheet(tokens: Optional[Dict[str, object]] = None) -> str:
    """按令牌生成全局 QSS。"""
    t = TOKENS if tokens is None else tokens
    primary_bg = _rgba(str(t["colorPrimary"]), 0.22)
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
            color: {t['colorTextLightSolid']};
            font-weight: 600;
        }}

        QPushButton#importBtn:hover {{
            background-color: {t['colorSuccessHover']};
            border-color: {t['colorSuccessHover']};
            color: {t['colorTextLightSolid']};
        }}

        QPushButton#importBtn:pressed {{
            background-color: {t['colorSuccessActive']};
            border-color: {t['colorSuccessActive']};
            color: {t['colorTextLightSolid']};
        }}

        QPushButton#importBtn:disabled,
        QPushButton#playBtn:disabled,
        QPushButton#stopBtn:disabled {{
            background-color: {t['colorBgContainer']};
            border-color: {t['colorBorderSecondary']};
            color: {t['colorTextDisabled']};
        }}

        QPushButton#playBtn {{
            background-color: {t['colorPrimary']};
            border-color: {t['colorPrimary']};
            color: {t['colorTextLightSolid']};
            min-width: 56px;
            font-size: {t['fontSize']}px;
            font-weight: 600;
        }}

        QPushButton#playBtn:hover {{
            background-color: {t['colorPrimaryHover']};
            border-color: {t['colorPrimaryHover']};
            color: {t['colorTextLightSolid']};
        }}

        QPushButton#playBtn:pressed {{
            background-color: {t['colorPrimaryActive']};
            border-color: {t['colorPrimaryActive']};
            color: {t['colorTextLightSolid']};
        }}

        QPushButton#stopBtn {{
            background-color: {t['colorError']};
            border-color: {t['colorError']};
            color: {t['colorTextLightSolid']};
            font-weight: 600;
        }}

        QPushButton#stopBtn:hover {{
            background-color: {t['colorErrorHover']};
            border-color: {t['colorErrorHover']};
            color: {t['colorTextLightSolid']};
        }}

        QPushButton#stopBtn:pressed {{
            background-color: {t['colorErrorActive']};
            border-color: {t['colorErrorActive']};
            color: {t['colorTextLightSolid']};
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
            background-color: {primary_bg};
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
            font-size: {t['fontSizeSM']}px;
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
            color: {t['colorTextLightSolid']};
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
            color: {t['colorTextLightSolid']};
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
            border-radius: {t['radiusXS']}px;
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

        QMenu {{
            background-color: {t['colorBgElevated']};
            border: 1px solid {t['colorBorder']};
            border-radius: {t['radius']}px;
            padding: {t['spaceXS']}px;
        }}

        QMenu::item {{
            padding: 6px {t['spaceXL']}px;
            border-radius: {t['radiusSM']}px;
            color: {t['colorText']};
        }}

        QMenu::item:selected {{
            background-color: {primary_bg};
            color: {t['colorText']};
        }}

        QMessageBox, QDialog {{
            background-color: {t['colorBgElevated']};
        }}

        QMessageBox QLabel {{
            color: {t['colorText']};
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
            background: {t['colorScrollbarHover']};
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
            background: {t['colorScrollbarHover']};
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        """
