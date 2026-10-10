"""A question parks the run (ADR 0027, decision 12; issue 90).

A question is the agent's `AskUserQuestion`, which reaches the console over the
gate's seam like any call. In a run nobody is watching it parks the run as a gate
does, the person answers it on the page, and the same run carries on with its
context: ending the run instead would throw that away over a one-word answer.
"""
import json
import re
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_console import STAND_IN    # noqa: E402
from test_request import RequestCase    # noqa: E402
from test_run_record import ROOT, RecordCase    # noqa: E402

from console.run import Run    # noqa: E402
from lib import last_run    # noqa: E402

ASKED = {"questions": [{"question": "How long should the beak be?",
                        "header": "Beak", "multiSelect": False,
                        "options": [{"label": "300 mm", "description": "as drawn"},
                                    {"label": "340 mm", "description": "longer"}]}]}


class ParkedTest(RecordCase):

    def asking(self, requester="the nightly agent"):
        """A run whose agent asks one question, and what the gate gave it."""
        given = []

        def drive(prompt, options, gate, say):
            given.append(gate("AskUserQuestion", dict(ASKED)))
            say("text", text="Then the beak it is.")
        run = Run(self.space, drive=drive)
        run.start("make the beak longer", ceiling=10**6, requester=requester)
        self.addCleanup(lambda: run.live and run.end())
        return run, given

    def test_a_question_in_an_unattended_run_parks_it_and_the_record_shows_it(self):
        self.asking()
        said = self.until("waiting for you")
        self.assertEqual(said["act"], "Claude has a question")
        self.assertEqual(said["questions"], ["How long should the beak be?"])

    def test_an_answer_resumes_the_same_run_with_the_answer_in_hand(self):
        run, given = self.asking()
        parked = self.until("waiting for you")
        asked = next(e for e in run.since(0)["events"] if e["kind"] == "question")
        answers = {"How long should the beak be?": "340 mm"}
        self.assertEqual(run.reply(asked["id"], answers), {"answered": True})
        said = self.until("finished")
        self.assertEqual(said["run"], parked["run"])
        self.assertEqual(said["closing"], "Then the beak it is.")
        self.assertNotIn("questions", said)
        self.assertEqual(given, [(True, answers)])

    def test_an_answer_to_another_question_or_a_verdict_answers_nothing(self):
        """A stale tab's reply lands on no later question, and a gate's
        allow is not an answer: a question has no *allow*."""
        run, given = self.asking()
        self.until("waiting for you")
        asked = next(e for e in run.since(0)["events"] if e["kind"] == "question")
        self.assertIsNone(run.reply("not-this-one", {"q": "a"}))
        self.assertIsNone(run.answer(asked["id"], True))
        time.sleep(0.2)
        self.assertEqual(last_run.read(self.space)["state"], "waiting for you")
        self.assertEqual(given, [])

    def test_an_attended_runs_question_is_unchanged(self):
        """Somebody is watching: the question is let through as any call that
        carries no intent is, and nothing parks."""
        _, given = self.asking(requester=None)
        said = self.until("finished")
        self.assertEqual(given, [(True, None)])
        self.assertNotIn("questions", said)

    def test_a_stop_ends_a_run_parked_on_a_question(self):
        run, given = self.asking()
        self.until("waiting for you")
        run.end("stopped with contour stop")
        said = self.until("stopped")
        self.assertEqual(said["why"], "stopped with contour stop")
        self.assertNotIn("questions", said)
        self.assertEqual(given, [])


class PageTest(RequestCase):
    """A console started on a request, parked on a question, and the page that
    answers it."""

    def test_a_parked_question_holds_the_console_and_the_page_answers_it(self):
        """Past the idle clock with nobody beating, as a parked gate is held;
        then one answer, and the run that asked is the run that finishes."""
        proc, url = self.launch(self.beaky, "--request", "make the beak longer",
                                "--requester", "the nightly agent",
                                CONTOUR_HOME=str(self.home), CONTOUR_CONSOLE_IDLE="1",
                                CONTOUR_CONSOLE_AGENT=f"{STAND_IN}:drive",
                                CONTOUR_AGENT_SCRIPT=json.dumps([
                                    {"ask": ASKED["questions"]}, {"say": "done"}]))
        said = self.transcript(url, lambda ev: any(e["kind"] == "question" for e in ev))
        asked = next(e for e in said if e["kind"] == "question")
        self.assertEqual(asked["questions"], ASKED["questions"])
        parked = self.until("waiting for you")
        time.sleep(3)
        self.assertIsNone(proc.poll(), "the idle clock ended a parked question")
        self.keep_beating(url, proc)          # the person opens the page to answer
        answers = {"How long should the beak be?": "340 mm"}
        self.assertEqual(self.ask(url, "/answer", {"id": asked["id"], "answers": answers}),
                         (200, {"answered": True}))
        said = self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        self.assertIn({"answers": answers},
                      [{"answers": e.get("answers")} for e in said if e["kind"] == "result"])
        self.assertEqual(self.until("finished")["run"], parked["run"])


class OnlyThePageTest(unittest.TestCase):
    """No command and no connector tool answers a question: an answer becomes
    intent, and only the person's is the person's (ADR 0027, decision 12)."""

    def test_the_one_caller_of_an_answer_is_the_pages_route(self):
        callers = sorted(str(f.relative_to(ROOT)) for d in ("lib", "console", "tools")
                         for f in (ROOT / d).rglob("*.py")
                         if re.search(r"\.reply\(", f.read_text(encoding="utf-8")))
        callers += [n for n in ("contour", "contour-console")
                    if ".reply(" in (ROOT / n).read_text(encoding="utf-8")]
        self.assertEqual(callers, ["console/server.py"])

    def test_the_page_answers_with_the_answers_and_nothing_else(self):
        page = (ROOT / "lib" / "canvas.html").read_text(encoding="utf-8")
        self.assertIn('<template id="question">', page)
        body = re.search(r"ask\('/answer', \{([^}]*)\}", page.split("<script>", 1)[1])
        self.assertIsNotNone(body, "the page never answers a question")
        self.assertEqual(set(re.findall(r"(\w+):", body.group(1))), {"id", "answers"})


class DriverTest(unittest.TestCase):
    """The real driver gives the person's answers back to the SDK as the
    question's own input, filled in, which is how the same session carries on.
    Run under the console's interpreter, where the SDK is."""

    def test_the_answers_go_back_on_the_question_and_a_verdict_stays_a_verdict(self):
        python = ROOT / ".venv" / "bin" / "python"
        if not python.exists():
            self.skipTest("no console environment")
        done = subprocess.run([str(python), "-c", (
            "from console import agent\n"
            f"asked = {ASKED!r}\n"
            "a = agent.result('AskUserQuestion', asked, True, {'How long?': '340 mm'})\n"
            "print(a.updated_input == {**asked, 'answers': {'How long?': '340 mm'}})\n"
            "b = agent.result('Bash', {'command': 'ls'}, True, None)\n"
            "print(b.updated_input is None)\n"
            "c = agent.result('Bash', {'command': 'ls'}, False, 'no')\n"
            "print(c.message)\n")], cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(done.stdout.split(), ["True", "True", "no"], done.stderr)


if __name__ == "__main__":
    unittest.main()
