import unittest

from piano_roll import pasted_starts


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


if __name__ == "__main__":
    unittest.main()
