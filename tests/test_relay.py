"""A chat fills the form (ADR 0034, decision 5; issue 150).

A Desktop chat reads a waiting form's questions from `status`, never Claude's
suggestions, and fills fields with `answer`, as *from the chat*. It approves
nothing and starts nothing: the user approves on the page, and a field they
edited is theirs.
"""
import json
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_form import ASKED, FormCase    # noqa: E402
from test_found import function    # noqa: E402

from console import approvals    # noqa: E402
from lib import connector, last_run, survey    # noqa: E402
from lib.canvas import PAGE    # noqa: E402

WAIT_S = 15


class StatusTest(FormCase):

    def waiting(self, run):
        """The form's id, once the run waits at it and its record says so."""
        deadline = time.monotonic() + WAIT_S
        while run.pending is None or not last_run.forms(self.space):
            self.assertLess(time.monotonic(), deadline, "the form never stopped the run")
            time.sleep(0.01)
        return run.pending["id"]

    def test_a_watched_form_is_in_status_with_its_questions_and_no_suggestion(self):
        run, _ = self.asking(ASKED)
        at = self.waiting(run)
        said = survey.status(self.space)
        self.assertEqual(said["forms"], [{"id": at, "questions": [
            {"id": "q1", "question": "What is it?"},
            {"id": "q2", "question": "How big is it in real life?"}]}])
        for withheld in ("handheld megaphone", "300 mm", "forearm", "trigger"):
            self.assertNotIn(withheld, json.dumps(said))

    def test_a_form_set_aside_is_in_status_after_its_run_has_ended(self):
        self.asking(ASKED, requester="the nightly agent")
        self.until("finished")
        [kept] = approvals.shown(self.space)
        said = survey.status(self.space)
        self.assertEqual(said["forms"], [{"id": kept["id"], "questions": [
            {"id": "q1", "question": "What is it?"},
            {"id": "q2", "question": "How big is it in real life?"}]}])
        self.assertNotIn("handheld megaphone", json.dumps(said))

    def test_an_answered_form_is_gone_from_status(self):
        self.asking(ASKED, requester="the nightly agent")
        self.until("finished")
        [kept] = approvals.shown(self.space)
        approvals.answer(self.space, kept["id"], True, answers=["a megaphone", "300 mm"])
        self.assertEqual(survey.status(self.space)["forms"], [])


class AnswerTest(FormCase):
    """`answer`, as the connector's tool calls it."""

    waiting = StatusTest.waiting

    def filled(self, run, at, n=1):
        """The `filled` events the page reads for this form, once there are
        `n` of them."""
        deadline = time.monotonic() + WAIT_S
        while True:
            said = [e for e in run.events if e["kind"] == "filled" and e["id"] == at]
            if len(said) >= n:
                return said
            self.assertLess(time.monotonic(), deadline, "the page was never told")
            time.sleep(0.01)

    def test_answer_fills_a_watched_forms_fields_as_the_chats_and_it_still_waits(self):
        run, given = self.asking(ASKED)
        at = self.waiting(run)
        said = connector.answering(self.space, {"form": at, "answers": {"q2": "320 mm long"}})
        self.assertTrue(said["filled"], said)
        self.assertIn("approves", said["said"])
        [event] = self.filled(run, at)
        self.assertEqual([(f["text"], f["source"]) for f in event["fields"]],
                         [("a handheld megaphone", "guess"), ("320 mm long", "chat")])
        self.assertEqual(run.pending["id"], at, "an answer approves nothing")
        self.assertEqual(given, [])
        run.answer(at, True, answers=["a handheld megaphone", "320 mm long"])
        allow, answers = self.answered(given)
        self.assertEqual([a["source"] for a in answers], ["guess", "chat"])

    def test_answer_fills_a_form_set_aside_and_approving_it_says_the_chats(self):
        self.asking(ASKED, requester="the nightly agent")
        self.until("finished")
        [kept] = approvals.shown(self.space)
        connector.answering(self.space, {"form": kept["id"], "answers": {"q2": "320 mm long"}})
        [kept] = approvals.shown(self.space)
        self.assertEqual([(f["text"], f["source"]) for f in kept["fields"]],
                         [("a handheld megaphone", "guess"), ("320 mm long", "chat")])
        done = approvals.answer(self.space, kept["id"], True,
                                answers=["a handheld megaphone", "320 mm long"])
        self.assertIn("320 mm long (from the chat)", done["prompt"])

    def test_a_later_relay_replaces_an_earlier_and_one_equal_to_the_guess_is_the_guess(self):
        self.asking(ASKED, requester="the nightly agent")
        self.until("finished")
        [kept] = approvals.shown(self.space)
        for said in ({"q1": "a loudhailer", "q2": "320 mm long"},
                     {"q1": "a bullhorn", "q2": "300 mm long"}):
            connector.answering(self.space, {"form": kept["id"], "answers": said})
        [kept] = approvals.shown(self.space)
        self.assertEqual([(f["text"], f["source"]) for f in kept["fields"]],
                         [("a bullhorn", "chat"), ("300 mm long", "guess")])

    def test_answer_on_an_approved_or_missing_form_is_refused_and_nothing_changes(self):
        self.asking(ASKED, requester="the nightly agent")
        self.until("finished")
        [kept] = approvals.shown(self.space)
        approvals.answer(self.space, kept["id"], True, answers=["a megaphone", "300 mm"])
        relayed = self.space / ".contour" / "relayed.json"
        for at in (kept["id"], "a99", None):
            with self.subTest(form=at):
                said = connector.answering(self.space, {"form": at, "answers": {"q1": "a bell"}})
                self.assertFalse(said["filled"])
                self.assertIn("no form", said["said"])
                self.assertIn("approved, or never asked", said["said"])
                self.assertFalse(relayed.exists())

    def test_an_id_that_is_not_one_of_its_questions_is_refused(self):
        self.asking(ASKED, requester="the nightly agent")
        self.until("finished")
        [kept] = approvals.shown(self.space)
        said = connector.answering(self.space, {"form": kept["id"], "answers": {"q3": "x"}})
        self.assertFalse(said["filled"])
        self.assertIn("q3 is not one of its questions: q1, q2", said["said"])
        [kept] = approvals.shown(self.space)
        self.assertEqual([f["source"] for f in kept["fields"]], ["guess", "guess"])


