"""Approvals answered on the page, later (ADR 0028, decision 3; issue 97).

What an unattended run set aside waits in the space, and any console opened on
it shows the approvals, oldest first, each with what its gate would have shown.
Allow applies the call then, as it was written; deny is a veto; one that no
longer applies is dropped and is no veto, because nobody considered it.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_console import STAND_IN, ConsoleCase    # noqa: E402

from console.run import Run    # noqa: E402
from lib import last_run    # noqa: E402

SPEC_WRITE = ("Edit", {"file_path": "spec.yaml", "old_string": "revision: 1\ndepth: 600",
                       "new_string": "revision: 2\ndepth: 640"})
SAVE = ("Bash", {"command": "git add -A && git commit -q -m 'a longer beak'"})
ASKED = ("AskUserQuestion", {"questions": [{"question": "How long should the beak be?",
                                            "options": [{"label": "300 mm"},
                                                        {"label": "340 mm"}]}]})
WAIT_S = 15


def git(space, *args):
    return subprocess.run(["git", "-C", str(space), *args], capture_output=True,
                          text=True, check=True).stdout


class AnsweredCase(ConsoleCase):

    def setUp(self):
        # A directory of its own, named as a space is: where `spaces` looks
        # for it, there is nothing else to walk.
        self.beaky = Path(tempfile.mkdtemp()) / "beaky"
        shutil.move(str(self.space()), str(self.beaky))
        (self.beaky / ".gitignore").write_text(".contour/*\n!.contour/project\nsheet.png\n")
        (self.beaky / "spec.yaml").write_text("revision: 1\ndepth: 600\n")
        git(self.beaky, "init", "-q")
        git(self.beaky, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
        git(self.beaky, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "first")
        self.home = tempfile.mkdtemp()
        patched = mock.patch.dict(os.environ, {
            "CONTOUR_HOME": self.home, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
        patched.start()
        self.addCleanup(patched.stop)

    def set_aside(self, *calls, case="Span m4 reads 640 mm, so the depth is 640."):
        """An unattended run that made `calls` and finished, each set aside."""
        def drive(prompt, options, gate, say):
            say("text", text=case)
            for tool, call in calls:
                gate(tool, dict(call))
            say("text", text="Two things wait for you.")
        run = Run(self.beaky, drive=drive)
        run.start("make the beak longer", ceiling=10**6, requester="the nightly agent")
        deadline = time.monotonic() + WAIT_S
        while (last_run.read(self.beaky) or {}).get("state") != "finished":
            self.assertLess(time.monotonic(), deadline, last_run.read(self.beaky))
            time.sleep(0.02)

    def opened(self):
        """A console opened on the space after the run has ended."""
        _, url = self.launch(self.beaky, CONTOUR_HOME=self.home,
                             CONTOUR_CONSOLE_AGENT=f"{STAND_IN}:drive",
                             CONTOUR_AGENT_SCRIPT=json.dumps([{"say": "done"}]))
        return url

    def waiting(self, url):
        return self.ask(url, "/approvals")[1]["approvals"]

    def answer(self, url, allow=True, reason=None, at=None, answers=None):
        at = at or self.waiting(url)[0]["id"]
        return self.ask(url, "/approval", {"id": at, "allow": allow, "reason": reason,
                                           **({"answers": answers} if answers else {})})[1]

    def until(self, state):
        deadline = time.monotonic() + WAIT_S
        while (last_run.read(self.beaky) or {}).get("state") != state:
            self.assertLess(time.monotonic(), deadline, last_run.read(self.beaky))
            time.sleep(0.05)
        return last_run.read(self.beaky)


class ShownTest(AnsweredCase):

    def test_a_console_opened_later_shows_them_oldest_first(self):
        self.set_aside(SPEC_WRITE, SAVE)
        shown = self.waiting(self.opened())
        self.assertEqual([a["act"] for a in shown],
                         ["Claude wants to change the spec", "Save this version?"])
        self.assertEqual(shown[0]["changes"], ["depth 600 → 640"])
        self.assertEqual(shown[0]["case"], "Span m4 reads 640 mm, so the depth is 640.")
        self.assertEqual([a["next"] for a in shown], [True, False])


    def test_a_save_shows_what_it_would_save_as_the_tree_now_stands(self):
        """Read when shown, not when set aside: what is saved is the tree the
        person answers on, after the spec write ahead of it has gone in."""
        self.set_aside(SPEC_WRITE, SAVE)
        url = self.opened()
        self.assertEqual(self.waiting(url)[1]["changes"], [])
        self.answer(url)
        self.assertEqual(self.waiting(url)[0]["changes"], ["M spec.yaml"])

    def test_a_save_whose_message_names_the_spec_is_shown_as_a_save(self):
        """Issue 103, as issue 100's tracer bullet met it."""
        (self.beaky / "spec.yaml").write_text("revision: 2\ndepth: 640\n")
        self.set_aside(("Bash", {"command": "git add spec.yaml && git commit -q -F - <<'EOF'\n"
                                            "spec.yaml: depth 600 -> 640\nEOF"}))
        [shown] = self.waiting(self.opened())
        self.assertEqual((shown["category"], shown["act"]), ("commit", "Save this version?"))
        self.assertEqual(shown["changes"], ["M spec.yaml"])

    def test_no_new_run_starts_until_they_are_answered(self):
        self.set_aside(SPEC_WRITE)
        url = self.opened()
        said = self.ask(url, "/run", {"prompt": "paint it blue"})[1]
        self.assertFalse(said["started"])
        self.assertIn("approval", said["why"])
        self.answer(url, allow=False, reason="not yet")
        self.assertTrue(self.ask(url, "/run", {"prompt": "paint it blue"})[1]["started"])


