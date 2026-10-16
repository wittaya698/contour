"""`contour stop`: a stop that answers no gate (ADR 0027, decision 9; issue 87).

Against a live console driven by the stand-in agent, because what is under test
is one process reaching another: the launcher, standing outside the space, and
the console holding it.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_console import ROOT, ConsoleCase    # noqa: E402

sys.path.insert(0, str(ROOT))

from console import approvals    # noqa: E402
from console.run import SPEC_TOOL    # noqa: E402
from lib import last_run, lock    # noqa: E402

CONTOUR = ROOT / "contour"
SPEC_WRITE = {"tool": SPEC_TOOL, "content": "revision: 2\ndepth: 640\n",
              "case": "Span m4 reads 640 mm, so the depth is 640."}
CASE = "Span m4 reads 640 mm, so the depth is 640."
WAIT_S = 10


class StopCase(ConsoleCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.beaky = self.root / "beaky"
        (self.beaky / ".contour").mkdir(parents=True)
        (self.beaky / ".contour" / "project").write_text("# Contour model space\n")
        (self.beaky / "sheet.png").write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")
        (self.beaky / "spec.yaml").write_text("revision: 1\ndepth: 600\n")

    def contour(self, *args, cwd=None, **env):
        return subprocess.run([sys.executable, str(CONTOUR), *args],
                              cwd=str(cwd or self.root), capture_output=True, text=True,
                              env=dict(os.environ, CONTOUR_SPACES=str(self.root), **env),
                              timeout=60)

    def parked(self):
        """A console in `beaky`, its run stopped at a spec write."""
        proc, url = self.driven({"say": CASE}, {"call": SPEC_WRITE}, space=self.beaky)
        self.ask(url, "/run", {"prompt": "make the beak longer"})
        self.gate(url)
        return proc, url

    def until(self, state):
        deadline = time.monotonic() + WAIT_S
        while time.monotonic() < deadline:
            said = last_run.read(self.beaky)
            if said and said["state"] == state:
                return said
            time.sleep(0.02)
        self.fail(f"the record never said {state!r}: {last_run.read(self.beaky)}")


class StopTest(StopCase):

    def test_stop_ends_a_parked_run_and_gives_the_space_back(self):
        self.parked()
        r = self.contour("stop", "beaky")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        said = self.until("stopped")
        self.assertEqual(said["why"], "stopped with contour stop")
        self.assertIsNone(lock.holder(self.beaky))

    def test_stop_ends_a_working_run_and_leaves_its_edits(self):
        """No gate to fall back on: the agent is mid-turn. What it already wrote
        stays in the space, uncommitted, for the person to look at."""
        edited = self.beaky / "build.py"
        _, url = self.driven({"keep_prompt": str(edited)}, {"busy": 30},
                             {"say": "done"}, space=self.beaky)
        self.ask(url, "/run", {"prompt": "make the beak longer"})
        self.until("running")
        deadline = time.monotonic() + WAIT_S
        while not edited.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        r = self.contour("stop", "beaky")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.until("stopped")["why"], "stopped with contour stop")
        self.assertIsNone(lock.holder(self.beaky))
        self.assertEqual(edited.read_text(), "make the beak longer")


class WaitingTest(StopCase):

    def test_the_hold_refuses_in_the_gates_words_while_one_is_parked(self):
        """Not *held by pid 4127*: the space is waiting for a person, and the
        refusal says for what and the two ways on (ADR 0027, decision 9)."""
        self.parked()
        r = self.contour("check", cwd=self.beaky)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("beaky is waiting for you: Claude wants to change the spec",
                      r.stderr)
        self.assertIn("contour stop beaky", r.stderr)


class RefusedTest(StopCase):

    def test_a_space_with_no_run_has_nothing_to_stop(self):
        r = self.contour("stop", "beaky")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no run to stop in beaky", r.stdout)

    def test_a_terminals_build_is_not_stopped(self):
        """The person's own command, at their own Ctrl-C. A stand-in process
        holds the space, so a stop that signalled it anyway would end it."""
        holder = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        self.addCleanup(holder.wait)
        self.addCleanup(holder.kill)
        rec = lock.take(self.beaky, "check")
        rec["pid"] = holder.pid
        lock.path(self.beaky).write_text(json.dumps(rec))
        r = self.contour("stop", "beaky")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not a console's run", r.stdout)
        time.sleep(0.2)
        self.assertIsNone(holder.poll())

    def test_a_run_cannot_stop_itself(self):
        """Anyone but the run's own agent (ADR 0027, decision 9): an agent that
        could end its run at a gate would be choosing what happens to it."""
        self.parked()
        r = self.contour("stop", "beaky", CONTOUR_RUN=lock.holder(self.beaky)["run"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("cannot stop itself", r.stdout)
        self.assertEqual(last_run.read(self.beaky)["state"], "waiting for you")


class UnreachableTest(StopCase):
    """A console whose tab its person has lost, with no run going, holds the
    space and no lock: `stop` ends it (ADR 0031, decision 2)."""

    def test_stop_ends_a_console_with_no_run_going(self):
        proc, url = self.launch(self.beaky)
        self.ask(url, "/beat", {"hidden": True})      # a tab left in the background
        r = self.contour("stop", "beaky")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ok   closed the console on beaky; nothing was running", r.stdout)
        self.assertEqual(proc.wait(timeout=WAIT_S), 0)

    def test_a_gate_waiting_when_stop_lands_is_set_aside_not_dropped(self):
        """Nobody who saw it answered it, so it waits for the person on the
        console's page, as an unattended run's would (ADR 0031, decision 3)."""
        self.parked()
        r = self.contour("stop", "beaky")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        said = self.until("stopped")
        kept = approvals.load(self.beaky)
        self.assertEqual([(a["category"], a["tool"], a["case"]) for a in kept],
                         [("spec-write", "Edit", CASE)])
        self.assertEqual(said["approvals"], ["Claude wants to change the spec"])
        self.assertEqual((self.beaky / "spec.yaml").read_text(), "revision: 1\ndepth: 600\n")

    def test_a_run_ended_from_its_own_page_keeps_nothing(self):
        """The person was looking at the gate when they ended the run."""
        _, url = self.parked()
        self.ask(url, "/end", {})
        self.until("stopped")
        self.assertEqual(approvals.load(self.beaky), [])


if __name__ == "__main__":
    unittest.main()
