"""The chat's size fills the size field (ADR 0034, decision 6; issue 149).

A Desktop chat that made the space may already have heard how big the thing
is. `--said` still carries it on the launch line, since `create` comes before
any form exists, and the console now puts it where the user answers: the size
field of the new-space run's first form, labelled *from the chat*. It beats
Claude's guess, and one identical to the guess stays *Claude's guess*: the
agreement says nothing the page can check (ADR 0034, decision 3).
"""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_console import STAND_IN, ConsoleCase    # noqa: E402
from test_form import FormCase    # noqa: E402

from console import approvals    # noqa: E402
from console.run import ASK_TOOL, Run    # noqa: E402

WHAT = {"question": "What is it?", "suggested": "a handheld megaphone",
        "basis": "the reference shows a cone with a handle"}
HOW_BIG = {"question": "How big is it in real life?", "suggested": "350 mm long",
           "basis": "a megaphone is about the length of a forearm", "is_size": True}


class PrefilledTest(ConsoleCase):

    def form(self, said, *asks):
        """The fields of the gate the new-space run's first `ask` stops at."""
        url = self.launch(None, "--begin", "new-space", *(("--said", said) if said else ()),
                          CONTOUR_HOME=tempfile.mkdtemp(),
                          CONTOUR_CONSOLE_AGENT=f"{STAND_IN}:drive",
                          CONTOUR_AGENT_SCRIPT=json.dumps([{"ask": a} for a in asks]))[1]
        gate, _ = self.gate(url)
        return gate["said"]["fields"], url

    def test_a_size_the_chat_said_fills_the_size_field_as_from_the_chat(self):
        fields, _ = self.form("width:300", [WHAT, HOW_BIG])
        self.assertEqual([(f["text"], f["source"]) for f in fields],
                         [("a handheld megaphone", "guess"), ("300 mm wide", "chat")])

    def test_a_size_the_chat_said_identical_to_claudes_guess_stays_claudes_guess(self):
        fields, _ = self.form("width:300", [WHAT, dict(HOW_BIG, suggested="300 mm wide")])
        self.assertEqual((fields[1]["text"], fields[1]["source"]), ("300 mm wide", "guess"))

    def test_with_no_said_size_every_field_is_claudes_guess(self):
        fields, _ = self.form(None, [WHAT, HOW_BIG])
        self.assertEqual([f["source"] for f in fields], ["guess", "guess"])

    def test_only_the_first_form_is_filled_from_the_chat(self):
        """A later form asks again, and a size said once in a chat answers
        what was asked first."""
        fields, url = self.form("width:300", [WHAT, HOW_BIG], [HOW_BIG])
        first, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": first["id"], "allow": True,
                                   "answers": [f["text"] for f in fields]})
        said = self.transcript(url, lambda ev: sum(e["kind"] == "gate" for e in ev) == 2)
        later = [e for e in said if e["kind"] == "gate"][1]
        self.assertEqual([(f["text"], f["source"]) for f in later["said"]["fields"]],
                         [("350 mm long", "guess")])

    def test_approved_as_it_was_filled_the_agent_is_told_it_came_from_the_chat(self):
        fields, url = self.form("width:300", [WHAT, HOW_BIG])
        gate, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": gate["id"], "allow": True,
                                   "answers": [f["text"] for f in fields]})
        said = self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        [result] = [e for e in said if e["kind"] == "result"]
        self.assertEqual([(a["answer"], a["source"]) for a in result["answers"]],
                         [("a handheld megaphone", "guess"), ("300 mm wide", "chat")])


class SetAsideTest(FormCase):

    def test_a_form_set_aside_when_the_run_is_ended_keeps_the_chats_size(self):
        """It waits for the person as it was shown (ADR 0031, decision 3)."""
        def drive(prompt, options, gate, say):
            gate(ASK_TOOL, {"questions": [WHAT, HOW_BIG]})
        run = Run(self.space, drive=drive)
        self.addCleanup(lambda: run.live and run.end())
        run.start("a new model", chat_size="300 mm wide")
        deadline = time.monotonic() + 15
        while run.pending is None:
            self.assertLess(time.monotonic(), deadline, "the form never stopped the run")
            time.sleep(0.01)
        run.end("stopped with contour stop", aside=True)
        [kept] = approvals.shown(self.space)
        self.assertEqual([(f["text"], f["source"]) for f in kept["fields"]],
                         [("a handheld megaphone", "guess"), ("300 mm wide", "chat")])



class PromptTest(unittest.TestCase):

    def test_the_new_space_prompt_no_longer_carries_the_said_sentence(self):
        """The size is in the form now, as the chat's: a sentence in the
        prompt too would be a second way it reached the agent (ADR 0034,
        decision 6)."""
        from console.server import NEW_SPACE, begun
        prompt, refused = begun(["--begin", "new-space", "--said", "width:300"])
        self.assertIsNone(refused)
        self.assertEqual(prompt, NEW_SPACE)
        self.assertNotIn("300 mm", prompt)


if __name__ == "__main__":
    unittest.main()
