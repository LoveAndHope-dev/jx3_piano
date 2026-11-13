import unittest
from unittest.mock import patch

from player import JX3Player


class FakeClock:
    """虚拟时钟：sleep 推进时间，可模拟超时与休眠期间触发的回调。"""

    def __init__(self, start: float = 1000.0, sleep_cost: float = 0.0, on_sleep=None):
        self.now = start
        self.sleep_cost = sleep_cost
        self.on_sleep = on_sleep
        self.sleeps = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        duration = max(0.0, float(seconds))
        self.sleeps.append(duration)
        self.now += duration + self.sleep_cost
        if self.on_sleep is not None:
            self.on_sleep()


class FakeDD:
    """记录按键时刻，并可模拟按键耗时。"""

    def __init__(self, clock: FakeClock, press_cost: float = 0.0, on_press=None):
        self.clock = clock
        self.press_cost = press_cost
        self.presses = []
        self.on_press = on_press

    def key_press(self, key: str) -> None:
        self.presses.append((key, self.clock.now))
        if self.on_press is not None:
            self.on_press(key)
        self.clock.now += self.press_cost


def _make_player(clock, dd, progress=None, log=None):
    with patch.object(
        JX3Player, "_init_dd_driver", lambda self: setattr(self, "dd", dd)
    ), patch.object(JX3Player, "_init_keyboard", lambda self: None):
        return JX3Player(
            log_callback=log or (lambda message: None),
            progress_callback=progress,
            clock=clock.time,
            sleep=clock.sleep,
        )


class PlaybackTimingTest(unittest.TestCase):
    def test_key_press_cost_does_not_accumulate(self):
        clock = FakeClock()
        dd = FakeDD(clock, press_cost=0.02)
        player = _make_player(clock, dd)

        data = [0.1, "A", 0.1, "B", 0.1, "C"]
        self.assertTrue(player._execute_playback_data(data))

        times = [moment - 1000.0 for _, moment in dd.presses]
        for order, moment in enumerate(times, start=1):
            self.assertAlmostEqual(moment, order * 0.1, places=6)

    def test_many_groups_keep_absolute_schedule(self):
        clock = FakeClock()
        dd = FakeDD(clock, press_cost=0.02)
        player = _make_player(clock, dd)

        data = []
        for _ in range(100):
            data.extend([0.1, "K"])

        self.assertTrue(player._execute_playback_data(data))
        for order, (_, moment) in enumerate(dd.presses, start=1):
            self.assertAlmostEqual(moment - 1000.0, order * 0.1, places=6)

    def test_sleep_overshoot_is_absorbed(self):
        clock = FakeClock(sleep_cost=0.003)
        dd = FakeDD(clock, press_cost=0.0)
        player = _make_player(clock, dd)

        data = [0.1, "A", 0.1, "B", 0.1, "C"]
        self.assertTrue(player._execute_playback_data(data))

        for order, (_, moment) in enumerate(dd.presses, start=1):
            self.assertLessEqual(moment - 1000.0, order * 0.1 + 0.004)

    def test_wait_steps_stay_small_for_stop_responsiveness(self):
        clock = FakeClock()
        player = _make_player(clock, FakeDD(clock))
        self.assertTrue(player._execute_playback_data([0.5, "A"]))
        self.assertTrue(clock.sleeps)
        for step in clock.sleeps:
            self.assertLessEqual(step, 0.0101)

    def test_progress_uses_wall_clock(self):
        clock = FakeClock()
        dd = FakeDD(clock, press_cost=0.01)
        samples = []
        player = _make_player(clock, dd, progress=samples.append)

        self.assertTrue(player._execute_playback_data([0.2, "A", 0.2, "B"]))

        self.assertAlmostEqual(samples[0], 0.0, places=6)
        self.assertGreaterEqual(samples[-1], 0.4)
        self.assertEqual(samples, sorted(samples))
        gaps = [b - a for a, b in zip(samples, samples[1:])]
        self.assertTrue(all(gap <= 0.06 for gap in gaps), gaps)

    def test_stop_signal_interrupts_playback(self):
        clock = FakeClock()
        holder = {}

        def stop_after_first(key):
            holder["player"].should_stop = True

        dd = FakeDD(clock, press_cost=0.0, on_press=stop_after_first)
        player = _make_player(clock, dd)
        holder["player"] = player

        self.assertFalse(player._execute_playback_data([0.1, "A", 0.1, "B"]))
        self.assertEqual([key for key, _ in dd.presses], ["A"])

    def test_stop_during_wait_is_detected(self):
        holder = {}

        def stop_on_sleep():
            holder["player"].should_stop = True

        clock = FakeClock(on_sleep=stop_on_sleep)
        player = _make_player(clock, FakeDD(clock))
        holder["player"] = player

        self.assertFalse(player._execute_playback_data([1.0, "A"]))
        self.assertEqual(clock.sleeps[0], 0.01)

    def test_late_group_is_reported(self):
        logs = []
        clock = FakeClock()
        dd = FakeDD(clock, press_cost=0.15)
        player = _make_player(clock, dd, log=logs.append)

        self.assertTrue(player._execute_playback_data([0.1, "A", 0.1, "B"]))
        self.assertTrue(any("最大延迟" in line for line in logs), logs)

    def test_empty_data_returns_false(self):
        clock = FakeClock()
        player = _make_player(clock, FakeDD(clock))
        self.assertFalse(player._execute_playback_data([]))


if __name__ == "__main__":
    unittest.main()
