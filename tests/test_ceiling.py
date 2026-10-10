"""A ceiling: an unattended run's cost, bounded in advance (ADR 0027, decision
13; issue 88).

The stop is driven in-process, as `test_run_record.py` drives a run: what is
under test is when a run ends, and that needs neither the SDK nor a server.
"""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_run_record import ROOT, RecordCase    # noqa: E402

from console.run import Run, Stopped    # noqa: E402
from lib import last_run    # noqa: E402

TURN = {"input_tokens": 100, "output_tokens": 0}
"""One turn, weighing 100."""


class ReachedTest(RecordCase):

    def costing(self, turns, ceiling):
        """A run that spends `turns` turns of 100 under `ceiling`, and how many
        it got to spend."""
        spent = []

        def drive(prompt, options, gate, say):
            for n in range(turns):
                say("usage", usage=dict(TURN))
                spent.append(n)
        run = Run(self.space, drive=drive)
        run.start("make the beak longer", ceiling=ceiling)
        self.addCleanup(lambda: run.live and run.end())
        return run, spent

    def test_a_run_stops_at_the_first_turn_that_reaches_its_ceiling(self):
        _, spent = self.costing(5, ceiling=300)
        said = self.until("stopped")
        self.assertEqual(said["why"], "reached your limit of 300")
        self.assertEqual(said["spend"]["turns"], 3)
        self.assertEqual(spent, [0, 1])

    def test_a_run_under_its_ceiling_runs_to_the_end(self):
        _, spent = self.costing(3, ceiling=301)
        said = self.until("finished")
        self.assertEqual(said["spend"]["turns"], 3)
        self.assertEqual(spent, [0, 1, 2])

    def test_a_run_with_no_ceiling_is_never_stopped_by_one(self):
        """What the page starts: an attended run, whose stop is the person
        watching it (ADR 0019, decision 37)."""
        _, spent = self.costing(20, ceiling=None)
        self.until("finished")
        self.assertEqual(len(spent), 20)

    def test_reaching_it_is_a_stop_that_keeps_the_edits_and_refuses_nothing(self):
        """ADR 0027 decision 9's stop: what the agent wrote stays for the person
        to look at, and nobody refused anything, so no veto is kept."""
        edited = self.space / "build.py"
        told = []

        def drive(prompt, options, gate, say):
            edited.write_text("longer beak")
            try:
                say("usage", usage={"input_tokens": 500})
            except Stopped:
                told.append("stopped")
                raise
        run = Run(self.space, drive=drive)
        run.start("make the beak longer", ceiling=300)
        self.until("stopped")
        deadline = time.monotonic() + 5
        while not told and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(told, ["stopped"])
        self.assertEqual(edited.read_text(), "longer beak")
        self.assertEqual(last_run.read(self.space)["vetoes"], [])
        self.assertFalse((self.space / "vetoes.json").exists())


class SetTest(unittest.TestCase):
    """The ceiling is the person's, set from a terminal beside the ask-list."""

    def setUp(self):
        self.home = tempfile.mkdtemp()

    def contour(self, *args, **env):
        return subprocess.run([sys.executable, str(ROOT / "contour"), "ceiling", *args],
                              cwd=self.home, capture_output=True, text=True, timeout=60,
                              env=dict(os.environ, CONTOUR_HOME=self.home, **env))

    def test_with_none_set_it_says_so(self):
        r = self.contour()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("no ceiling", r.stdout)

    def test_it_can_be_set_shown_and_removed(self):
        self.assertEqual(self.contour("50000").returncode, 0)
        self.assertIn("50000", self.contour().stdout)
        self.assertEqual(self.contour("--remove").returncode, 0)
        self.assertIn("no ceiling", self.contour().stdout)

    def test_a_ceiling_is_a_whole_number_above_nothing(self):
        for bad in ("0", "-5", "lots", "1.5"):
            r = self.contour(bad)
            self.assertNotEqual(r.returncode, 0, bad)
            self.assertIn("whole number", r.stdout, bad)
        self.assertIn("no ceiling", self.contour().stdout)

    def test_a_run_cannot_set_or_remove_its_own_ceiling(self):
        """The agent and the requester never reach it (ADR 0027, decision 13):
        a run that could raise its limit would have none."""
        self.contour("300")
        for args in (("90000",), ("--remove",)):
            r = self.contour(*args, CONTOUR_RUN="r-1")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("a run cannot set its own ceiling", r.stdout)
        self.assertIn("300", self.contour(CONTOUR_RUN="r-1").stdout)


class ReachTest(RecordCase):
    """The console refuses its agent a call that would write the ceiling, as it
    refuses one that would rewrite the ask-list: outright, and not as a gate a
    person might allow by reflex."""

    def answered(self, tool, call):
        told = []
        self.started(lambda prompt, options, gate, say: told.append(gate(tool, call)))
        self.until("finished")
        return told[0]

    def test_writing_the_ceiling_is_refused_by_any_door(self):
        from lib import ceiling
        for tool, call in (("Bash", {"command": "contour ceiling 999999"}),
                           ("Bash", {"command": "cd .. && ./contour ceiling --remove"}),
                           ("Write", {"file_path": str(ceiling.path()), "content": "{}"}),
                           ("Bash", {"command": f"rm {ceiling.path()}"})):
            allowed, why = self.answered(tool, call)
            self.assertFalse(allowed, call)
            self.assertIn("the user's to change", why)

    def test_reading_the_ceiling_is_still_the_agents_to_do(self):
        self.assertEqual(self.answered("Bash", {"command": "contour ceiling"}),
                         (True, None))

if __name__ == "__main__":
    unittest.main()
