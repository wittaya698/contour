"""A space carries the topics its user approved (ADR 0030; issue 114).

A topic is a free word a model is labelled with so it can be found. The agent
proposes, the person approves word by word, and a word they strike is
remembered against the model and never proposed for it again.
"""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import one_run    # noqa: E402,F401  one suite run per machine (issue 94)
from test_approvals_answered import WAIT_S, AnsweredCase    # noqa: E402

from console import approvals    # noqa: E402
from console import run as console_run    # noqa: E402
from console.run import TOPICS_TOOL, Run    # noqa: E402
from lib import cli, topics, vetoes    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

CASE = "A bird with a beak and two legs: a creature, a bird, fauna."

PROPOSED = (TOPICS_TOOL, {"words": ["creature", "bird", "fauna"], "case": CASE})


class WatchedTest(AnsweredCase):

    def proposed(self, call=PROPOSED):
        """A watched run whose agent makes `call`, stopped at its gate.
        Returns the run, and the list the gate's answer lands in."""
        said = []

        def drive(prompt, options, gate, say):
            said.append(gate(*call))
        run = Run(self.beaky, drive=drive)
        self.addCleanup(lambda: run.live and run.end())
        run.start("suggest topics", ceiling=10**6)
        deadline = time.monotonic() + WAIT_S
        while run.pending is None and not said:
            self.assertLess(time.monotonic(), deadline, "the gate never stopped")
            time.sleep(0.02)
        return run, said

    def settled(self, run, said):
        deadline = time.monotonic() + WAIT_S
        while not said or run.live:
            self.assertLess(time.monotonic(), deadline, "the run never finished")
            time.sleep(0.02)
        return said[0]

    def test_the_words_kept_are_its_topics_and_the_rest_are_struck(self):
        run, said = self.proposed()
        run.answer(run.pending["id"], True, kept=["creature", "bird"])
        allow, told = self.settled(run, said)
        self.assertTrue(allow)
        self.assertEqual(told, {"kept": ["creature", "bird"], "struck": ["fauna"],
                                "struck_before": []})
        self.assertEqual(topics.load(self.beaky),
                         {"topics": ["creature", "bird"], "struck": ["fauna"]})
        self.assertEqual((self.beaky / "spec.yaml").read_text(), "revision: 1\ndepth: 600\n")

    def test_a_word_struck_before_is_not_offered_again_and_the_agent_hears_why(self):
        topics.answered(self.beaky, ["fauna"], [])
        run, said = self.proposed()
        self.assertEqual(run.pending["call"]["words"], ["creature", "bird"])
        run.answer(run.pending["id"], True, kept=["creature"])
        _, told = self.settled(run, said)
        self.assertEqual(told, {"kept": ["creature"], "struck": ["bird"],
                                "struck_before": ["fauna"]})

    def test_none_of_them_strikes_every_word_and_is_no_veto(self):
        """A struck topic refuses a word, not a call (ADR 0030, decision 5)."""
        run, said = self.proposed()
        run.answer(run.pending["id"], False)
        allow, why = self.settled(run, said)
        self.assertFalse(allow)
        self.assertIsInstance(why, str)
        self.assertIn("creature, bird, fauna", why)
        self.assertEqual(topics.load(self.beaky),
                         {"topics": [], "struck": ["creature", "bird", "fauna"]})
        self.assertEqual(vetoes.load(self.beaky), [])
        self.assertEqual(run.latest["vetoes"], [])

    def test_the_answer_only_narrows_the_agents_words_never_adds_to_them(self):
        """What the person keeps is the answer; a word the agent never proposed
        cannot arrive by it, or the agent would be named as proposing it
        (ADR 0019, decision 13). The person adds their own with `contour topics`."""
        run, said = self.proposed()
        run.answer(run.pending["id"], True, kept=["creature", "dragon"])
        _, told = self.settled(run, said)
        self.assertEqual(told["kept"], ["creature"])
        self.assertNotIn("dragon", topics.load(self.beaky)["topics"])

    def test_a_proposal_is_kept_in_the_spelling_a_filter_finds(self):
        run, said = self.proposed((TOPICS_TOOL, {"words": ["Creature", " low  poly ",
                                                           "creature", ""],
                                                 "case": CASE}))
        self.assertEqual(run.pending["call"]["words"], ["creature", "low poly"])
        run.answer(run.pending["id"], False)
        self.settled(run, said)

    def test_a_proposal_of_only_struck_words_never_stops_the_run(self):
        """Nothing is left to put to the person, so nobody is asked."""
        topics.answered(self.beaky, ["fauna"], [])
        run, said = self.proposed((TOPICS_TOOL, {"words": ["fauna"], "case": CASE}))
        allow, why = self.settled(run, said)
        self.assertFalse(allow)
        self.assertIn("fauna", why)
        self.assertEqual(run.gates, 0)

    def test_the_agent_cannot_label_the_model_by_hand(self):
        """Only by proposing. A reflex Allow on `contour topics add fauna` would
        put back a word the person struck, and keep no word-by-word answer."""
        topics.answered(self.beaky, ["fauna"], [])
        for call in (("Bash", {"command": "contour topics add fauna"}),
                     ("Bash", {"command": "contour topics strike bird"}),
                     ("Write", {"file_path": "topics.json", "content": "{}"}),
                     ("Bash", {"command": "echo '{}' > topics.json"})):
            with self.subTest(call=call):
                run, said = self.proposed(call)
                allow, why = self.settled(run, said)
                self.assertFalse(allow)
                self.assertIn("topics_propose", why)
                self.assertEqual(run.gates, 0)
        self.assertEqual(topics.load(self.beaky), {"topics": [], "struck": ["fauna"]})

    def test_reading_them_is_not_labelling(self):
        for command in ("cat topics.json", "git diff topics.json", "contour topics"):
            with self.subTest(command=command):
                self.assertFalse(topics.by_hand("Bash", {"command": command}))


