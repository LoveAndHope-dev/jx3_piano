import importlib
import os
import unittest

MAX_MODULE_LINES = 800

PACKAGE_DIRS = ("app", "piano_roll", "music")


class PublicImportTest(unittest.TestCase):
    def test_entry_modules_keep_public_names(self):
        gui = importlib.import_module("gui")
        piano_roll = importlib.import_module("piano_roll")
        build_music = importlib.import_module("build_music")

        for name in ("MidiConverterGUI", "QPushButton", "QMessageBox", "get_midi_dir_path"):
            self.assertTrue(hasattr(gui, name), name)
        for name in (
            "PianoRollWidget",
            "first_playable_start",
            "playback_notes_from_position",
            "octave_shift_pitches",
            "pasted_starts",
            "bpm_scale_factor",
            "grid_seconds_for_bpm",
            "scaled_note_times",
            "tempo_us_from_bpm",
            "clamp_pixels_per_second",
            "anchored_scroll_value",
            "MAX_PIXELS_PER_SECOND",
            "MIN_PIXELS_PER_SECOND",
        ):
            self.assertTrue(hasattr(piano_roll, name), name)
        self.assertTrue(hasattr(build_music, "MidiToKeysConverter"))

    def test_midi_converter_is_still_usable(self):
        from build_music import MidiToKeysConverter

        converter = MidiToKeysConverter()
        sequence, _ = converter.midi_note_to_key_sequence(60)
        self.assertEqual(sequence, ["Q"])


class ModuleSizeTest(unittest.TestCase):
    def test_package_modules_stay_reviewable(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        oversized = []
        for package in PACKAGE_DIRS:
            for dirpath, _dirs, files in os.walk(os.path.join(root, package)):
                if "__pycache__" in dirpath:
                    continue
                for filename in files:
                    if not filename.endswith(".py"):
                        continue
                    path = os.path.join(dirpath, filename)
                    with open(path, encoding="utf-8") as handle:
                        lines = sum(1 for _ in handle)
                    if lines > MAX_MODULE_LINES:
                        oversized.append((os.path.relpath(path, root), lines))
        self.assertEqual(oversized, [])


if __name__ == "__main__":
    unittest.main()
