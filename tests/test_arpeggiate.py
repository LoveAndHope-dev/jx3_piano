import unittest

from arpeggiate import arpeggiate_notes


def _notes():
    return [
        {"id": 0, "pitch": 60, "start": 1.0, "duration": 0.5},
        {"id": 1, "pitch": 64, "start": 1.0, "duration": 0.5},
        {"id": 2, "pitch": 67, "start": 1.0, "duration": 0.5},
        {"id": 3, "pitch": 72, "start": 3.0, "duration": 0.5},
    ]


class ArpeggiateTest(unittest.TestCase):
    def test_expands_chord_by_pitch(self):
        result = arpeggiate_notes(_notes(), {0, 1, 2}, 1.0)
        by_id = {n["id"]: n for n in result}
        step = 1.0 / 32.0
        self.assertAlmostEqual(by_id[0]["start"], 1.0, delta=1e-6)
        self.assertAlmostEqual(by_id[1]["start"], 1.0 + step, delta=1e-6)
        self.assertAlmostEqual(by_id[2]["start"], 1.0 + 2 * step, delta=1e-6)

    def test_durations_are_preserved(self):
        result = arpeggiate_notes(_notes(), {0, 1, 2}, 1.0)
        for note in result[:3]:
            self.assertAlmostEqual(note["duration"], 0.5, delta=1e-6)

    def test_ends_move_with_starts(self):
        notes = [
            {"id": 0, "pitch": 60, "start": 1.0, "duration": 2.0},
            {"id": 1, "pitch": 64, "start": 1.0, "duration": 2.0},
        ]
        result = arpeggiate_notes(notes, {0, 1}, 1.0)
        step = 1.0 / 32.0
        self.assertAlmostEqual(result[0]["start"] + result[0]["duration"], 3.0, delta=1e-6)
        self.assertAlmostEqual(
            result[1]["start"] + result[1]["duration"], 3.0 + step, delta=1e-6
        )

    def test_single_note_unchanged(self):
        result = arpeggiate_notes(_notes(), {3}, 1.0)
        self.assertEqual(result[3]["start"], 3.0)
        self.assertEqual(result[3]["duration"], 0.5)

    def test_unselected_untouched(self):
        result = arpeggiate_notes(_notes(), {0, 1}, 1.0)
        self.assertEqual(result[3]["start"], 3.0)
        self.assertEqual(result[3]["pitch"], 72)

    def test_groups_are_independent(self):
        notes = [
            {"id": 0, "pitch": 60, "start": 1.0, "duration": 0.5},
            {"id": 1, "pitch": 64, "start": 1.0, "duration": 0.5},
            {"id": 2, "pitch": 60, "start": 5.0, "duration": 0.5},
            {"id": 3, "pitch": 64, "start": 5.0, "duration": 0.5},
        ]
        result = arpeggiate_notes(notes, {0, 1, 2, 3}, 1.0)
        by_id = {n["id"]: n for n in result}
        self.assertAlmostEqual(by_id[0]["start"], 1.0, delta=1e-6)
        self.assertAlmostEqual(by_id[2]["start"], 5.0, delta=1e-6)

    def test_short_notes_keep_duration_and_stagger(self):
        notes = [
            {"id": 0, "pitch": 60, "start": 1.0, "duration": 0.03},
            {"id": 1, "pitch": 64, "start": 1.0, "duration": 0.03},
        ]
        result = arpeggiate_notes(notes, {0, 1}, 1.0)
        step = 1.0 / 32.0
        self.assertAlmostEqual(result[0]["start"], 1.0, delta=1e-6)
        self.assertAlmostEqual(result[1]["start"], 1.0 + step, delta=1e-6)
        for note in result:
            self.assertAlmostEqual(note["duration"], 0.03, delta=1e-6)

    def test_input_is_not_mutated(self):
        notes = _notes()
        snapshot = [dict(n) for n in notes]
        arpeggiate_notes(notes, {0, 1, 2}, 1.0)
        self.assertEqual(notes, snapshot)

    def test_invalid_beat_returns_copies(self):
        notes = _notes()
        result = arpeggiate_notes(notes, {0, 1, 2}, 0.0)
        self.assertEqual(result, notes)
        self.assertIsNot(result[0], notes[0])


if __name__ == "__main__":
    unittest.main()