class UnattendedTest(AnsweredCase):
    """A proposal nobody was watching for waits as an approval like any other
    (ADR 0030, decision 6), and is answered later, on the page."""

    def test_it_waits_holds_the_space_and_is_answered_word_by_word_later(self):
        self.set_aside(PROPOSED)
        [waiting] = approvals.load(self.beaky)
        self.assertEqual(waiting["category"], "topics")
        self.assertEqual(waiting["call"]["words"], ["creature", "bird", "fauna"])
        self.assertEqual(topics.load(self.beaky), {"topics": [], "struck": []})
        with mock.patch.dict(os.environ, {"CONTOUR_SPACES": str(self.beaky.parent)}):
            refused = cli.requested(self.beaky.name, "paint it blue", "the nightly agent")
        self.assertFalse(refused["started"])

        said = approvals.answer(self.beaky, waiting["id"], True,
                                words=["creature", "bird"])
        self.assertEqual(said["outcome"], "applied")
        self.assertEqual(topics.load(self.beaky),
                         {"topics": ["creature", "bird"], "struck": ["fauna"]})
        self.assertEqual(approvals.load(self.beaky), [])
        self.assertEqual((self.beaky / "spec.yaml").read_text(), "revision: 1\ndepth: 600\n")

    def test_later_too_the_answer_only_narrows_the_agents_words(self):
        self.set_aside(PROPOSED)
        [waiting] = approvals.load(self.beaky)
        approvals.answer(self.beaky, waiting["id"], True, words=["bird", "dragon"])
        self.assertEqual(topics.load(self.beaky)["topics"], ["bird"])

    def test_none_of_them_later_strikes_them_all_and_is_no_veto(self):
        self.set_aside(PROPOSED)
        [waiting] = approvals.load(self.beaky)
        said = approvals.answer(self.beaky, waiting["id"], False)
        self.assertEqual(said["outcome"], "struck")
        self.assertEqual(topics.load(self.beaky)["struck"], ["creature", "bird", "fauna"])
        self.assertEqual(vetoes.load(self.beaky), [])

    def test_on_the_page_the_words_ticked_are_the_ones_kept(self):
        """The page answers it as it answers any approval, with the words."""
        self.set_aside(PROPOSED)
        url = self.opened()
        [shown] = self.waiting(url)
        self.assertEqual(shown["category"], "topics")
        self.assertEqual(shown["act"], "Claude suggests words to find this model by")
        self.assertEqual(shown["call"]["words"], ["creature", "bird", "fauna"])
        said = self.ask(url, "/approval", {"id": shown["id"], "allow": True,
                                           "words": ["bird"]})[1]
        self.assertEqual(said["outcome"], "applied")
        self.assertEqual(topics.load(self.beaky),
                         {"topics": ["bird"], "struck": ["creature", "fauna"]})


