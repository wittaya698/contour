"""The agent's questions are a form (ADR 0034, decisions 1-3; issue 147).

Under a console the agent asks with `ask`: each question carries a suggested
answer and the basis for it, and the page shows them as fields already filled,
each saying where its text came from, with one Approve for them all. Watched,
the run waits at the form; unwatched, the form is set aside as a question is,
and approving it starts a run on the answers. What was approved is kept with
its sources in the space's `.contour/`.
"""
import json
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import one_run    # noqa: E402,F401  one suite run per machine (issue 94)
from test_run_record import RecordCase    # noqa: E402

from console import approvals    # noqa: E402
from console import run as console_run    # noqa: E402
from console.run import ASK_TOOL, Run    # noqa: E402
from lib import form    # noqa: E402
from lib.canvas import PAGE    # noqa: E402
from test_found import function    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WAIT_S = 15

WHAT = {"question": "What is it?", "suggested": "a handheld megaphone",
        "basis": "the reference shows a cone with a handle and a trigger"}
HOW_BIG = {"question": "How big is it in real life?", "suggested": "300 mm long",
           "basis": "a megaphone is about the length of a forearm", "is_size": True}
ASKED = {"questions": [WHAT, HOW_BIG]}


class FormCase(RecordCase):

    def asking(self, payload, requester=None):
        """A run whose agent asks once, and what the gate gave it."""
        given = []

        def drive(prompt, options, gate, say):
            given.append(gate(ASK_TOOL, payload))
            say("text", text="Then that is what it is.")
        run = Run(self.space, drive=drive)
        self.addCleanup(lambda: run.live and run.end())
        run.start("a new model", ceiling=10**6, requester=requester)
        return run, given

    def answered(self, given):
        deadline = time.monotonic() + WAIT_S
        while not given:
            self.assertLess(time.monotonic(), deadline, "the gate never answered")
            time.sleep(0.01)
        return given[0]


class RefusedTest(FormCase):

    def test_a_suggestion_with_no_basis_is_refused_and_nothing_waits(self):
        unfounded = {"questions": [WHAT, dict(HOW_BIG, basis="")]}
        for requester in (None, "the nightly agent"):
            with self.subTest(requester=requester):
                run, given = self.asking(unfounded, requester)
                allow, why = self.answered(given)
                self.assertFalse(allow)
                self.assertIn("basis", why)
                self.assertIn("How big is it in real life?", why)
                self.assertIsNone(run.pending)
                self.assertEqual(approvals.load(self.space), [])
                run.live and run.end()

    def test_a_second_size_question_is_refused(self):
        """One anchor, so one question answers it (ADR 0034, decision 1)."""
        tall = dict(HOW_BIG, question="How tall is it?", suggested="120 mm")
        run, given = self.asking({"questions": [HOW_BIG, tall]})
        allow, why = self.answered(given)
        self.assertFalse(allow)
        self.assertIn("one question is the size", why)
        self.assertIsNone(run.pending)

    def test_ask_user_question_is_refused_and_names_ask(self):
        """So no question skips the form, watched or not (ADR 0034,
        decision 1)."""
        other = {"questions": [{"question": "What is it?", "header": "What",
                                "multiSelect": False, "options": []}]}
        for requester in (None, "the nightly agent"):
            with self.subTest(requester=requester):
                given = []

                def drive(prompt, options, gate, say):
                    given.append(gate("AskUserQuestion", other))
                run = Run(self.space, drive=drive)
                self.addCleanup(lambda r=run: r.live and r.end())
                run.start("a new model", ceiling=10**6, requester=requester)
                allow, why = self.answered(given)
                self.assertFalse(allow)
                self.assertIn("under this console a question is asked with `ask`", why)
                self.assertEqual(approvals.load(self.space), [])
                run.live and run.end()


class WatchedTest(FormCase):

    def waiting(self, run):
        deadline = time.monotonic() + WAIT_S
        while run.pending is None:
            self.assertLess(time.monotonic(), deadline, "the form never stopped the run")
            time.sleep(0.01)
        return run.pending["id"]

    def test_approve_hands_the_run_every_answer_with_its_source(self):
        run, given = self.asking(ASKED)
        at = self.waiting(run)
        self.assertEqual(run.answer(at, True, answers=["a handheld megaphone", "320 mm long"]),
                         {"answered": True})
        allow, answers = self.answered(given)
        self.assertTrue(allow)
        self.assertEqual(answers, [
            {"question": "What is it?", "answer": "a handheld megaphone", "source": "guess"},
            {"question": "How big is it in real life?", "answer": "320 mm long",
             "source": "yours", "is_size": True}])

    def test_the_approved_answers_and_their_sources_are_kept_in_the_space(self):
        """Beside the approvals, for the anchor span's question to read
        (ADR 0034, decision 4)."""
        run, given = self.asking(ASKED)
        self.assertEqual(form.approved(self.space), [])
        run.answer(self.waiting(run), True, answers=["a handheld megaphone", "320 mm long"])
        self.answered(given)
        [kept] = form.approved(self.space)
        self.assertEqual(kept["answers"], given[0][1])
        self.assertEqual(kept["run"], run.latest["run"])
        self.assertTrue((self.space / ".contour" / form.NAME).is_file())


    def test_a_form_waiting_when_the_run_is_ended_from_outside_is_set_aside(self):
        """By somebody who never saw it, so it waits for the person as an
        unwatched run's would (ADR 0031, decision 3)."""
        run, _ = self.asking(ASKED)
        self.waiting(run)
        run.end("stopped with contour stop", aside=True)
        [kept] = approvals.shown(self.space)
        self.assertEqual(kept["category"], "question")
        self.assertEqual([f["source"] for f in kept["fields"]], ["guess", "guess"])


