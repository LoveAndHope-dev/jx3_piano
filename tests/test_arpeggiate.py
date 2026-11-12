import os
import unittest

import arpeggiate
from arpeggiate_runner import arpeggiate_notes

STEP = 1.0 / 32.0


def _notes():
    return [
        {"id": 0, "pitch": 60, "start": 1.0, "duration": 0.5},
        {"id": 1, "pitch": 64, "start": 1.0, "duration": 0.5},
        {"id": 2, "pitch": 67, "start": 1.0, "duration": 0.5},
        {"id": 3, "pitch": 72, "start": 3.0, "duration": 0.5},
    ]


class ArpeggiateRunnerTest(unittest.TestCase):
    def test_expands_chord_by_pitch(self):
        result = arpeggiate_notes(_notes(), {0, 1, 2}, 1.0)
        by_id = {n["id"]: n for n in result}
        self.assertAlmostEqual(by_id[0]["start"], 1.0, delta=1e-4)
        self.assertAlmostEqual(by_id[1]["start"], 1.0 + STEP, delta=1e-4)
        self.assertAlmostEqual(by_id[2]["start"], 1.0 + 2 * STEP, delta=1e-4)

    def test_durations_are_preserved(self):
        result = arpeggiate_notes(_notes(), {0, 1, 2}, 1.0)
        for note in result[:3]:
            self.assertAlmostEqual(note["duration"], 0.5, delta=1e-4)

    def test_ends_move_with_starts(self):
        notes = [
            {"id": 0, "pitch": 60, "start": 1.0, "duration": 2.0},
            {"id": 1, "pitch": 64, "start": 1.0, "duration": 2.0},
        ]
        result = arpeggiate_notes(notes, {0, 1}, 1.0)
        self.assertAlmostEqual(result[0]["start"] + result[0]["duration"], 3.0, delta=1e-4)
        self.assertAlmostEqual(
            result[1]["start"] + result[1]["duration"], 3.0 + STEP, delta=1e-4
        )

    def test_single_note_unchanged(self):
        result = arpeggiate_notes(_notes(), {3}, 1.0)
        by_id = {n["id"]: n for n in result}
        self.assertAlmostEqual(by_id[3]["start"], 3.0, delta=1e-4)
        self.assertAlmostEqual(by_id[3]["duration"], 0.5, delta=1e-4)

    def test_off_grid_single_note_is_not_nudged(self):
        notes = [{"id": 0, "pitch": 60, "start": 1.0001, "duration": 0.5}]
        result = arpeggiate_notes(notes, {0}, 1.0)
        self.assertEqual(result[0]["start"], 1.0001)
        self.assertEqual(result[0]["duration"], 0.5)

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
        self.assertAlmostEqual(by_id[0]["start"], 1.0, delta=1e-4)
        self.assertAlmostEqual(by_id[2]["start"], 5.0, delta=1e-4)

    def test_duplicate_notes_are_deduped(self):
        notes = [
            {"id": 0, "pitch": 60, "start": 1.0, "duration": 0.5},
            {"id": 1, "pitch": 60, "start": 1.0, "duration": 0.25},
            {"id": 2, "pitch": 64, "start": 1.0, "duration": 0.5},
        ]
        result = arpeggiate_notes(notes, {0, 1, 2}, 1.0)
        ids = [n["id"] for n in result]
        self.assertNotIn(1, ids)
        self.assertIn(0, ids)
        self.assertIn(2, ids)
        survivor = next(n for n in result if n["id"] == 0)
        self.assertAlmostEqual(survivor["duration"], 0.5, delta=1e-4)

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


class ArpeggiateScriptTest(unittest.TestCase):
    def test_script_structure_is_preserved(self):
        for name in ("extract_notes", "dedupe", "arpeggiate", "rebuild", "main"):
            self.assertTrue(callable(getattr(arpeggiate, name)), name)
        self.assertAlmostEqual(arpeggiate.WINDOW_BEATS, 1 / 32)
        self.assertAlmostEqual(arpeggiate.STEP_BEATS, 1 / 32)
        self.assertTrue(arpeggiate.CROSS_TRACK)
        self.assertTrue(arpeggiate.DEDUPE)

    def test_old_helper_implementation_is_gone(self):
        self.assertFalse(hasattr(arpeggiate, "arpeggiate_notes"))

    def test_script_keeps_shebang(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "arpeggiate.py")
        with open(path, encoding="utf-8") as handle:
            first_line = handle.readline()
        self.assertTrue(first_line.startswith("#!"))


if __name__ == "__main__":
    unittest.main()
