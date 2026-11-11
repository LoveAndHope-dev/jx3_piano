import unittest

from piano_roll import octave_shift_pitches, pasted_starts


class PastedStartsTest(unittest.TestCase):
    def test_preserves_relative_spacing(self):
        clipboard = [{"start": 1.0}, {"start": 3.0}]
        self.assertEqual(pasted_starts(clipboard, 10.0), [10.0, 12.0])

    def test_single_note_lands_on_anchor(self):
        self.assertEqual(pasted_starts([{"start": 4.5}], 2.0), [2.0])

    def test_zero_based_clipboard(self):
        self.assertEqual(pasted_starts([{"start": 0.0}, {"start": 0.5}], 5.0), [5.0, 5.5])

    def test_does_not_mutate_input(self):
        clipboard = [{"start": 1.0, "pitch": 60}, {"start": 3.0, "pitch": 64}]
        pasted_starts(clipboard, 10.0)
        self.assertEqual(clipboard, [{"start": 1.0, "pitch": 60}, {"start": 3.0, "pitch": 64}])

    def test_empty_clipboard(self):
        self.assertEqual(pasted_starts([], 10.0), [])


class OctaveShiftTest(unittest.TestCase):
    def test_shift_up_all_notes(self):
        notes = [{"id": 1, "pitch": 60}, {"id": 2, "pitch": 64}]
        self.assertEqual(octave_shift_pitches(notes, {1, 2}, 12), {1: 72, 2: 76})

    def test_shift_down_all_notes(self):
        notes = [{"id": 1, "pitch": 60}]
        self.assertEqual(octave_shift_pitches(notes, {1}, -12), {1: 48})

    def test_out_of_range_note_keeps_pitch(self):
        notes = [{"id": 1, "pitch": 100}, {"id": 2, "pitch": 60}]
        self.assertEqual(octave_shift_pitches(notes, {1, 2}, 12), {1: 100, 2: 72})

    def test_all_out_of_range_returns_original_pitches(self):
        notes = [{"id": 1, "pitch": 21}]
        self.assertEqual(octave_shift_pitches(notes, {1}, -12), {1: 21})

    def test_unselected_notes_are_ignored(self):
        notes = [{"id": 1, "pitch": 60}, {"id": 2, "pitch": 64}]
        self.assertEqual(octave_shift_pitches(notes, {2}, 12), {2: 76})


if __name__ == "__main__":
    unittest.main()