class UnwatchedTest(FormCase):

    def test_an_ask_is_set_aside_and_approving_it_starts_a_run_on_the_answers(self):
        """Nothing resumes: the run that asked goes on, and the answers start
        one of their own (ADR 0028, decision 2)."""
        _, given = self.asking(ASKED, requester="the nightly agent")
        said = self.until("finished")
        allow, why = given[0]
        self.assertFalse(allow)
        self.assertIn("the user will answer it later", why)
        self.assertEqual(said["approvals"], ["What is it? How big is it in real life?"])
        [waiting] = approvals.shown(self.space)
        self.assertEqual([f["text"] for f in waiting["fields"]],
                         ["a handheld megaphone", "300 mm long"])
        done = approvals.answer(self.space, waiting["id"], True,
                                answers=["a handheld megaphone", "320 mm long"])
        self.assertTrue(done["answered"])
        for line in ("What is it?", "a handheld megaphone (Claude's guess, approved)",
                     "How big is it in real life?", "320 mm long (yours)"):
            self.assertIn(line, done["prompt"])
        self.assertEqual([a["source"] for a in form.approved(self.space)[0]["answers"]],
                         ["guess", "yours"])
        self.assertEqual(approvals.load(self.space), [])


class ToolTest(unittest.TestCase):
    """`ask` as the agent is given it, and its answers as the agent reads
    them."""

    def test_it_says_every_question_carries_a_suggestion_and_its_basis(self):
        said = console_run.ASKER["description"]
        self.assertIn("suggested answer", said)
        self.assertIn("basis", said)
        self.assertIn("never in your closing", said)
        self.assertEqual(ASK_TOOL, f"mcp__contour__{console_run.ASKER['name']}")
        question = console_run.ASKER["schema"]["properties"]["questions"]["items"]
        self.assertEqual(set(question["required"]), {"question", "suggested", "basis"})
        self.assertEqual(question["properties"]["is_size"]["type"], "boolean")

    def test_the_driver_hands_the_approved_answers_back_on_the_call(self):
        """Run under the console's interpreter, where the SDK is."""
        python = ROOT / ".venv" / "bin" / "python"
        if not python.exists():
            self.skipTest("no console environment")
        answers = [{"question": "What is it?", "answer": "a megaphone", "source": "yours"}]
        done = subprocess.run([str(python), "-c", (
            "from console import agent\n"
            f"a = agent.result({ASK_TOOL!r}, {ASKED!r}, True, {answers!r})\n"
            f"print(a.updated_input == {{**{ASKED!r}, 'answers': {answers!r}}})\n")],
            cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(done.stdout.split(), ["True"], done.stderr)


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class PageTest(unittest.TestCase):
    """The form on the page. Where a field's label comes from is a function of
    its script, run under node as the browser gets it; how it looks is for
    eyes on a real console."""

    def labelled(self, field, value):
        page = PAGE.read_text(encoding="utf-8")
        js = (function(page, "labelled") + page.split("// LABELS\n")[1].split("\n\n")[0]
              + f"\nconsole.log(JSON.stringify(labelled({json.dumps(field)}, "
                f"{json.dumps(value)})));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_a_field_says_where_its_text_came_from_and_an_edit_makes_it_yours(self):
        guess = {"text": "a megaphone", "source": "guess"}
        self.assertEqual(self.labelled(guess, "a megaphone"), "Claude's guess")
        self.assertEqual(self.labelled(guess, "a loudhailer"), "yours")
        chat = {"text": "320 mm long", "source": "chat"}
        self.assertEqual(self.labelled(chat, "320 mm long"), "from the chat")
        self.assertEqual(self.labelled(chat, "330 mm long"), "yours")

    def test_one_approve_sends_every_field_watched_or_set_aside(self):
        page = PAGE.read_text(encoding="utf-8")
        form = function(page, "question")
        self.assertIn("asking.fields", form)
        self.assertIn(".basis", form)
        self.assertIn("Approve", page.split('<template id="question">')[1].split("</template>")[0])
        self.assertRegex(function(page, "turn"), r"category === 'question'")
        self.assertRegex(page, r"ask\('/verdict', \{ id: event\.id, allow: true, answers: answers \}\)")
        self.assertRegex(function(page, "approval"),
                         r"ask\('/approval', \{ id: a\.id, answers: answers \}\)")


if __name__ == "__main__":
    unittest.main()