class ToolTest(unittest.TestCase):
    """`answer` as Desktop is given it."""

    def test_answer_is_the_connectors_eleventh_tool_and_says_the_user_approves(self):
        names = [t["name"] for t in connector.TOOLS]
        self.assertEqual(len(names), 11)
        [tool] = [t for t in connector.TOOLS if t["name"] == "answer"]
        self.assertIn("the user approves on the page", tool["description"])
        self.assertIn("never say", tool["description"])
        self.assertEqual(set(tool["inputSchema"]["required"]), {"space", "form", "answers"})

    def test_answer_says_a_field_is_the_users_words_and_nothing_of_the_chats(self):
        """On Desktop a chat told *it is 280 mm long* filled the size field with
        that, a diameter of its own and a note saying the user gave only the
        length: approved, its guess would have read as the chat's."""
        [tool] = [t for t in connector.TOOLS if t["name"] == "answer"]
        said = tool["description"]
        for rule in ("only what the user said, in their words", "no notes, no sources",
                     "no value they did not say", "answered in part gets that part",
                     "left out, and Claude's guess stays"):
            self.assertIn(rule, said)
        self.assertIn("no guess, note or source of yours goes into a field",
                      connector.INSTRUCTIONS)

    def test_the_instructions_say_a_chat_relays_and_never_invents(self):
        said = connector.INSTRUCTIONS
        self.assertIn("relay its questions", said)
        self.assertIn("only what the user told you", said)
        self.assertIn("never one of your own", said)

    def test_the_launcher_serves_answer(self):
        """Every tool defined is served (`test_connector`), so `answer` is
        handed to `serve` with the rest."""
        self.assertIn("answer", connector.relaying())


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class PageTest(unittest.TestCase):
    """What a field on the page does when a chat fills it: a function of its
    script, run under node as the browser gets it."""

    def refill(self, shown, value, field):
        page = PAGE.read_text(encoding="utf-8")
        js = (function(page, "refill") + f"\nconsole.log(JSON.stringify(refill("
              f"{json.dumps(shown)}, {json.dumps(value)}, {json.dumps(field)})));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_a_field_still_as_it_was_filled_takes_the_chats_text(self):
        guess = {"text": "a megaphone", "source": "guess"}
        chat = {"text": "a loudhailer", "source": "chat"}
        self.assertEqual(self.refill(guess, "a megaphone", chat),
                         {"shown": chat, "value": "a loudhailer"})
        later = {"text": "a bullhorn", "source": "chat"}
        self.assertEqual(self.refill(chat, "a loudhailer", later),
                         {"shown": later, "value": "a bullhorn"})

    def test_a_field_the_user_edited_is_never_overwritten(self):
        guess = {"text": "a megaphone", "source": "guess"}
        chat = {"text": "a loudhailer", "source": "chat"}
        self.assertEqual(self.refill(guess, "a siren", chat),
                         {"shown": guess, "value": "a siren"})

    def test_the_page_fills_a_watched_form_and_one_set_aside(self):
        page = PAGE.read_text(encoding="utf-8")
        self.assertIn("event.kind === 'filled'", function(page, "turn"))
        self.assertIn("refill?.(a.fields)", function(page, "refreshApprovals"))


if __name__ == "__main__":
    unittest.main()
