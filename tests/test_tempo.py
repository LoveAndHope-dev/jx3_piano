import unittest

from piano_roll import (
    bpm_scale_factor,
    grid_seconds_for_bpm,
    scaled_note_times,
    tempo_us_from_bpm,
)


class BpmFactorTest(unittest.TestCase):
    def test_slow_down(self):
        self.assertEqual(bpm_scale_factor(120.0, 60.0), 2.0)

    def test_speed_up(self):
        self.assertEqual(bpm_scale_factor(60.0, 120.0), 0.5)

    def test_same_bpm_is_one(self):
        self.assertEqual(bpm_scale_factor(120.0, 120.0), 1.0)

    def test_invalid_bpm_raises(self):
        with self.assertRaises(ValueError):
            bpm_scale_factor(120.0, 0.0)
        with self.assertRaises(ValueError):
            bpm_scale_factor(-1.0, 120.0)


class TempoUsTest(unittest.TestCase):
    def test_120_bpm(self):
        self.assertEqual(tempo_us_from_bpm(120.0), 500000)

    def test_90_bpm(self):
        self.assertEqual(tempo_us_from_bpm(90.0), 666667)

    def test_invalid_bpm_raises(self):
        with self.assertRaises(ValueError):
            tempo_us_from_bpm(0.0)


class ScaledNoteTimesTest(unittest.TestCase):
    def test_slow_down_scales_start_and_duration(self):
        notes = [{"start": 1.0, "duration": 0.5, "pitch": 60}]
        result = scaled_note_times(notes, 2.0)
        self.assertEqual(result[0]["start"], 2.0)
        self.assertEqual(result[0]["duration"], 1.0)
        self.assertEqual(result[0]["pitch"], 60)

    def test_speed_up(self):
        notes = [{"start": 2.0, "duration": 1.0}]
        self.assertEqual(scaled_note_times(notes, 0.5)[0]["start"], 1.0)

    def test_round_trip_within_tolerance(self):
        notes = [{"start": 1.234, "duration": 0.567}]
        scaled = scaled_note_times(notes, 0.75)
        restored = scaled_note_times(scaled, 1.0 / 0.75)
        self.assertAlmostEqual(restored[0]["start"], 1.234, delta=1e-6)
        self.assertAlmostEqual(restored[0]["duration"], 0.567, delta=1e-6)

    def test_does_not_mutate_input(self):
        notes = [{"start": 1.0, "duration": 0.5}]
        scaled_note_times(notes, 2.0)
        self.assertEqual(notes, [{"start": 1.0, "duration": 0.5}])


class GridSecondsTest(unittest.TestCase):
    def test_four_four_120(self):
        measure, beat = grid_seconds_for_bpm(120.0, 4, 4)
        self.assertAlmostEqual(beat, 0.5)
        self.assertAlmostEqual(measure, 2.0)

    def test_four_four_60(self):
        measure, beat = grid_seconds_for_bpm(60.0, 4, 4)
        self.assertAlmostEqual(beat, 1.0)
        self.assertAlmostEqual(measure, 4.0)

    def test_three_four_90(self):
        measure, beat = grid_seconds_for_bpm(90.0, 3, 4)
        self.assertAlmostEqual(beat, 2.0 / 3.0)
        self.assertAlmostEqual(measure, 2.0)

    def test_invalid_bpm_raises(self):
        with self.assertRaises(ValueError):
            grid_seconds_for_bpm(0.0, 4, 4)


if __name__ == "__main__":
    unittest.main()
