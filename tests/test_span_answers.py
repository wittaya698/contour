"""The user answers an agent span (ADR 0022, decision 5; issue 42).

An agent span is a question: *is this what you meant?* The user has three
answers, on the canvas — adopt, correct, reject — and the agent has none. These
talk to the running canvas over HTTP, as the page does.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import marks as marks_store
from lib import span
from lib.canvas import Canvas
from client import get, open_url, post
from test_console import ConsoleCase
from budget import slow

QUESTION = {"extent": "across", "of": None, "anchor": 1700.0,
            "tol": 0.05, "bg_tol": 0.10}


class AnswerCase(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.marks = self.tmp / "marks.json"
        self.canvas = Canvas(sheet=self.tmp / "sheet.png", marks=self.marks)
        self.addCleanup(self.canvas.stop)
        self.canvas.start()

    def drawn(self, k=2.0):
        """An agent span, as `contour measure` draws one: 200 px across."""
        span.pinned(self.marks, "front.jpg", QUESTION,
                    ([99.5, 549.5], [299.5, 549.5]), k, "the body, side to side")
        return [m for m in marks_store.load(self.marks)
                if m.get("placed") == "snapped"][-1]["id"]

    def stored(self, mark_id):
        return span.marked(self.marks, mark_id)


class AdoptTest(AnswerCase):

    def test_an_adopted_span_is_the_user_s_and_says_the_agent_drew_it(self):
        mark_id = self.drawn()
        status, said = post(self.canvas, "/adopt", {"id": mark_id})
        self.assertEqual(status, 200)
        self.assertNotIn("refused", said)
        got = self.stored(mark_id)
        self.assertEqual(got["author"], "user")
        self.assertEqual(got["drawn_by"], "agent")
        self.assertEqual(got["answer"], "adopted")
        self.assertEqual(got["status"], "open")
        self.assertEqual((got["pixel"], got["to"]), ([99.5, 549.5], [299.5, 549.5]))


class CorrectTest(AnswerCase):

    def correct(self, mark_id, to=(349.5, 549.5)):
        return post(self.canvas, "/correct",
                    {"id": mark_id, "pixel": [99.5, 549.5], "to": list(to)})

    def test_a_corrected_span_has_the_user_s_ends_and_keeps_the_agent_s(self):
        """It becomes the user's span, placed by the user and no longer
        snapped, and keeps the fact that the agent drew it first."""
        mark_id = self.drawn()
        status, said = self.correct(mark_id)
        self.assertEqual(status, 200)
        self.assertNotIn("refused", said)
        got = self.stored(mark_id)
        self.assertEqual((got["pixel"], got["to"]), ([99.5, 549.5], [349.5, 549.5]))
        self.assertEqual(got["author"], "user")
        self.assertEqual(got["drawn_by"], "agent")
        self.assertEqual(got["answer"], "corrected")
        self.assertEqual(got["agent_ends"], [[99.5, 549.5], [299.5, 549.5]])
        self.assertNotIn("placed", got)
        self.assertFalse(span.asked(self.marks, mark_id)["ok"])

    def test_it_is_measured_again_and_the_old_answer_is_closed(self):
        """A fresh answer in millimetres, at the scale the agent's was read
        at, pinned between the new ends; the old number no longer stands."""
        mark_id = self.drawn()
        old = self.stored(mark_id)["reading"]
        self.correct(mark_id)
        got = self.stored(mark_id)
        fresh = self.stored(got["reading"])
        self.assertNotEqual(got["reading"], old)
        self.assertIn(f"span {mark_id}: 500 mm ±4 mm", fresh["text"])
        self.assertEqual(fresh["pixel"], span.midpoint(got["pixel"], got["to"]))
        self.assertEqual(fresh["status"], "open")
        self.assertEqual(self.stored(old)["status"], "closed")

    def test_with_no_scale_on_file_the_fresh_answer_is_in_pixels(self):
        mark_id = self.drawn(k=None)
        self.correct(mark_id)
        fresh = self.stored(self.stored(mark_id)["reading"])
        self.assertIn("250 px", fresh["text"])
        self.assertNotIn(" mm ", fresh["text"])


class RejectTest(AnswerCase):

    def test_a_rejected_span_is_closed_with_the_reason_and_its_number_unused(self):
        mark_id = self.drawn()
        reading = self.stored(mark_id)["reading"]
        status, said = post(self.canvas, "/reject",
                            {"id": mark_id, "why": "that is the wing, not the body"})
        self.assertEqual(status, 200)
        self.assertNotIn("refused", said)
        got = self.stored(mark_id)
        self.assertEqual(got["status"], "closed")
        self.assertEqual(got["answer"], "rejected")
        self.assertEqual(got["why"], "that is the wing, not the body")
        self.assertTrue(got["unused"])
        self.assertEqual(self.stored(reading)["status"], "closed")
        self.assertTrue(self.stored(reading)["unused"])
        self.assertIsNone(marks_store.status_line(self.marks))

    def test_reject_without_a_reason_is_refused_and_nothing_changes(self):
        mark_id = self.drawn()
        before = marks_store.load(self.marks)
        for body in ({"id": mark_id}, {"id": mark_id, "why": "   "}):
            with self.subTest(body=body):
                _, said = post(self.canvas, "/reject", body)
                self.assertIn("reason", said["refused"])
                self.assertEqual(marks_store.load(self.marks), before)


class OnlyAQuestionTest(AnswerCase):

    def answers(self, mark_id):
        return (("/adopt", {"id": mark_id}),
                ("/correct", {"id": mark_id, "pixel": [1, 1], "to": [9, 1]}),
                ("/reject", {"id": mark_id, "why": "wrong thing"}))

    def test_only_an_open_agent_span_with_no_answer_can_be_answered(self):
        """A user's span is already their intent; an agent's reading is a
        number, not a span; an answered span has had its answer."""
        user = marks_store.append(self.marks, {"ref": "front.jpg", "pixel": [1, 2],
                                               "to": [9, 2], "text": "by hand"})
        drawn = self.drawn()
        reading = self.stored(drawn)["reading"]
        adopted, rejected = self.drawn(), self.drawn()
        post(self.canvas, "/adopt", {"id": adopted})
        post(self.canvas, "/reject", {"id": rejected, "why": "the wing"})
        before = marks_store.load(self.marks)
        for mark_id in (user["id"], reading, adopted, rejected, "m404"):
            for path, body in self.answers(mark_id):
                with self.subTest(mark=mark_id, answer=path):
                    _, said = post(self.canvas, path, body)
                    self.assertIn(mark_id, said["refused"])
        self.assertEqual(marks_store.load(self.marks), before)

    def test_a_correction_needs_two_different_ends(self):
        mark_id = self.drawn()
        before = marks_store.load(self.marks)
        for ends in ({}, {"pixel": [5, 5], "to": [5, 5]}):
            with self.subTest(ends=ends):
                _, said = post(self.canvas, "/correct", {"id": mark_id, **ends})
                self.assertIn("refused", said)
        self.assertEqual(marks_store.load(self.marks), before)



class UnderTheConsoleTest(ConsoleCase):
    """The same canvas, served by the console: the answers come with it."""

    def test_each_answer_can_be_given_under_the_console(self):
        space = self.space()
        found = space / "marks.json"
        ids = []
        for _ in range(3):
            drawn = span.pinned(found, "front.jpg", QUESTION,
                                ([99.5, 549.5], [299.5, 549.5]), 2.0, "the body")
            ids.append(drawn["lines"][0].split()[2])
        _, url = self.launch(space)
        self.ask(url, "/adopt", {"id": ids[0]})
        self.ask(url, "/correct", {"id": ids[1], "pixel": [99.5, 549.5],
                                   "to": [349.5, 549.5]})
        self.ask(url, "/reject", {"id": ids[2], "why": "the wing"})
        self.assertEqual([span.marked(found, i)["answer"] for i in ids],
                         ["adopted", "corrected", "rejected"])


class PageTest(AnswerCase):

    def test_the_page_offers_the_three_answers_and_shows_which_was_given(self):
        """No JS runs here, so this proves the page's half of the contract:
        it posts each answer, and it has a look for each state. What they look
        like is a HITL check."""
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        for path in ("'/adopt'", "'/correct'", "'/reject'"):
            self.assertIn(path, page)
        for state in ("unanswered", "adopted", "corrected", "rejected"):
            self.assertIn(f".{state}", page)


BEFORE = [
    {"id": "m1", "view": "front", "pixel": [412, 208], "text": "beak too low",
     "author": "user", "status": "open"},
    {"id": "m2", "ref": "front.jpg", "pixel": [1, 2], "to": [9, 2],
     "text": "by hand", "author": "user", "status": "closed"},
    {"id": "m3", "ref": "front.jpg", "pixel": [414.5, 749], "to": [574.5, 749],
     "text": "the legs", "placed": "snapped", "question": {"scanline": 250.0},
     "author": "agent", "status": "open"},
    {"id": "m4", "ref": "front.jpg", "pixel": [494, 749],
     "text": "span m3: 320 mm \u00b14 mm", "author": "agent", "status": "open"}]
"""A `marks.json` from before this slice: a span with no scale and no link to
its reading."""


class OlderMarksTest(AnswerCase):

    def setUp(self):
        super().setUp()
        self.marks.write_text(json.dumps(BEFORE))

    def test_they_load_and_are_served_unchanged(self):
        self.assertEqual(marks_store.load(self.marks), BEFORE)
        self.assertEqual(get(self.canvas, "/marks")[1], BEFORE)

    def test_an_older_agent_span_can_still_be_answered(self):
        """With no link to its reading, the reading is left as it was; with
        no scale, the correction is answered in pixels."""
        _, said = post(self.canvas, "/correct", {"id": "m3", "pixel": [400, 749],
                                                 "to": [600, 749]})
        self.assertEqual(said["answer"], "corrected")
        fresh = self.stored(said["reading"])["text"]
        self.assertIn("200 px", fresh)
        self.assertIn("contour measure --span m3", fresh)
        self.assertEqual(self.stored("m4")["status"], "open")


ROOT = Path(__file__).resolve().parent.parent


class NoAgentSpellingTest(AnswerCase):
    """The agent asks; it never answers its own question. As with closing a
    mark, it has no spelling for any of the three."""

    @slow("six launcher runs, one per spelling refused")
    def test_no_agent_command_can_adopt_correct_or_reject(self):
        (self.tmp / ".contour").mkdir()
        (self.tmp / ".contour" / "project").write_text("toolkit: stub\n")
        mark_id = self.drawn()
        before = marks_store.load(self.marks)
        for args in (["mark", "--adopt", mark_id],
                     ["mark", "--correct", mark_id, "--pixel", "1,1"],
                     ["mark", "--reject", mark_id, "wrong"],
                     ["mark", "--answer", "adopted", mark_id],
                     ["measure", "--adopt", mark_id],
                     ["measure", "--reject", mark_id, "wrong"]):
            with self.subTest(args=args):
                subprocess.run([sys.executable, str(ROOT / "contour"), *args],
                               cwd=str(self.tmp), env=dict(os.environ),
                               capture_output=True, text=True, timeout=60)
                self.assertEqual(marks_store.load(self.marks), before)

    def test_the_agent_s_modules_have_nothing_that_answers(self):
        """A guard, as for closing: what notices if a door ever appears."""
        from lib import agent
        for module in (agent, span):
            for word in ("adopt", "correct", "reject", "answer"):
                with self.subTest(module=module.__name__, word=word):
                    self.assertFalse([n for n in dir(module) if word in n.lower()])


if __name__ == "__main__":
    unittest.main()
