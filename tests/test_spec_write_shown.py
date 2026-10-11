"""A spec write shows its diff and its case (ADR 0028, decision 1; issue 101).

What is refused before it can wait, and why: part of a change, or a case that
does not name what it sets. One with no case says so on the page, rather than
nothing. How it is made at all is `test_spec_tool`'s (ADR 0029).
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import one_run    # noqa: E402,F401  one suite run per machine (issue 94)
from test_approvals_answered import WAIT_S, AnsweredCase    # noqa: E402

from console import approvals    # noqa: E402
from console.run import SPEC_TOOL, Run    # noqa: E402
from lib import last_run    # noqa: E402

BY_SHELL = ("Bash", {"command": "python3 - <<'EOF'\nfrom pathlib import Path\n"
                                "p = Path('spec.yaml')\n"
                                "p.write_text(p.read_text().replace('600', '640'))\nEOF"})


class MadeCase(AnsweredCase):

    def made(self, call, requester):
        """What the gate said to `call`, in a run with or without a requester."""
        said = []

        def drive(prompt, options, gate, say):
            text = getattr(self, "said", "Span m4 reads 640 mm, so the depth is 640.")
            if text:
                say("text", text=text)
            said.append(gate(*call))
        run = Run(self.beaky, drive=drive)
        self.addCleanup(lambda: run.live and run.end())
        run.start("make the beak longer", ceiling=10**6, requester=requester)
        deadline = time.monotonic() + WAIT_S
        while not said or run.live:
            self.assertLess(time.monotonic(), deadline, "the gate never answered")
            time.sleep(0.02)
        return said[0], run

def written(content, case="Span m4 reads 640 mm, so the depth is 640."):
    """A spec write as the console takes one: the whole spec, and its case
    (ADR 0029)."""
    return (SPEC_TOOL, {"content": content, "case": case})


REVISION_ONLY = written("revision: 2\ndepth: 600\n")
FIELD_ONLY = written("revision: 1\ndepth: 640\n")
WHOLE = "revision: 2\ndepth: 640\n"


class RefusedTest(MadeCase):

    def test_a_spec_write_of_part_of_the_change_is_refused(self):
        """The revision alone, or a field without it: rule 1 bumps it in the
        same write, and a page could show nothing of the first and a check
        would go red on the second (issue 104)."""
        for call in (REVISION_ONLY, FIELD_ONLY):
            for requester in ("the nightly agent", None):
                with self.subTest(content=call[1]["content"], requester=requester):
                    (allow, why), run = self.made(call, requester)
                    self.assertFalse(allow)
                    self.assertIn("the whole change, revision bump included", why)
                    self.assertIn("made with spec_write", why)
                    self.assertIn("the span if you measured one", why)
                    self.assertEqual(approvals.load(self.beaky), [])
                    self.assertIn(why, [e.get("text") for e in run.events
                                        if e["kind"] == "refused"])
                    self.assertEqual((self.beaky / "spec.yaml").read_text(),
                                     "revision: 1\ndepth: 600\n")


class UnarguedTest(MadeCase):
    """The case names the numbers the write sets, or it is not one: narration
    before a spec write was shown as its case (issue 106)."""

    def test_a_case_that_is_narration_is_refused_naming_what_to_say(self):
        for requester in ("the nightly agent", None):
            with self.subTest(requester=requester):
                (allow, why), run = self.made(
                    written(WHOLE, "While that waits, I'll read the last recorded "
                                   "check result."), requester)
                self.assertFalse(allow)
                self.assertIn("your case names what it sets: 640", why)
                self.assertIn("in its case", why)
                self.assertEqual(approvals.load(self.beaky), [])

    def test_a_number_inside_another_does_not_count(self):
        (allow, why), _ = self.made(
            written(WHOLE, "The tip moves to y = -6400, so depth goes up."),
            "the nightly agent")
        self.assertIn("names what it sets: 640", why)

    def test_what_was_said_before_it_is_not_its_case(self):
        """Said, not carried: three runs left theirs in their thinking, and one
        in a reply is no surer to be there (ADR 0029)."""
        self.said = "You asked for a longer beak, which makes depth 640 mm."
        (allow, why), _ = self.made(written(WHOLE, ""), "the nightly agent")
        self.assertIn("names what it sets: 640", why)


class ClosingTest(MadeCase):
    """What a set-aside call tells the agent to say of it in its closing: that
    it waits, and not why, since the case is on the page with it (issue 102)."""

    def test_the_closing_names_what_waits_and_does_not_argue_it(self):
        (_, why), _ = self.made(written(WHOLE), "the nightly agent")
        self.assertIn("say in your closing what waits on it, and not why", why)
        self.assertIn("its case is on the page with it", why)


class NoCaseTest(AnsweredCase):

    def test_a_spec_write_with_no_case_says_so(self):
        """One that sets no number, since one that does is refused without it
        (issue 106): here, depth taken out."""
        self.set_aside(written("revision: 2\n", case=""), case="")
        [shown] = self.waiting(self.opened())
        self.assertEqual(shown["case"], "Claude gave no case for this.")

    def test_a_save_with_nothing_before_it_is_not_said_to_lack_one(self):
        self.set_aside(("Bash", {"command": "git commit -qam 'a longer beak'"}), case="")
        [shown] = self.waiting(self.opened())
        self.assertEqual(shown["case"], "")


if __name__ == "__main__":
    unittest.main()
