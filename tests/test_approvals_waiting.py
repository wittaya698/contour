"""The space says approvals are waiting (ADR 0028, decisions 5, 6 and 7; issue
99).

*Waiting for you* is something a space has, not a state a run is in: the
lobby's row and the connector's `status` say how many approvals wait and for
what, until none do, and never why. A request is refused while any wait.
"""
import json
import os
import signal
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import one_run    # noqa: E402,F401  one suite run per machine (issue 94)
from executables import executable    # noqa: E402
from test_approvals_answered import ASKED, SAVE, SPEC_WRITE, WAIT_S, AnsweredCase    # noqa: E402

from console import approvals    # noqa: E402
from console.run import Run    # noqa: E402
from lib import cli, connector, last_run, presence, survey    # noqa: E402


class StatusTest(AnsweredCase):

    def test_status_names_the_acts_waiting_and_nothing_under_them(self):
        self.set_aside(SPEC_WRITE, SAVE)
        said = survey.status(self.beaky)
        self.assertEqual(said["approvals"], ["Claude wants to change the spec",
                                             "Save this version?"])
        self.assertIn("2 approvals waiting: Claude wants to change the spec; "
                      "Save this version?", said["said"])
        for leaked in ("640", "depth", "spec.yaml", "m4", "git add"):
            self.assertNotIn(leaked, json.dumps(said))

    def test_the_closing_of_a_run_that_set_something_aside_never_reaches_status(self):
        """Its closing is the agent's account, and with something set aside that
        account is the case for it: *depth 600 to 640*. Withheld for good, not
        only while it waits, since answered it would also be stale (found in
        issue 100's tracer bullet)."""
        def drive(prompt, options, gate, say):
            gate(*SPEC_WRITE)
            say("text", text="I'd like the depth to go from 600 to 640, after span m4.")
        run = Run(self.beaky, drive=drive)
        run.start("make the beak longer", ceiling=10**6, requester="the nightly agent")
        self.until("finished")
        self.assertWithheld()
        self.answer(self.opened(), allow=False, reason="not yet")
        self.assertWithheld()

    def test_once_all_are_answered_the_closing_says_nothing_waits(self):
        """And while one waits it still points at the page: a chat read the
        unchanged sentence as something still waiting, over an empty list, and
        sent the person to the console (issue 105)."""
        self.set_aside(SPEC_WRITE, SAVE)
        self.assertEqual(survey.status(self.beaky)["run"]["closing"], last_run.WITHHELD)
        url = self.opened()
        self.answer(url)
        self.assertEqual(survey.status(self.beaky)["run"]["closing"], last_run.WITHHELD)
        self.answer(url, allow=False, reason="not yet")
        self.assertEqual(survey.status(self.beaky)["run"]["closing"],
                         "this run set something aside, and all of it has been "
                         "answered on its console's page; nothing waits")

    def assertWithheld(self):
        said = json.dumps(survey.status(self.beaky))
        for leaked in ("640", "m4"):
            self.assertNotIn(leaked, said)
        self.assertIn("on its console's page", said)

    def test_a_run_that_set_nothing_aside_keeps_its_closing(self):
        def drive(prompt, options, gate, say):
            say("text", text="The beak is 10% longer and the check is green.")
        run = Run(self.beaky, drive=drive)
        run.start("make the beak longer", ceiling=10**6, requester="the nightly agent")
        self.until("finished")
        self.assertEqual(survey.status(self.beaky)["run"]["closing"],
                         "The beak is 10% longer and the check is green.")

    def test_until_none_are_left(self):
        self.set_aside(SPEC_WRITE, SAVE)
        url = self.opened()
        self.answer(url)
        self.assertEqual(survey.status(self.beaky)["approvals"], ["Save this version?"])
        self.answer(url, allow=False, reason="not yet")
        said = survey.status(self.beaky)
        self.assertEqual(said["approvals"], [])
        self.assertFalse([s for s in said["said"] if "waiting" in s])


class RowTest(AnsweredCase):
    """The lobby's row, from the reading `contour spaces --json` prints."""

    def test_the_row_says_how_many_wait_and_for_what(self):
        self.set_aside(SPEC_WRITE, ASKED)
        row = survey.row(self.beaky, None)
        self.assertEqual(row["approvals"], ["Claude wants to change the spec",
                                            "How long should the beak be?"])
        self.assertEqual(row["awaiting"], "2 approvals waiting: Claude wants to change "
                                          "the spec; How long should the beak be?")

    def test_the_lobby_shows_it_on_the_row(self):
        page = (Path(__file__).resolve().parent.parent / "lib" / "lobby.html").read_text()
        self.assertIn("if (s.awaiting) name.append(para(s.awaiting, 'warn'));", page)