class AllowTest(AnsweredCase):

    def test_allowing_a_spec_write_applies_the_edit_as_written(self):
        self.set_aside(SPEC_WRITE)
        url = self.opened()
        self.assertEqual(self.answer(url)["outcome"], "applied")
        self.assertEqual((self.beaky / "spec.yaml").read_text(), "revision: 2\ndepth: 640\n")
        self.assertEqual(self.waiting(url), [])

    def test_a_write_missing_its_revision_bump_never_reaches_the_page(self):
        """It used to, and `contour check` refused it after the person had
        allowed it. Now the gate refuses it, and the agent is told to make the
        whole change as one write (issue 104)."""
        self.set_aside(("Edit", {"file_path": "spec.yaml", "old_string": "depth: 600",
                                 "new_string": "depth: 640"}))
        self.assertEqual(self.waiting(self.opened()), [])
        self.assertEqual((self.beaky / "spec.yaml").read_text(), "revision: 1\ndepth: 600\n")

    def test_allowing_a_save_after_the_spec_write_saves_it(self):
        self.set_aside(SPEC_WRITE, SAVE)
        url = self.opened()
        self.answer(url)
        self.assertEqual(self.answer(url)["outcome"], "applied")
        self.assertEqual(git(self.beaky, "log", "-1", "--format=%s").strip(), "a longer beak")
        self.assertEqual(git(self.beaky, "show", "HEAD:spec.yaml"), "revision: 2\ndepth: 640\n")


class OrderTest(AnsweredCase):

    def test_a_save_cannot_be_answered_before_the_spec_write_ahead_of_it(self):
        self.set_aside(SPEC_WRITE, SAVE)
        url = self.opened()
        later = self.waiting(url)[1]["id"]
        said = self.answer(url, at=later)
        self.assertFalse(said["answered"])
        self.assertEqual(git(self.beaky, "log", "-1", "--format=%s").strip(), "first")
        self.assertEqual(len(self.waiting(url)), 2)



