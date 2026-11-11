import unittest

from build_music import MidiToKeysConverter


class EdgeNoteMappingTest(unittest.TestCase):
    def setUp(self):
        self.conv = MidiToKeysConverter()

    def test_c6_maps_to_sharp_top_key(self):
        seq, state = self.conv.midi_note_to_key_sequence(84)
        self.assertEqual(seq, ["+", "7"])
        self.assertTrue(state["sharp"])

    def test_c6_then_b5_restores_sharp(self):
        _, state = self.conv.midi_note_to_key_sequence(84)
        seq, state = self.conv.midi_note_to_key_sequence(83, state)
        self.assertEqual(seq, ["-", "7"])
        self.assertFalse(state["sharp"])

    def test_consecutive_c6_does_not_repeat_sharp(self):
        _, state = self.conv.midi_note_to_key_sequence(84)
        seq, _ = self.conv.midi_note_to_key_sequence(84, state)
        self.assertEqual(seq, ["7"])

    def test_csharp6_still_skipped(self):
        seq, _ = self.conv.midi_note_to_key_sequence(85)
        self.assertEqual(seq, [])

    def test_a_sharp1_still_skipped(self):
        seq, _ = self.conv.midi_note_to_key_sequence(34)
        self.assertEqual(seq, [])

    def test_c6_included_in_box_pipeline(self):
        notes = [
            {"pitch": 84, "start": 0.0, "duration": 0.5, "track": 0},
            {"pitch": 85, "start": 1.0, "duration": 0.5, "track": 0},
        ]
        result = self.conv.regenerate_playback_from_notes(
            notes, pitch_range=(36, 83), transpose=0
        )
        self.assertEqual(result["playback_data"], ["+", "7"])


if __name__ == "__main__":
    unittest.main()
