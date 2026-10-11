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
            say("text", text="Span m4 reads 640 mm, so the depth is 640.")
            said.append(gate(*call))
        run = Run(self.beaky, drive=drive)
        self.addCleanup(lambda: run.live and run.end())
        run.start("make the beak longer", ceiling=10**6, requester=requester)
        deadline = time.monotonic() + WAIT_S
        while not said or run.live:
            self.assertLess(time.monotonic(), deadline, "the gate never answered")
            time.sleep(0.02)
        return said[0], run


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
        self.assertEqual(len(approvals.load(self.beaky)), 1)


class ClosingTest(MadeCase):
    """What a set-aside call tells the agent to say of it in its closing: that
    it waits, and not why, since the case is on the page with it (issue 102)."""

    def test_the_closing_names_what_waits_and_does_not_argue_it(self):
        (_, why), _ = self.made(SPEC_WRITE, "the nightly agent")
        self.assertIn("say in your closing what waits on it, and not why", why)
        self.assertIn("its case is on the page with it", why)


class NoCaseTest(AnsweredCase):

    def test_a_spec_write_with_no_case_says_so(self):
        self.set_aside(SPEC_WRITE, case="")
        [shown] = self.waiting(self.opened())
        self.assertEqual(shown["case"], "Claude gave no case for this.")

    def test_a_save_with_nothing_before_it_is_not_said_to_lack_one(self):
        self.set_aside(("Bash", {"command": "git commit -qam 'a longer beak'"}), case="")
        [shown] = self.waiting(self.opened())
        self.assertEqual(shown["case"], "")


if __name__ == "__main__":
    unittest.main()
