"""A spec write shows its diff and its case (ADR 0028, decision 1; issue 101).

A spec write made by a script cannot be read before it runs, so it is refused,
watched or not, and the agent is told to make it as an `Edit`. One with no case
before it says so on the page, rather than nothing.
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import one_run    # noqa: E402,F401  one suite run per machine (issue 94)
from test_approvals_answered import SPEC_WRITE, WAIT_S, AnsweredCase    # noqa: E402

from console import approvals    # noqa: E402
from console.run import Run    # noqa: E402
from lib import last_run    # noqa: E402

BY_SHELL = ("Bash", {"command": "python3 - <<'EOF'\nfrom pathlib import Path\n"
                                "p = Path('spec.yaml')\n"
                                "p.write_text(p.read_text().replace('600', '640'))\nEOF"})


class MadeCase(AnsweredCase):

    def made(self, call, requester):
        """What the gate said to `call`, in a run with or without a requester."""
        said = []

        def drive(prompt, options, gate, say):
            say("text", text=getattr(self, "said", "Span m4 reads 640 mm, so the depth is 640."))
            said.append(gate(*call))
        run = Run(self.beaky, drive=drive)
        self.addCleanup(lambda: run.live and run.end())
        run.start("make the beak longer", ceiling=10**6, requester=requester)
        deadline = time.monotonic() + WAIT_S
        while not said or run.live:
            self.assertLess(time.monotonic(), deadline, "the gate never answered")
            time.sleep(0.02)
        return said[0], run

REVISION_ONLY = ("Edit", {"file_path": "spec.yaml", "old_string": "revision: 1",
                          "new_string": "revision: 2"})
FIELD_ONLY = ("Edit", {"file_path": "spec.yaml", "old_string": "depth: 600",
                       "new_string": "depth: 640"})


class RefusedTest(MadeCase):

    def test_a_spec_write_by_shell_is_refused_and_told_to_be_an_edit(self):
        for requester in ("the nightly agent", None):
            with self.subTest(requester=requester):
                (allow, why), run = self.made(BY_SHELL, requester)
                self.assertFalse(allow)
                self.assertIn("as an Edit of spec.yaml", why)
                self.assertIn("just before it", why)
                self.assertEqual(approvals.load(self.beaky), [])
                self.assertIn(why, [e.get("text") for e in run.events
                                    if e["kind"] == "refused"])
                self.assertEqual((self.beaky / "spec.yaml").read_text(),
                                 "revision: 1\ndepth: 600\n")

    def test_a_spec_write_as_an_edit_is_still_set_aside(self):
        (allow, why), _ = self.made(SPEC_WRITE, "the nightly agent")
        self.assertFalse(allow)
        self.assertIn("set aside", why)
        [kept] = approvals.load(self.beaky)
        self.assertEqual(kept["said"]["changes"], ["depth 600 → 640"])

    def test_a_spec_write_of_part_of_the_change_is_refused(self):
        """The revision alone, or a field without it: rule 1 bumps it in the
        same write, and a page could show nothing of the first and a check
        would go red on the second (issue 104)."""
        for call in (REVISION_ONLY, FIELD_ONLY):
            for requester in ("the nightly agent", None):
                with self.subTest(call=call[1]["new_string"], requester=requester):
                    (allow, why), run = self.made(call, requester)
                    self.assertFalse(allow)
                    self.assertIn("the whole change, revision bump included, as one Edit", why)
                    self.assertIn("just before it", why)
                    self.assertEqual(approvals.load(self.beaky), [])
                    self.assertEqual((self.beaky / "spec.yaml").read_text(),
                                     "revision: 1\ndepth: 600\n")


class UnarguedTest(MadeCase):
    """The case names the numbers the write sets, or it is not one: narration
    before a spec write was shown as its case (issue 106)."""

    def made(self, call, requester, said="Span m4 reads 640 mm, so the depth is 640."):
        self.said = said
        return super().made(call, requester)

    def test_a_spec_write_after_narration_is_refused_naming_what_to_say(self):
        for requester in ("the nightly agent", None):
            with self.subTest(requester=requester):
                (allow, why), run = self.made(
                    SPEC_WRITE, requester,
                    said="While that waits, I'll read the last recorded check result.")
                self.assertFalse(allow)
                self.assertIn("your case just before it names what it sets: 640", why)
                self.assertEqual(approvals.load(self.beaky), [])
                self.assertIn(why, [e.get("text") for e in run.events
                                    if e["kind"] == "refused"])

    def test_a_number_inside_another_does_not_count(self):
        (allow, why), _ = self.made(SPEC_WRITE, "the nightly agent",
                                    said="The tip moves to y = -6400, so depth goes up.")
        self.assertIn("names what it sets: 640", why)

    def test_a_case_naming_the_number_is_set_aside_with_it(self):
        (allow, why), _ = self.made(SPEC_WRITE, "the nightly agent",
                                    said="You asked for a longer beak, which makes depth "
                                         "640 mm, past 600 ±20.")
        self.assertIn("set aside", why)
        [kept] = approvals.load(self.beaky)
        self.assertEqual(kept["case"], "You asked for a longer beak, which makes depth "
                                       "640 mm, past 600 ±20.")


class ClosingTest(MadeCase):
    """What a set-aside call tells the agent to say of it in its closing: that
    it waits, and not why, since the case is on the page with it (issue 102)."""

    def test_the_closing_names_what_waits_and_does_not_argue_it(self):
        (_, why), _ = self.made(SPEC_WRITE, "the nightly agent")
        self.assertIn("say in your closing what waits on it, and not why", why)
        self.assertIn("its case is on the page with it", why)


class NoCaseTest(AnsweredCase):

    def test_a_spec_write_with_no_case_says_so(self):
        """One that sets no number, since one that does is refused without it
        (issue 106): here, depth taken out."""
        self.set_aside(("Edit", {"file_path": "spec.yaml",
                                 "old_string": "revision: 1\ndepth: 600",
                                 "new_string": "revision: 2"}), case="")
        [shown] = self.waiting(self.opened())
        self.assertEqual(shown["case"], "Claude gave no case for this.")

    def test_a_save_with_nothing_before_it_is_not_said_to_lack_one(self):
        self.set_aside(("Bash", {"command": "git commit -qam 'a longer beak'"}), case="")
        [shown] = self.waiting(self.opened())
        self.assertEqual(shown["case"], "")


if __name__ == "__main__":
    unittest.main()