class DenyTest(AnsweredCase):

    def test_denying_records_a_veto_with_the_call_the_reason_and_the_build(self):
        from console import vetoes
        self.set_aside(SPEC_WRITE)
        url = self.opened()
        self.assertEqual(self.answer(url, allow=False, reason="not the depth")["outcome"],
                         "vetoed")
        [veto] = vetoes.load(self.beaky)
        self.assertEqual((veto["tool"], veto["call"]), SPEC_WRITE)
        self.assertEqual(veto["reason"], "not the depth")
        self.assertIn("build", veto)
        self.assertEqual((self.beaky / "spec.yaml").read_text(), "revision: 1\ndepth: 600\n")
        self.assertEqual(self.waiting(url), [])


class StaleTest(AnsweredCase):
    """Nobody considered what it would do now, so it is dropped, not refused."""

    def test_an_edit_whose_old_text_is_gone_is_dropped_and_is_no_veto(self):
        from console import vetoes
        self.set_aside(SPEC_WRITE)
        (self.beaky / "spec.yaml").write_text("revision: 1\ndepth: 620\n")
        url = self.opened()
        said = self.answer(url)
        self.assertEqual(said["outcome"], "no longer applies")
        self.assertEqual((self.beaky / "spec.yaml").read_text(), "revision: 1\ndepth: 620\n")
        self.assertEqual(vetoes.load(self.beaky), [])
        self.assertEqual(self.waiting(url), [])

    def test_a_save_with_nothing_left_to_save_is_dropped(self):
        self.set_aside(SAVE)
        said = self.answer(self.opened())
        self.assertEqual(said["outcome"], "no longer applies")
        self.assertEqual(git(self.beaky, "log", "-1", "--format=%s").strip(), "first")


class GuardTest(AnsweredCase):

    def test_a_tracked_reference_is_refused_as_the_hook_refuses_it_live(self):
        (self.beaky / "refs").mkdir()
        (self.beaky / "refs" / "side.png").write_bytes(b"the user's")
        git(self.beaky, "add", "-A")
        git(self.beaky, "commit", "-q", "-m", "a reference")
        self.set_aside(("Write", {"file_path": "refs/side.png", "content": "x"}))
        said = self.answer(self.opened())
        self.assertEqual(said["outcome"], "refused")
        self.assertEqual((self.beaky / "refs" / "side.png").read_bytes(), b"the user's")



class QuestionTest(AnsweredCase):
    """A question set aside is answered in its place in the order, and the
    answer starts a run of its own: nothing resumes (ADR 0028, decision 2)."""

    def test_it_is_shown_in_its_place_with_its_question(self):
        self.set_aside(SPEC_WRITE, ASKED)
        shown = self.waiting(self.opened())
        self.assertEqual([a["category"] for a in shown], ["spec-write", "question"])
        self.assertEqual(shown[1]["questions"], ASKED[1]["questions"])

    def test_answering_it_starts_an_attended_run_with_the_question_and_the_answer(self):
        self.set_aside(ASKED)
        url = self.opened()
        said = self.answer(url, answers={"How long should the beak be?": "340 mm"})
        self.assertEqual(said["outcome"], "answered")
        record = self.until("finished")
        self.assertIn("How long should the beak be?", record["prompt"])
        self.assertIn("340 mm", record["prompt"])
        self.assertIsNone(record["requester"])
        self.assertEqual(self.waiting(url), [])


class PageTest(unittest.TestCase):
    """The page's source, structural as the other page tests are: there is no
    browser here."""

    def setUp(self):
        self.page = (Path(__file__).resolve().parent.parent / "lib" / "canvas.html").read_text()
        self.script = self.page.split("function approval(")[1].split("\n}\n")[0]

    def test_shown_in_a_section_of_their_own_under_the_run(self):
        run = self.page.split('<section id="run"')[1].split("</section>")[0]
        self.assertIn('<ol id="approvals">', run)

    def test_answered_by_their_own_route_and_never_as_a_live_gate(self):
        self.assertIn("ask('/approval', ", self.script)
        self.assertNotIn("/verdict", self.script)

    def test_only_the_next_can_be_answered(self):
        self.assertIn("if (!a.next)", self.script)


if __name__ == "__main__":
    unittest.main()
