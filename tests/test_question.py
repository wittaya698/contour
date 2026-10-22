"""A question is set aside too (ADR 0028, decision 2; issue 98).

A question is the agent's `ask`, which reaches the console over the gate's
seam like any call (ADR 0034; `test_form`). In a run nobody is watching it no
longer parks the run: it is kept with the approvals, the agent is told the
person will answer it later and carries on, and the person's answer on the page
starts a run of its own (`test_approvals_answered`), because nothing resumes.
This undoes issue 90's park.
"""
import re
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_run_record import ROOT, RecordCase    # noqa: E402

from console import approvals    # noqa: E402
from console.run import ASK_TOOL, Run    # noqa: E402
from lib import last_run    # noqa: E402

ASKED = {"questions": [{"question": "How long should the beak be?",
                        "suggested": "300 mm", "basis": "as drawn"}]}
WAIT_S = 15


class AsideTest(RecordCase):

    def asking(self, requester="the nightly agent"):
        """A run whose agent asks one question, and what the gate gave it."""
        given = []

        def drive(prompt, options, gate, say):
            given.append(gate(ASK_TOOL, dict(ASKED)))
            say("text", text="Then the beak it is.")
        run = Run(self.space, drive=drive)
        run.start("make the beak longer", ceiling=10**6, requester=requester)
        self.addCleanup(lambda: run.live and run.end())
        return run, given

    def test_a_question_in_an_unattended_run_is_set_aside_and_the_run_goes_on(self):
        _, given = self.asking()
        said = self.until("finished")
        self.assertEqual(said["closing"], last_run.WITHHELD)
        self.assertEqual(said["approvals"], ["How long should the beak be?"])
        [(allow, why)] = given
        self.assertFalse(allow)
        self.assertIn("the user will answer it later", why)
        self.assertIn("say in your closing", why)

    def test_a_stop_leaves_a_question_set_aside_waiting(self):
        """A stop ends the run and answers nothing (ADR 0028, decision 7)."""
        set_aside = threading.Event()

        def drive(prompt, options, gate, say):
            gate(ASK_TOOL, dict(ASKED))
            set_aside.set()
            threading.Event().wait(WAIT_S)    # working on, till stopped
            say("text", text="never said")
        run = Run(self.space, drive=drive)
        run.start("make the beak longer", ceiling=10**6, requester="the nightly agent")
        self.addCleanup(lambda: run.live and run.end())
        self.assertTrue(set_aside.wait(WAIT_S))
        run.end("stopped with contour stop")
        said = self.until("stopped")
        self.assertEqual(said["approvals"], ["How long should the beak be?"])
        self.assertEqual([a["tool"] for a in approvals.load(self.space)], [ASK_TOOL])


class OnlyThePageTest(unittest.TestCase):
    """No command and no connector tool answers a question: an answer becomes
    intent, and only the person's is the person's (ADR 0027, decision 12)."""

    def test_the_one_caller_of_an_answer_is_the_pages_route(self):
        callers = sorted(str(f.relative_to(ROOT)) for d in ("lib", "console", "tools")
                         for f in (ROOT / d).rglob("*.py")
                         if re.search(r"approval_store\.answer\(|approvals\.answer\(",
                                      f.read_text(encoding="utf-8")))
        callers += [n for n in ("contour", "contour-console")
                    if "approvals.answer(" in (ROOT / n).read_text(encoding="utf-8")]
        self.assertEqual(callers, ["console/server.py"])

    def test_the_page_answers_a_question_set_aside_with_the_answers(self):
        page = (ROOT / "lib" / "canvas.html").read_text(encoding="utf-8")
        self.assertIn('<template id="question">', page)
        script = page.split("function approval(")[1].split("\n}\n")[0]
        self.assertIn("a.category === 'question'", script)
        body = re.search(r"ask\('/approval', \{ id: a\.id, answers: answers \}\)", script)
        self.assertIsNotNone(body, "the page never answers a question set aside")

    def test_no_route_answers_a_question_but_a_gates_and_an_approvals(self):
        """Set aside, nothing parks on one (ADR 0028, decision 2); watched, it
        waits at the form as a gate does, and is answered by the gate's own
        route (ADR 0034, decision 2). No route of its own."""
        page = (ROOT / "lib" / "canvas.html").read_text(encoding="utf-8")
        self.assertNotIn("'/answer'", page)
        self.assertNotIn("def reply(", (ROOT / "console" / "run.py").read_text())
        self.assertNotIn('"/answer"', (ROOT / "console" / "server.py").read_text())


if __name__ == "__main__":
    unittest.main()