class RefusedTest(AnsweredCase):
    """In the words the command and the connector both say: they are one
    function, `contour request` and the `request` tool alike."""

    def requested(self):
        with mock.patch.dict(os.environ, {"CONTOUR_SPACES": str(self.beaky.parent)}):
            return cli.requested(self.beaky.name, "paint it blue", "the nightly agent")

    def test_a_request_is_refused_while_approvals_wait_naming_the_way_in(self):
        self.set_aside(SPEC_WRITE, SAVE)
        before = last_run.read(self.beaky)["run"]
        said = self.requested()
        self.assertFalse(said["started"])
        self.assertEqual(said["why"], "beaky has 2 approvals waiting; "
                                      "open its console to answer them.")
        self.assertEqual(last_run.read(self.beaky)["run"], before)

    def test_one_waiting_is_said_as_one(self):
        self.set_aside(SPEC_WRITE)
        self.assertEqual(self.requested()["why"], "beaky has 1 approval waiting; "
                                                  "open its console to answer it.")


class OpenTest(AnsweredCase):
    """`open console` once the run that set them aside has ended: no console
    is left to show its page, so one is started, and it shows them (ADR 0028,
    decision 4)."""

    def test_open_console_starts_a_page_showing_them_and_says_no_url(self):
        self.set_aside(SPEC_WRITE, SAVE)
        opened = self.beaky.parent / "opened"
        browser = executable(self.beaky.parent / "browser",
                             '#!/bin/sh\necho "$1" >> "$(dirname "$0")/opened"\n')
        self.addCleanup(lambda: [os.kill(p["pid"], signal.SIGTERM)
                                 for p in presence.live(self.beaky)])
        with mock.patch.dict(os.environ, {"CONTOUR_SPACES": str(self.beaky.parent),
                                          "BROWSER": str(browser),
                                          "CONTOUR_CONSOLE_PYTHON": sys.executable}):
            said = cli.opened("console", "beaky")
        self.assertIsNone(said["refused"], said)
        deadline = time.monotonic() + WAIT_S
        while not (opened.exists() and opened.read_text().strip()):
            self.assertLess(time.monotonic(), deadline, "no page asked for a browser")
            time.sleep(0.1)
        url = opened.read_text().split()[0]
        self.assertEqual([a["act"] for a in self.waiting(url)],
                         ["Claude wants to change the spec", "Save this version?"])
        self.assertNotIn("http", json.dumps(said))


class EndedTest(AnsweredCase):
    """A stop or the ceiling ends the run and answers nothing: what it set
    aside stays waiting (ADR 0028, decision 7)."""

    def test_the_ceiling_ends_a_run_and_leaves_what_it_set_aside_waiting(self):
        def drive(prompt, options, gate, say):
            gate(*SPEC_WRITE)
            for _ in range(5):
                say("usage", usage={"input_tokens": 100, "output_tokens": 0})
        run = Run(self.beaky, drive=drive)
        run.start("make the beak longer", ceiling=300, requester="the nightly agent")
        self.addCleanup(lambda: run.live and run.end())
        self.assertEqual(self.until("stopped")["why"], "reached your limit of 300")
        self.assertEqual(survey.status(self.beaky)["approvals"],
                         ["Claude wants to change the spec"])
        self.assertEqual(len(approvals.load(self.beaky)), 1)

    def test_contour_stop_ends_a_run_and_leaves_what_it_set_aside_waiting(self):
        set_aside = threading.Event()

        def drive(prompt, options, gate, say):
            gate(*SPEC_WRITE)
            set_aside.set()
            threading.Event().wait(WAIT_S)    # working on, till stopped
            say("text", text="never said")
        run = Run(self.beaky, drive=drive)
        run.start("make the beak longer", ceiling=10**6, requester="the nightly agent")
        self.addCleanup(lambda: run.live and run.end())
        self.assertTrue(set_aside.wait(WAIT_S))
        run.end("stopped with contour stop")
        self.until("stopped")
        self.assertEqual(survey.status(self.beaky)["approvals"],
                         ["Claude wants to change the spec"])


class InstructionsTest(unittest.TestCase):
    """What a chat is told to do with approvals it finds waiting (ADR 0028,
    decision 6): say what they are, and ask; never answer."""

    def test_a_chat_asks_now_or_later_and_now_is_open(self):
        said = connector.INSTRUCTIONS
        self.assertIn("approvals waiting", said)
        self.assertIn("now or later", said)
        self.assertIn("Call open (the console) only if they say now", said)

    def test_a_chat_never_answers_relays_a_case_or_says_yes_for_the_user(self):
        said = connector.INSTRUCTIONS
        self.assertIn("never answer one", said)
        self.assertIn("never pass on the case for one", said)
        self.assertIn("never write that the user says yes into a request", said)


if __name__ == "__main__":
    unittest.main()
