import unittest

from piano_roll import playback_notes_from_position


class PlaybackNotesFromPositionTest(unittest.TestCase):
    def test_excludes_notes_starting_before_playhead(self):
        notes = [{"start": 1.0, "pitch": 60}, {"start": 10.0, "pitch": 62}]
        result = playback_notes_from_position(notes, 5.0)
        self.assertEqual([n["pitch"] for n in result], [62])

    def test_note_exactly_on_playhead_is_kept(self):
        notes = [{"start": 5.0, "pitch": 60}]
        result = playback_notes_from_position(notes, 5.0)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]["start"], 0.0)

    def test_note_ending_after_playhead_is_not_retriggered(self):
        notes = [{"start": 8.0, "duration": 4.0, "pitch": 60}, {"start": 11.0, "pitch": 62}]
        result = playback_notes_from_position(notes, 10.0)
        self.assertEqual([n["pitch"] for n in result], [62])

    def test_starts_are_shifted_to_relative_time(self):
        notes = [{"start": 10.0, "pitch": 60}, {"start": 12.5, "pitch": 62}]
        starts = [n["start"] for n in playback_notes_from_position(notes, 10.0)]
        self.assertEqual(starts, [0.0, 2.5])

    def test_empty_when_no_note_after_playhead(self):
        self.assertEqual(playback_notes_from_position([{"start": 1.0}], 5.0), [])

    def test_does_not_mutate_input(self):
        notes = [{"start": 10.0, "pitch": 60}]
        playback_notes_from_position(notes, 4.0)
        self.assertEqual(notes, [{"start": 10.0, "pitch": 60}])


if __name__ == "__main__":
    unittest.main()
