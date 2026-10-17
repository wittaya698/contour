"""The run says whether it is working (issue 130).

The line under the transcript said *running* only on the tab that started the
run, and nothing told a slow run from a stuck one. It is now one of three
states, which the console says with every page of the transcript: so a
reloaded tab, which started nothing, reads them the same as the tab that did.
Never how far along a run is (ADR 0019, decision 4).
"""
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from console import run                 # noqa: E402
from test_console import ConsoleCase    # noqa: E402


class WorkingTest(ConsoleCase):

    def now(self, url, until):
        """What the line under the transcript says, once `until` is true of it."""
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            _, said = self.ask(url, "/events?since=0")
            if until(said["now"]):
                return said["now"]
            time.sleep(0.1)
        self.fail(f"the line never satisfied {until}: {said['now']!r}")

    def test_a_page_that_asks_mid_run_is_told_the_agent_is_working(self):
        """Asked fresh, as a reloaded tab asks: it started nothing."""
        _, url = self.driven({"say": "measuring"}, {"busy": 5})
        self.ask(url, "/run", {"prompt": "go on"})
        now = self.now(url, lambda n: n["state"] != "idle")
        self.assertEqual(now, {"state": "working", "said": "Claude is working"})

    def test_a_gate_waiting_says_it_is_waiting_for_you(self):
        """The agent is not working then, and the person is the hold-up: the
        line says so, in the colour a gate is in, and does not pulse."""
        _, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}})
        self.ask(url, "/run", {"prompt": "check the build"})
        self.gate(url)
        self.assertEqual(self.now(url, lambda n: True),
                         {"state": "waiting", "said": "Waiting for you: answer above"})

    def test_a_run_that_has_ended_is_no_run(self):
        """In the same reply as the end: a transcript that says the run ended
        over a line that says Claude is working would be two answers."""
        _, url = self.driven({"say": "done"})
        self.ask(url, "/run", {"prompt": "go on"})
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            _, said = self.ask(url, "/events?since=0")
            if any(e["kind"] == "ended" for e in said["events"]):
                break
        self.assertEqual(said["now"], {"state": "idle", "said": "no run"})


class QuietTest(unittest.TestCase):

    def test_quiet_is_said_after_fifteen_seconds_and_is_only_a_measurement(self):
        """How long since the transcript last heard anything: a slow run told
        from a stuck one by the person, never by the page. No verdict in the
        words, and nothing else about the line changes."""
        self.assertEqual(run.working(14), "Claude is working")
        self.assertEqual(run.working(40), "Claude is working · quiet for 40s")
        self.assertEqual(run.working(130), "Claude is working · quiet for 2m 10s")



class PageTest(unittest.TestCase):

    def test_the_page_draws_the_consoles_line_and_keeps_still_if_asked(self):
        """Read from the source, as every page test is: there is no browser in
        this suite. The page says what the console says, and no longer
        *running* of its own accord, which only the tab that started a run
        could; and under reduced motion the dot does not pulse."""
        page = (ROOT / "lib" / "canvas.html").read_text()
        self.assertTrue("said.now" in page, "the page does not draw the console's line")
        self.assertFalse("'running'" in page, "the page still says running itself")
        still = page.split("@media (prefers-reduced-motion: reduce)", 1)
        self.assertEqual(len(still), 2, "nothing is said for reduced motion")
        self.assertRegex(still[1].split("}", 1)[0], r"#state \.dot\s*\{\s*animation: none")


if __name__ == "__main__":
    unittest.main()
