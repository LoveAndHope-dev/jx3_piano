import json
import os
import tempfile
import unittest

import mido

from playlist_store import (
    HIDDEN_FILENAME,
    create_blank_midi,
    filter_entries,
    list_entries,
    load_hidden,
    save_hidden,
    sort_entries,
    unique_midi_name,
)


class HiddenStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = self.tmp.name

    def test_missing_file_is_empty(self):
        self.assertEqual(load_hidden(self.dir), set())

    def test_save_and_load(self):
        save_hidden(self.dir, {"a.mid", "b.mid"})
        self.assertEqual(load_hidden(self.dir), {"a.mid", "b.mid"})

    def test_corrupt_file_returns_empty_and_keeps_content(self):
        path = os.path.join(self.dir, HIDDEN_FILENAME)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("not-json")
        self.assertEqual(load_hidden(self.dir), set())
        with open(path, "r", encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "not-json")

    def test_non_list_json_returns_empty(self):
        path = os.path.join(self.dir, HIDDEN_FILENAME)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"a": 1}')
        self.assertEqual(load_hidden(self.dir), set())

    def test_save_creates_directory(self):
        target = os.path.join(self.dir, "sub")
        save_hidden(target, {"x.mid"})
        self.assertEqual(load_hidden(target), {"x.mid"})


class EntriesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = self.tmp.name
        for name, stamp in (("Qing.mid", 100.0), ("qing2.MID", 300.0), ("note.txt", 200.0)):
            path = os.path.join(self.dir, name)
            with open(path, "wb") as fh:
                fh.write(b"x")
            os.utime(path, (stamp, stamp))

    def test_lists_only_midi(self):
        names = [e[0] for e in list_entries(self.dir)]
        self.assertIn("Qing.mid", names)
        self.assertIn("qing2.MID", names)
        self.assertNotIn("note.txt", names)

    def test_filter_is_case_insensitive(self):
        entries = list_entries(self.dir)
        self.assertEqual(len(filter_entries(entries, "QING")), 2)
        self.assertEqual(len(filter_entries(entries, "2")), 1)
        self.assertEqual(len(filter_entries(entries, "")), 2)
        self.assertEqual(len(filter_entries(entries, "   ")), 2)

    def test_sort_by_name(self):
        names = [e[0] for e in sort_entries(list_entries(self.dir), "name")]
        self.assertEqual(names, ["Qing.mid", "qing2.MID"])

    def test_sort_by_mtime_desc(self):
        names = [e[0] for e in sort_entries(list_entries(self.dir), "mtime")]
        self.assertEqual(names, ["qing2.MID", "Qing.mid"])

    def test_sort_ties_are_stable(self):
        path = os.path.join(self.dir, "same.mid")
        with open(path, "wb") as fh:
            fh.write(b"x")
        os.utime(path, (300.0, 300.0))
        names = [e[0] for e in sort_entries(list_entries(self.dir), "mtime")]
        self.assertEqual(names[:2], ["qing2.MID", "same.mid"])


class BlankMidiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = self.tmp.name

    def test_unique_name(self):
        self.assertEqual(unique_midi_name(self.dir), "新建曲目.mid")
        with open(os.path.join(self.dir, "新建曲目.mid"), "wb"):
            pass
        self.assertEqual(unique_midi_name(self.dir), "新建曲目_2.mid")

    def test_create_blank_midi_rejects_invalid_bpm(self):
        path = os.path.join(self.dir, "bad.mid")
        with self.assertRaises(ValueError):
            create_blank_midi(path, bpm=0.0)

    def test_create_blank_midi_contents(self):
        path = os.path.join(self.dir, unique_midi_name(self.dir))
        create_blank_midi(path)
        mid = mido.MidiFile(path)
        self.assertGreaterEqual(len(mid.tracks), 1)
        tempos = [m.tempo for t in mid.tracks for m in t if m.type == "set_tempo"]
        self.assertEqual(tempos, [500000])
        signatures = [m for t in mid.tracks for m in t if m.type == "time_signature"]
        self.assertEqual((signatures[0].numerator, signatures[0].denominator), (4, 4))
        notes = [m for t in mid.tracks for m in t if m.type == "note_on"]
        self.assertEqual(notes, [])

    def test_create_two_blanks_do_not_overwrite(self):
        first = os.path.join(self.dir, unique_midi_name(self.dir))
        create_blank_midi(first)
        second = os.path.join(self.dir, unique_midi_name(self.dir))
        create_blank_midi(second)
        self.assertNotEqual(first, second)
        self.assertTrue(os.path.exists(first))
        self.assertTrue(os.path.exists(second))


if __name__ == "__main__":
    unittest.main()
