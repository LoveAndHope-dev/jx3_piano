import json
import os
import tempfile
import unittest

from build_music import MidiToKeysConverter
from play_assets import (
    build_play_code_data,
    edited_midi_path,
    play_code_path,
    read_play_code,
    split_playback_at,
    write_play_code,
)


class SplitPlaybackTest(unittest.TestCase):
    def test_zero_start_returns_copy(self):
        data = ["Q", 0.5, "W"]
        result = split_playback_at(data, 0.0)
        self.assertEqual(result, data)
        self.assertIsNot(result, data)

    def test_skips_keys_before_start(self):
        data = ["Q", 0.5, "W", 0.5, "E"]
        self.assertEqual(split_playback_at(data, 0.6), [0.4, "E"])
        self.assertEqual(split_playback_at(data, 0.5), ["W", 0.5, "E"])

    def test_keeps_remaining_delay_inside_a_gap(self):
        data = [1.0, "Q", 1.0, "W", 2.0, "E"]
        self.assertEqual(split_playback_at(data, 2.6), [1.4, "E"])
        self.assertEqual(split_playback_at(data, 1.5), [0.5, "W", 2.0, "E"])

    def test_key_exactly_at_start_is_kept(self):
        data = [1.0, "Q", 1.0, "W", 2.0, "E"]
        self.assertEqual(split_playback_at(data, 2.0), ["W", 2.0, "E"])
        self.assertEqual(split_playback_at(data, 1.0), ["Q", 1.0, "W", 2.0, "E"])
        self.assertEqual(split_playback_at(data, 4.0), ["E"])

    def test_float_accumulation_keeps_key_at_start(self):
        data = ["K", 0.1] * 10 + ["K"]  # 按键位于 0.0 ~ 1.0 秒
        self.assertEqual(
            split_playback_at(data, 0.8), ["K", 0.1, "K", 0.1, "K"]
        )
        self.assertEqual(split_playback_at(data, 1.0), ["K"])

    def test_trailing_delay_only_returns_empty(self):
        self.assertEqual(split_playback_at(["Q", 2.0], 1.0), [])

    def test_input_is_not_mutated(self):
        data = ["Q", 0.5, "W"]
        snapshot = list(data)
        split_playback_at(data, 0.2)
        self.assertEqual(data, snapshot)

    def test_start_after_end_returns_empty(self):
        self.assertEqual(split_playback_at(["Q", 0.2], 5.0), [])


class PlayCodeDataTest(unittest.TestCase):
    def setUp(self):
        self.converter = MidiToKeysConverter()

    def test_keeps_notes_inside_box(self):
        notes = [{"pitch": 60, "start": 0.0, "duration": 0.2, "track": 0}]
        data = build_play_code_data(
            self.converter, notes, 120.0, "demo", pitch_range=(36, 83), transpose=0
        )
        self.assertTrue(data["playback_data"])
        self.assertEqual(data["filename"], "demo")
        self.assertEqual(data["bpm"], 120.0)

    def test_first_note_keeps_absolute_time_axis(self):
        notes = [{"pitch": 60, "start": 5.0, "duration": 0.5, "track": 0}]
        data = build_play_code_data(
            self.converter, notes, 120.0, "demo", pitch_range=(36, 83), transpose=0
        )
        self.assertEqual(data["playback_data"][0], 5.0)
        self.assertEqual(data["timeline_offset"], 0.0)

    def test_notes_outside_box_are_filtered(self):
        notes = [{"pitch": 90, "start": 0.0, "duration": 0.2, "track": 0}]
        data = build_play_code_data(
            self.converter, notes, 120.0, "demo", pitch_range=(36, 83), transpose=0
        )
        self.assertEqual(data["playback_data"], [])

    def test_unmapped_notes_are_skipped(self):
        notes = [{"pitch": 20, "start": 0.0, "duration": 0.2, "track": 0}]
        data = build_play_code_data(self.converter, notes, 120.0, "demo")
        self.assertEqual(data["playback_data"], [])


class PlayCodeFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_roundtrip(self):
        path = play_code_path(self.tmp.name, "song")
        write_play_code(path, {"playback_data": ["Q"], "filename": "song"})
        self.assertEqual(read_play_code(path)["filename"], "song")

    def test_corrupt_returns_none(self):
        path = play_code_path(self.tmp.name, "bad")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("not json")
        self.assertIsNone(read_play_code(path))

    def test_paths_are_separate(self):
        edited = edited_midi_path(self.tmp.name, "song")
        code = play_code_path(self.tmp.name, "song")
        self.assertNotEqual(edited, code)
        self.assertIn("edited", edited)
        self.assertTrue(code.endswith(".json"))


if __name__ == "__main__":
    unittest.main()
