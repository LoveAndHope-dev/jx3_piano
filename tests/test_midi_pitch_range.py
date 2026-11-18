import os
import tempfile
import unittest

import mido

from build_music import MidiToKeysConverter


def _mixed_file(path):
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    for pitch in list(range(24, 72)) + [120]:
        track.append(mido.Message("note_on", note=pitch, velocity=100, time=0))
        track.append(mido.Message("note_off", note=pitch, velocity=0, time=120))
    mid.save(path)


class MidiPitchRangeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.converter = MidiToKeysConverter(log_callback=lambda message: None)

    def test_auto_transpose_stays_inside_midi_range(self):
        src = os.path.join(self.tmp.name, "mixed.mid")
        _mixed_file(src)
        track_filter, transpose = self.converter.auto_select_tracks_and_transpose(src)
        for pitch in list(range(24, 72)) + [120]:
            self.assertGreaterEqual(pitch + transpose, 0)
            self.assertLessEqual(pitch + transpose, 127)
        self.assertTrue(track_filter)

    def test_import_and_write_back_do_not_raise(self):
        src = os.path.join(self.tmp.name, "mixed.mid")
        _mixed_file(src)
        track_filter, transpose = self.converter.auto_select_tracks_and_transpose(src)
        notes = self.converter.extract_notes(
            src, track_filter=track_filter, transpose=transpose
        )
        self.assertTrue(all(0 <= n["pitch"] <= 127 for n in notes))
        out = os.path.join(self.tmp.name, "out.mid")
        self.converter.write_notes_to_midi(
            src, notes, track_filter, out, tempo_bpm=120.0
        )
        self.assertTrue(os.path.exists(out))

    def test_write_skips_out_of_range_notes(self):
        src = os.path.join(self.tmp.name, "seed.mid")
        mid = mido.MidiFile(ticks_per_beat=480)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.Message("note_on", note=60, velocity=100, time=0))
        track.append(mido.Message("note_off", note=60, velocity=0, time=240))
        mid.save(src)

        notes = [
            {"pitch": 60, "start": 0.0, "duration": 0.5, "track": 0, "channel": 0},
            {"pitch": 200, "start": 0.0, "duration": 0.5, "track": 0, "channel": 0},
            {"pitch": -5, "start": 0.0, "duration": 0.5, "track": 0, "channel": 0},
        ]
        out = os.path.join(self.tmp.name, "out.mid")
        self.converter.write_notes_to_midi(src, notes, [0], out, tempo_bpm=120.0)

        written = self.converter.extract_notes(out, track_filter=[0])
        self.assertEqual([n["pitch"] for n in written], [60])

    def test_transposed_entry_is_clamped(self):
        src = os.path.join(self.tmp.name, "seed.mid")
        mid = mido.MidiFile(ticks_per_beat=480)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.Message("note_on", note=120, velocity=100, time=0))
        track.append(mido.Message("note_off", note=120, velocity=0, time=240))
        mid.save(src)

        notes = self.converter.extract_notes(src, track_filter=[0], transpose=24)
        self.assertEqual(notes[0]["pitch"], 127)


if __name__ == "__main__":
    unittest.main()
