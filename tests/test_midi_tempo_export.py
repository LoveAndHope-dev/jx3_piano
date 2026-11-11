import os
import tempfile
import unittest

import mido

from build_music import MidiToKeysConverter


def _absolute_ticks(track):
    tick = 0
    result = []
    for msg in track:
        tick += msg.time
        result.append((tick, msg))
    return result


class MidiTempoExportTest(unittest.TestCase):
    def setUp(self):
        self.converter = MidiToKeysConverter()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.src = os.path.join(self.tmp.name, "source.mid")
        self.out = os.path.join(self.tmp.name, "out.mid")

        mid = mido.MidiFile(ticks_per_beat=480)
        conductor = mido.MidiTrack()
        conductor.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))
        conductor.append(mido.MetaMessage("end_of_track", time=0))
        notes_track = mido.MidiTrack()
        notes_track.append(mido.Message("program_change", program=0, channel=0, time=0))
        notes_track.append(mido.Message("note_on", note=60, velocity=100, channel=0, time=960))
        notes_track.append(mido.Message("note_off", note=60, velocity=0, channel=0, time=480))
        notes_track.append(mido.Message("note_on", note=62, velocity=100, channel=0, time=480))
        notes_track.append(mido.Message("note_off", note=62, velocity=0, channel=0, time=480))
        notes_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(conductor)
        mid.tracks.append(notes_track)
        mid.save(self.src)

        # 120 BPM 下的 1.0s / 2.0s 起始，按 90 BPM 的秒数传入
        factor = 120.0 / 90.0
        self.notes = [
            {"pitch": 60, "start": 1.0 * factor, "duration": 0.5 * factor, "track": 1,
             "channel": 0, "velocity": 100},
            {"pitch": 62, "start": 2.0 * factor, "duration": 0.5 * factor, "track": 1,
             "channel": 0, "velocity": 100},
        ]

    def test_writes_new_tempo(self):
        self.converter.write_notes_to_midi(self.src, self.notes, [1], self.out, tempo_bpm=90.0)
        mid = mido.MidiFile(self.out)
        tempos = [msg.tempo for track in mid.tracks for msg in track if msg.type == "set_tempo"]
        self.assertTrue(tempos)
        self.assertTrue(all(abs(t - 666667) <= 1 for t in tempos), tempos)

    def test_note_ticks_are_preserved(self):
        self.converter.write_notes_to_midi(self.src, self.notes, [1], self.out, tempo_bpm=90.0)
        mid = mido.MidiFile(self.out)
        ticks = [
            tick
            for tick, msg in _absolute_ticks(mid.tracks[1])
            if msg.type == "note_on" and msg.velocity > 0
        ]
        self.assertEqual(ticks, [960, 1920])

    def test_unprocessed_track_events_are_preserved(self):
        self.converter.write_notes_to_midi(self.src, self.notes, [1], self.out, tempo_bpm=90.0)
        before = _absolute_ticks(mido.MidiFile(self.src).tracks[0])
        after = _absolute_ticks(mido.MidiFile(self.out).tracks[0])
        self.assertEqual([(t, m.type) for t, m in before], [(t, m.type) for t, m in after])

    def test_without_tempo_bpm_keeps_source_tempo(self):
        self.converter.write_notes_to_midi(self.src, self.notes, [1], self.out)
        mid = mido.MidiFile(self.out)
        tempos = [msg.tempo for track in mid.tracks for msg in track if msg.type == "set_tempo"]
        self.assertEqual(tempos, [500000])


if __name__ == "__main__":
    unittest.main()
