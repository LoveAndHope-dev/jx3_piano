import importlib
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

MAX_MODULE_LINES = 800

PACKAGE_DIRS = ("app", "piano_roll", "music")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PublicImportTest(unittest.TestCase):
    def test_entry_modules_keep_public_names(self):
        gui = importlib.import_module("gui")
        piano_roll = importlib.import_module("piano_roll")
        build_music = importlib.import_module("build_music")

        for name in (
            "MidiConverterGUI",
            "QPushButton",
            "QMessageBox",
            "get_midi_dir_path",
            "get_play_code_dir_path",
            "main",
            "is_admin",
            "run_as_admin",
            "PlayThread",
            "BatchConversionWorker",
        ):
            self.assertTrue(hasattr(gui, name), name)

        from app.main_window import MidiConverterGUI

        self.assertIs(gui.MidiConverterGUI, MidiConverterGUI)

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
            "get_chromatic_key_ladder",
            "arpeggiate_notes",
        ):
            self.assertTrue(hasattr(piano_roll, name), name)
        self.assertTrue(hasattr(build_music, "MidiToKeysConverter"))

        from music import MidiToKeysConverter as PackageConverter

        self.assertIs(PackageConverter, build_music.MidiToKeysConverter)

    def test_midi_converter_is_still_usable(self):
        from build_music import MidiToKeysConverter

        converter = MidiToKeysConverter()
        sequence, _ = converter.midi_note_to_key_sequence(60)
        self.assertEqual(sequence, ["Q"])

    def test_fresh_interpreter_can_import_entry_modules(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import gui, piano_roll, build_music; print('ok')",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", result.stdout)


class PathProviderTest(unittest.TestCase):
    def test_base_directory_is_project_root(self):
        import music.paths as paths

        self.assertEqual(os.path.abspath(paths.get_base_directory()), ROOT)

    def test_patching_music_paths_redirects_all_callers(self):
        import music.paths as paths
        from app import common
        from app.workers import batch_import

        with patch.object(paths, "get_midi_dir_path", return_value="X:/tmp/midi"):
            self.assertEqual(common.get_midi_dir_path(), "X:/tmp/midi")
            self.assertEqual(batch_import.paths.get_midi_dir_path(), "X:/tmp/midi")


class ModuleSizeTest(unittest.TestCase):
    def test_package_modules_stay_reviewable(self):
        oversized = []
        for package in PACKAGE_DIRS:
            for dirpath, _dirs, files in os.walk(os.path.join(ROOT, package)):
                if "__pycache__" in dirpath:
                    continue
                for filename in files:
                    if not filename.endswith(".py"):
                        continue
                    path = os.path.join(dirpath, filename)
                    with open(path, encoding="utf-8") as handle:
                        lines = sum(1 for _ in handle)
                    if lines > MAX_MODULE_LINES:
                        oversized.append((os.path.relpath(path, ROOT), lines))
        self.assertEqual(oversized, [])


if __name__ == "__main__":
    unittest.main()
