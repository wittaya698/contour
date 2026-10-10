"""`contour request`: an unattended run (ADR 0027, decisions 3, 4, 5, 6, 10 and
11; issue 89).

Against a live console driven by the stand-in agent, started the way a
requester starts one: by a command that stands outside the space and never sees
the console's URL.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_console import ROOT, STAND_IN, ConsoleCase    # noqa: E402

sys.path.insert(0, str(ROOT))

from console.run import Run    # noqa: E402
from lib import intent, last_run, lock, policy, presence    # noqa: E402
from test_run_record import RecordCase    # noqa: E402

CONTOUR = ROOT / "contour"
SPEC_WRITE = {"tool": "Edit", "file_path": "spec.yaml",
              "old_string": "depth: 600", "new_string": "depth: 640"}
WAIT_S = 15


class RequestCase(ConsoleCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.home = Path(tempfile.mkdtemp())
        (self.home / "ceiling.json").write_text('{"weighted": 1000000}\n')
        self.beaky = self.root / "beaky"
        (self.beaky / ".contour").mkdir(parents=True)
        (self.beaky / ".contour" / "project").write_text("# Contour model space\n")
        (self.beaky / "sheet.png").write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")
        (self.beaky / "spec.yaml").write_text("revision: 1\ndepth: 600\n")
        # Whatever this test started in the space, and nothing else: the
        # console it asked for never told anybody its URL or its pid.
        self.addCleanup(self.reaped)

    def reaped(self):
        for page in presence.live(self.beaky):
            try:
                os.kill(page["pid"], signal.SIGTERM)
            except OSError:
                pass

    def request(self, *args, script=(), **env):
        """`contour request beaky <args>`, as JSON, and how it exited."""
        env.setdefault("CONTOUR_HOME", str(self.home))
        r = subprocess.run(
            [sys.executable, str(CONTOUR), "request", "beaky", *args],
            cwd=str(self.root), capture_output=True, text=True, timeout=60,
            env=dict(os.environ, CONTOUR_SPACES=str(self.root),
                     CONTOUR_CONSOLE_PYTHON=sys.executable,
                     CONTOUR_CONSOLE_AGENT=f"{STAND_IN}:drive",
                     CONTOUR_AGENT_SCRIPT=json.dumps(list(script)), **env))
        try:
            return json.loads(r.stdout), r
        except ValueError:
            self.fail(f"not JSON: {r.stdout!r} {r.stderr!r}")

    def until(self, state):
        deadline = time.monotonic() + WAIT_S
        while time.monotonic() < deadline:
            said = last_run.read(self.beaky)
            if said and said["state"] == state:
                return said
            time.sleep(0.05)
        self.fail(f"the record never said {state!r}: {last_run.read(self.beaky)}")

    def gone(self):
        """Once no console serves the space; False if one still does."""
        deadline = time.monotonic() + WAIT_S
        while time.monotonic() < deadline:
            if not presence.live(self.beaky):
                return True
            time.sleep(0.05)
        return False


class StartsTest(RequestCase):

    def test_a_request_starts_a_run_that_ends_its_console_when_it_ends(self):
        said, r = self.request("make the beak longer", "--as", "the nightly agent",
                               script=({"say": "The beak is longer."},))
        self.assertEqual(r.returncode, 0, said)
        self.assertTrue(said["started"], said)
        record = self.until("finished")
        self.assertEqual(record["run"], said["run"])
        self.assertEqual(record["prompt"], "make the beak longer")
        self.assertEqual(record["requester"], "the nightly agent")
        self.assertTrue(self.gone(), "the console outlived its run with no page open")
        self.assertIsNone(lock.holder(self.beaky))

    def test_a_parked_question_outlives_the_idle_clock_and_a_stop_ends_it(self):
        """Silence is not an answer (ADR 0027, decision 9): with nobody there,
        the console waits at the question for as long as it takes, and ends with
        its run when somebody stops it."""
        said, _ = self.request("make the beak longer",
                               script=({"ask": [{"question": "How long?"}]},),
                               CONTOUR_CONSOLE_IDLE="1")
        self.assertTrue(said["started"], said)
        self.until("waiting for you")
        time.sleep(3)
        self.assertTrue(presence.live(self.beaky), "the idle clock ended a parked gate")
        self.assertEqual(last_run.read(self.beaky)["state"], "waiting for you")
        r = subprocess.run([sys.executable, str(CONTOUR), "stop", "beaky"],
                           cwd=str(self.root), capture_output=True, text=True, timeout=60,
                           env=dict(os.environ, CONTOUR_SPACES=str(self.root)))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.gone(), "the console outlived its stopped run")

    def test_a_working_run_outlives_the_idle_clock(self):
        """No gate, no page: the run is what keeps the console, not a touch."""
        said, _ = self.request("make the beak longer",
                               script=({"busy": 3}, {"say": "done"}),
                               CONTOUR_CONSOLE_IDLE="1")
        self.assertTrue(said["started"], said)
        self.assertEqual(self.until("finished")["closing"], "done")


FLOOR = (("Edit", {"file_path": "spec.yaml", "old_string": "a", "new_string": "b"}),
         ("Write", {"file_path": "refs/side.png", "content": "x"}),
         ("Bash", {"command": "git commit -m 'longer beak'"}))
"""A spec write, a reference write and saving a version (ADR 0027, decision 10)."""


class FloorTest(RecordCase):
    """With an ask-list that lets everything through, what nobody has seen
    still waits for somebody who has."""

    def setUp(self):
        super().setUp()
        home = Path(tempfile.mkdtemp())
        (home / "ask-list.yaml").write_text(policy.dumps({"spaces": {str(self.space): {
            "allow": ["spec-write", "ref-write", "build", "commit", "push"]}}}))
        patched = mock.patch.dict(os.environ, {"CONTOUR_HOME": str(home)})
        patched.start()
        self.addCleanup(patched.stop)

    def through(self, tool, call, requester):
        """Whether this call is made without the person, in a run started by
        `requester`: not parked, and not set aside for later."""
        given = []
        run = Run(self.space, drive=lambda prompt, options, gate, say:
                  given.append(gate(tool, dict(call))))
        run.start("make the beak longer", ceiling=10**6, requester=requester)
        self.addCleanup(lambda: run.live and run.end())
        deadline = time.monotonic() + WAIT_S
        while run.live and time.monotonic() < deadline:
            if run.pending is not None:
                run.end()
                return False
            time.sleep(0.01)
        [(allow, _)] = given
        return allow

    def test_an_unattended_run_holds_back_the_floor_whatever_the_list_says(self):
        for tool, call in FLOOR:
            self.assertFalse(self.through(tool, call, "the nightly agent"), call)

    def test_an_unattended_run_lets_through_what_the_list_lets_through(self):
        self.assertTrue(self.through("Bash", {"command": "contour check"},
                                     "the nightly agent"))

    def test_an_attended_run_follows_the_list_alone(self):
        self.assertTrue(self.through(*FLOOR[0], None))


class PageTest(RequestCase):
    """A requested console with a page open on it: what the person sees, and
    what the page does not change."""

    def opened(self, *script):
        """A console started on a request, as `contour request` starts one, but
        with its URL in hand, so a test can be the page; and an ask-list that
        lets everything through."""
        (self.home / "ask-list.yaml").write_text(policy.dumps({"spaces": {
            str(self.beaky): {"allow": list(intent.categories())}}}))
        return self.launch(self.beaky, "--request", "make the beak longer",
                           "--requester", "the nightly agent",
                           CONTOUR_HOME=str(self.home),
                           CONTOUR_CONSOLE_AGENT=f"{STAND_IN}:drive",
                           CONTOUR_AGENT_SCRIPT=json.dumps(list(script)))

    def test_opening_the_page_mid_run_does_not_lift_the_floor(self):
        proc, url = self.opened({"busy": 1}, {"call": SPEC_WRITE})
        self.keep_beating(url, proc)
        said = self.transcript(url, lambda ev: any(e["kind"] == "aside" for e in ev))
        [aside] = [e for e in said if e["kind"] == "aside"]
        self.assertEqual(aside["category"], "spec-write")
        self.assertNotIn("gate", [e["kind"] for e in said])
        self.assertIn("this run was asked for by the nightly agent; "
                      "some actions always ask you",
                      [e.get("text") for e in said])

    def test_a_page_open_when_the_run_ends_keeps_the_console(self):
        """The page's rule takes over (ADR 0027, decision 4): the person is
        looking at what the run did."""
        proc, url = self.opened({"busy": 1}, {"say": "done"})
        self.keep_beating(url, proc)
        self.until("finished")
        time.sleep(1)
        self.assertIsNone(proc.poll(), "the console ended under an open page")


class RefusedTest(RequestCase):
    """Each in words that already exist for it, and none starting a console."""

    def refused(self, **env):
        said, r = self.request("make the beak longer", **env)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(said["started"])
        return said["why"]

    def test_a_held_space_is_refused_in_the_holds_words(self):
        """A parked gate says what it is waiting for, as `contour check` would
        be told (ADR 0027, decisions 3 and 9)."""
        _, url = self.driven({"call": SPEC_WRITE}, space=self.beaky)
        self.ask(url, "/run", {"prompt": "paint it blue"})
        self.gate(url)
        self.assertIn("beaky is waiting for you: Claude wants to change the spec",
                      self.refused())
        self.assertEqual(last_run.read(self.beaky)["prompt"], "paint it blue")

    def test_a_space_with_a_console_open_is_the_persons_and_refused(self):
        """In the lobby's words (ADR 0027, decision 6): the person types the
        request into that page themselves."""
        self.launch(self.beaky)
        self.assertIn("already open in a console", self.refused())
        self.assertIn("its tab is the way in", self.refused())
        self.assertIsNone(last_run.read(self.beaky))

    def test_with_no_ceiling_set_a_request_is_refused(self):
        """Silence decides nothing: the first request makes the person choose a
        number (ADR 0027, decision 13)."""
        (self.home / "ceiling.json").unlink()
        self.assertIn("no ceiling set", self.refused())
        self.assertIn("contour ceiling <n>", self.refused())
        self.assertIsNone(last_run.read(self.beaky))
        self.assertEqual(presence.live(self.beaky), [])


if __name__ == "__main__":
    unittest.main()
