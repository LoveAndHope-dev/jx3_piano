import unittest

from app.ui.theme import REQUIRED_TOKEN_KEYS, TOKENS, build_stylesheet


class ThemeTokenTest(unittest.TestCase):
    def test_required_tokens_exist(self):
        for key in REQUIRED_TOKEN_KEYS:
            self.assertIn(key, TOKENS)
            self.assertIsNotNone(TOKENS[key])

    def test_antd_dark_palette(self):
        self.assertEqual(TOKENS["colorPrimary"], "#1677ff")
        self.assertEqual(TOKENS["colorBgBase"], "#141414")
        self.assertEqual(TOKENS["colorBgContainer"], "#1f1f1f")
        self.assertEqual(TOKENS["controlHeight"], 32)

    def test_stylesheet_uses_tokens(self):
        stylesheet = build_stylesheet()
        self.assertIn("#1677ff", stylesheet)
        self.assertIn(f"{TOKENS['controlHeight'] - 2}px", stylesheet)
        self.assertNotIn("#3498DB", stylesheet)
        self.assertNotIn("#2C3E50", stylesheet)

    def test_primary_token_drives_derived_colors(self):
        stylesheet = build_stylesheet({**TOKENS, "colorPrimary": "#ff0000"})
        self.assertIn("#ff0000", stylesheet)
        self.assertIn("rgba(255, 0, 0, 0.22)", stylesheet)
        self.assertNotIn("rgba(22, 119, 255, 0.22)", stylesheet)

    def test_stylesheet_keeps_core_selectors(self):
        stylesheet = build_stylesheet()
        for selector in (
            "QPushButton#playBtn",
            "QPushButton#stopBtn",
            "QPushButton#importBtn",
            "QListWidget",
            "QTextEdit",
            "QTabBar::tab:selected",
            "QFrame#controlPanel",
            "QLabel#panelTitle",
            "QScrollBar",
            "QMenu::item:selected",
            "QMessageBox",
        ):
            self.assertIn(selector, stylesheet)

    def test_primary_buttons_have_state_selectors(self):
        stylesheet = build_stylesheet()
        for selector in (
            "QPushButton#playBtn:pressed",
            "QPushButton#playBtn:disabled",
            "QPushButton#importBtn:pressed",
            "QPushButton#importBtn:disabled",
            "QPushButton#stopBtn:pressed",
            "QPushButton#stopBtn:disabled",
        ):
            self.assertIn(selector, stylesheet)


if __name__ == "__main__":
    unittest.main()
