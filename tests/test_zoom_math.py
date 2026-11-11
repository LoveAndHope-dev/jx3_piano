import unittest

from piano_roll import (
    MAX_PIXELS_PER_SECOND,
    MIN_PIXELS_PER_SECOND,
    anchored_scroll_value,
    clamp_pixels_per_second,
)


class ZoomMathTest(unittest.TestCase):
    def test_clamps_low_and_high(self):
        self.assertEqual(clamp_pixels_per_second(1.0), MIN_PIXELS_PER_SECOND)
        self.assertEqual(clamp_pixels_per_second(9999.0), MAX_PIXELS_PER_SECOND)

    def test_keeps_value_inside_range(self):
        self.assertEqual(clamp_pixels_per_second(70.0), 70.0)

    def test_anchor_time_survives_zoom_in(self):
        anchor_time, screen_x, pps = 5.0, 120.0, 87.5
        value = anchored_scroll_value(anchor_time, screen_x, pps)
        self.assertAlmostEqual((value + screen_x) / pps, anchor_time)

    def test_anchor_time_survives_zoom_out(self):
        anchor_time, screen_x, pps = 12.0, 40.0, 56.0
        value = anchored_scroll_value(anchor_time, screen_x, pps)
        self.assertAlmostEqual((value + screen_x) / pps, anchor_time)

    def test_never_returns_negative_scroll(self):
        self.assertEqual(anchored_scroll_value(0.5, 300.0, 70.0), 0.0)


if __name__ == "__main__":
    unittest.main()
