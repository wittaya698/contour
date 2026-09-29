"""A signal as something a wait can be interrupted by (issue 27).

`tests/test_console.py` sends real signals to real consoles; this is the step
under both of them, on its own: a signal becomes an exception that says which
signal it was, and a caller asks one question whichever of the two it caught.
"""
import os
import signal
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import signals  # noqa: E402


class SignalsTest(unittest.TestCase):
    def setUp(self):
        before = {n: signal.getsignal(n) for n in signals.STOPPING}
        self.addCleanup(lambda: [signal.signal(n, h) for n, h in before.items()])

    def test_a_signal_that_arrives_comes_out_of_the_wait_named(self):
        signals.raising(signal.SIGTERM)
        with self.assertRaises(signals.Arrived) as got:
            os.kill(os.getpid(), signal.SIGTERM)
        self.assertEqual(signals.number(got.exception), signal.SIGTERM)
        self.assertEqual(str(got.exception), "SIGTERM")

    def test_a_keyboard_interrupt_is_the_one_signal_it_can_be(self):
        self.assertEqual(signals.number(KeyboardInterrupt()), signal.SIGINT)

    def test_the_three_ways_a_console_is_told_to_stop(self):
        self.assertEqual(set(signals.STOPPING),
                         {signal.SIGINT, signal.SIGTERM, signal.SIGHUP})

    def test_a_number_no_signal_has_is_still_named_for_a_reader(self):
        self.assertEqual(signals.name(signal.SIGHUP), "SIGHUP")
        self.assertEqual(signals.name(999), "signal 999")


if __name__ == "__main__":
    unittest.main()
