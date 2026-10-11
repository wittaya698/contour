"""A space records its latest run (ADR 0027, decision 8; issue 86).

Driven in-process, as `InheritsTest` drives `console/run.py`: the record is the
console's stdlib half, and proving it must not need the SDK or a server. The
agent is a function given the same two callbacks the real driver is given.
"""
import json
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from console.run import SPEC_TOOL, Run, Stopped    # noqa: E402
from lib import last_run       # noqa: E402

WAIT_S = 5


CASE = "Span m4 reads 640 mm, so the depth is 640."
"""What an agent says before a spec write: the numbers it sets (issue 106)."""


class RecordCase(unittest.TestCase):

    def setUp(self):
        self.space = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.space, True)
        (self.space / ".contour").mkdir()
        (self.space / ".contour" / "project").write_text("# Contour model space\n")

    def started(self, drive, prompt="make the beak longer"):
        """A run, begun, and stopped however the test leaves it. Its agent
        makes its case first, as one does before a spec write (issue 106)."""
        def argued(prompt, options, gate, say):
            say("text", text=CASE)
            return drive(prompt, options, gate, say)
        run = Run(self.space, drive=argued)
        run.start(prompt)
        self.addCleanup(lambda: run.live and run.end())
        return run

    def until(self, state):
        """The record, once it says `state`."""
        deadline = time.monotonic() + WAIT_S
        while time.monotonic() < deadline:
            said = last_run.read(self.space)
            if said and said["state"] == state:
                return said
            time.sleep(0.01)
        self.fail(f"the record never said {state!r}: {last_run.read(self.space)}")


class RunningTest(RecordCase):

    def test_a_run_says_it_is_running_and_what_it_was_asked(self):
        held = threading.Event()
        self.addCleanup(held.set)
        self.started(lambda prompt, options, gate, say: held.wait(WAIT_S))
        said = self.until("running")
        self.assertEqual(said["prompt"], "make the beak longer")
        self.assertIsNone(said["requester"])


class WaitingTest(RecordCase):

    WRITE = {"content": "revision: 2\ndepth: 640\n",
             "case": "Span m4 reads 640 mm, so the depth is 640."}

    def parked(self):
        """A run stopped at a spec write, and the record while it waits."""
        (self.space / "spec.yaml").write_text("revision: 1\ndepth: 600\n")
        answered = []
        run = self.started(lambda prompt, options, gate, say:
                           answered.append(gate(SPEC_TOOL, dict(self.WRITE))))
        return run, self.until("waiting for you"), answered

    def test_a_parked_gate_names_the_act_in_the_gates_words(self):
        _, said, _ = self.parked()
        self.assertEqual(said["act"], "Claude wants to change the spec")

    def test_a_parked_gate_never_shows_the_call_or_what_it_changes(self):
        """The case for a change is made on the page (rule 1): a requester that
        saw *600 -> 640* without the span would argue it in chat."""
        self.parked()
        kept = last_run.path(self.space).read_text()
        for leaked in ("640", "depth", "spec.yaml", "Edit"):
            self.assertNotIn(leaked, kept)

    def test_an_answered_gate_puts_the_run_back_to_running(self):
        (self.space / "spec.yaml").write_text("revision: 1\ndepth: 600\n")
        after = threading.Event()
        self.addCleanup(after.set)

        def drive(prompt, options, gate, say):
            gate(SPEC_TOOL, dict(self.WRITE))
            after.wait(WAIT_S)
        run = self.started(drive)
        self.until("waiting for you")
        run.answer(gated(run), allow=False, reason="not yet")
        said = self.until("running")
        self.assertNotIn("act", said)


class FinishedTest(RecordCase):

    def test_a_finished_run_says_how_it_ended_what_it_cost_and_what_was_refused(self):
        (self.space / "spec.yaml").write_text("revision: 1\ndepth: 600\n")
        (self.space / ".contour" / "last-build.json").write_text(
            json.dumps({"ok": True, "built": True, "results": []}))

        def drive(prompt, options, gate, say):
            gate(SPEC_TOOL, dict(WaitingTest.WRITE))
            say("usage", usage={"input_tokens": 10, "output_tokens": 2})
            say("text", text="The beak is 10% longer.")
        run = self.started(drive)
        self.until("waiting for you")
        run.answer(gated(run), allow=False, reason="not the depth")
        said = self.until("finished")
        self.assertEqual(said["closing"], "The beak is 10% longer.")
        self.assertEqual(said["vetoes"], [{"act": "Claude wants to change the spec",
                                           "reason": "not the depth"}])
        self.assertEqual(said["verdict"]["line"], "matches the spec")
        self.assertEqual(said["spend"]["turns"], 1)
        self.assertGreater(said["spend"]["weighted"], 0)

    def test_the_verdict_is_the_last_checks_and_not_a_copy_of_it(self):
        """Read when the record is: a copy would be a second verdict to drift."""
        self.started(lambda prompt, options, gate, say: None)
        self.until("finished")
        self.assertNotIn("verdict", json.loads(last_run.path(self.space).read_text()))


class StoppedTest(RecordCase):

    def test_a_run_ended_from_the_page_is_stopped_and_says_so(self):
        (self.space / "spec.yaml").write_text("revision: 1\ndepth: 600\n")
        run = self.started(lambda prompt, options, gate, say:
                           gate(SPEC_TOOL, dict(WaitingTest.WRITE)))
        self.until("waiting for you")
        run.end()
        said = self.until("stopped")
        self.assertEqual(said["why"], "you ended the run")
        self.assertNotIn("act", said)

    def test_a_stop_answers_no_gate(self):
        """The parked call never happens and the agent is not told no, so it has
        nothing to work around; and nobody refused anything, so no veto is kept
        (ADR 0027, decision 9; issue 87)."""
        (self.space / "spec.yaml").write_text("revision: 1\ndepth: 600\n")
        told = []

        def drive(prompt, options, gate, say):
            try:
                told.append(gate(SPEC_TOOL, dict(WaitingTest.WRITE)))
            except Stopped:
                told.append("stopped")
                raise
        run = self.started(drive)
        self.until("waiting for you")
        run.end()
        self.until("stopped")
        deadline = time.monotonic() + WAIT_S
        while not told and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(told, ["stopped"])
        self.assertFalse((self.space / "vetoes.json").exists())

    def test_a_run_that_failed_is_stopped_and_says_why(self):
        def drive(prompt, options, gate, say):
            raise RuntimeError("no network")
        self.started(drive)
        self.assertEqual(self.until("stopped")["why"], "the run failed: no network")


class ReplacedTest(RecordCase):

    def test_a_second_run_replaces_the_first(self):
        """The newest run only: a status, not a history."""
        (self.space / "spec.yaml").write_text("revision: 1\ndepth: 600\n")
        first = self.started(lambda prompt, options, gate, say:
                             gate(SPEC_TOOL, dict(WaitingTest.WRITE)))
        self.until("waiting for you")
        first.answer(gated(first), allow=False, reason="no")
        self.until("finished")
        held = threading.Event()
        self.addCleanup(held.set)
        self.started(lambda prompt, options, gate, say: held.wait(WAIT_S),
                     prompt="paint it blue")
        said = self.until("running")
        self.assertEqual(said["prompt"], "paint it blue")
        self.assertEqual(said["vetoes"], [])
        self.assertNotIn("closing", said)


def gated(run):
    """The id of the gate a run is parked at, as the page learns it."""
    return [e for e in run.since(0)["events"] if e["kind"] == "gate"][-1]["id"]


if __name__ == "__main__":
    unittest.main()