class PageTest(unittest.TestCase):
    """What the page is handed for a topics gate, and what it sends back."""

    def test_the_gate_names_each_word_for_its_own_toggle(self):
        from lib import gate as gate_words
        said = gate_words.say("topics", Path(tempfile.mkdtemp()), TOPICS_TOOL,
                              PROPOSED[1], CASE)
        self.assertEqual(said["words"], ["creature", "bird", "fauna"])
        self.assertFalse(said["always"])

    def test_the_page_ticks_every_word_and_sends_the_ticked_ones(self):
        page = (ROOT / "lib" / "canvas.html").read_text()
        self.assertIn("for (const w of said.words || [])", page)
        self.assertIn("box.checked = true;", page)
        self.assertIn("words: kept()", page)
        self.assertIn("'struck': 'you kept none of them'", page)


class ByHandTest(unittest.TestCase):
    """The user's own path: `contour topics`, ungated, in their terminal."""

    def setUp(self):
        self.space = Path(tempfile.mkdtemp()) / "beaky"
        (self.space / ".contour").mkdir(parents=True)
        (self.space / ".contour" / "project").write_text("toolkit: stub\n")

    def contour(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "contour"), "topics", *args],
                              cwd=str(self.space), capture_output=True, text=True,
                              timeout=60)

    def test_the_user_adds_and_strikes_a_word_and_lists_them(self):
        topics.answered(self.space, ["fauna"], [])
        self.assertEqual(self.contour("add", "Creature").returncode, 0)
        self.assertEqual(self.contour("add", "fauna").returncode, 0)
        self.assertEqual(self.contour("strike", "creature").returncode, 0)
        self.assertEqual(topics.load(self.space),
                         {"topics": ["fauna"], "struck": ["creature"]})
        listed = self.contour()
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn("fauna", listed.stdout)


class ToolTest(unittest.TestCase):
    """The proposal as the agent is given it, and what it is told back."""

    def test_it_is_the_consoles_own_tool_and_says_what_it_is_for(self):
        said = console_run.TOPICS_PROPOSER["description"]
        self.assertIn("words to find this model by", said)
        self.assertIn("keeps or strikes each word", said)
        self.assertEqual(set(console_run.TOPICS_PROPOSER["schema"]["required"]),
                         {"words", "case"})
        self.assertEqual(TOPICS_TOOL,
                         f"mcp__contour__{console_run.TOPICS_PROPOSER['name']}")

    def test_answered_it_says_what_was_kept_struck_and_held_back(self):
        said = console_run.topics_proposed({"kept": ["creature"], "struck": ["bird"],
                                            "struck_before": ["fauna"]})
        self.assertIn("kept: creature", said)
        self.assertIn("struck: bird", said)
        self.assertIn("fauna", said)

    def test_the_driver_hands_the_answer_back_on_the_call(self):
        python = ROOT / ".venv" / "bin" / "python"
        if not python.exists():
            self.skipTest("no console environment")
        told = {"kept": ["creature"], "struck": ["bird"], "struck_before": []}
        done = subprocess.run([str(python), "-c", (
            "from console import agent\n"
            f"call = {PROPOSED[1]!r}\n"
            f"a = agent.result({TOPICS_TOOL!r}, call, True, {told!r})\n"
            f"print(a.updated_input == {{**call, **{told!r}}})\n"
            "print(sorted(t.name for t in agent.tools('.')))\n")],
            cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(done.stdout.split("\n")[:2],
                         ["True", "['spec_write', 'topics_propose']"], done.stderr)


if __name__ == "__main__":
    unittest.main()
