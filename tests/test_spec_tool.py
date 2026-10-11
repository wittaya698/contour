"""Under a console a spec write carries its case (ADR 0029; issue 109).

Three real runs argued their spec change only in their thinking, which the gate
does not see and the person is not shown, and two wordings of a refusal did not
change that (issues 107 and 108). So the case is an argument of the write: the
console's `spec_write` takes the whole new spec and the case for it together.
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import one_run    # noqa: E402,F401  one suite run per machine (issue 94)
from test_approvals_answered import WAIT_S    # noqa: E402
from test_spec_write_shown import BY_SHELL, MadeCase    # noqa: E402

from console import approvals    # noqa: E402
from console import run as console_run    # noqa: E402
from console.run import SPEC_TOOL    # noqa: E402

CASE = "You asked for a longer beak, which makes depth 640 mm, past 600 ±20."

WRITTEN = (SPEC_TOOL, {"content": "revision: 2\ndepth: 640\n", "case": CASE})


class CarriedTest(MadeCase):

    def test_its_case_is_the_one_it_carries_whatever_was_said_before(self):
        self.said = ""
        (allow, why), _ = self.made(WRITTEN, "the nightly agent")
        self.assertFalse(allow)
        self.assertIn("set aside", why)
        [kept] = approvals.load(self.beaky)
        self.assertEqual(kept["case"], CASE)
        self.assertEqual(kept["said"]["changes"], ["depth 600 → 640"])


class OtherwiseTest(MadeCase):

    def test_a_spec_write_made_any_other_way_is_told_to_carry_its_case(self):
        """Watched or not: a case said before the call is the one three runs
        never wrote down."""
        edit = ("Edit", {"file_path": "spec.yaml", "old_string": "revision: 1\ndepth: 600",
                         "new_string": "revision: 2\ndepth: 640"})
        whole = ("Write", {"file_path": "spec.yaml", "content": "revision: 2\ndepth: 640\n"})
        for call in (edit, whole, BY_SHELL):
            for requester in ("the nightly agent", None):
                with self.subTest(tool=call[0], requester=requester):
                    (allow, why), run = self.made(call, requester)
                    self.assertFalse(allow)
                    self.assertIn("made with spec_write", why)
                    self.assertIn("your case for it as its case", why)
                    self.assertEqual(approvals.load(self.beaky), [])
                    self.assertEqual((self.beaky / "spec.yaml").read_text(),
                                     "revision: 1\ndepth: 600\n")


class ToolTest(MadeCase):
    """The tool as the agent is given it, and what it does once allowed."""

    def test_it_says_the_case_is_what_the_person_reads(self):
        said = console_run.SPEC_WRITER["description"]
        self.assertIn("whole new spec.yaml", said)
        self.assertIn("the only place the person reads your case", said)
        self.assertEqual(set(console_run.SPEC_WRITER["schema"]["required"]),
                         {"content", "case"})
        self.assertEqual(SPEC_TOOL, f"mcp__contour__{console_run.SPEC_WRITER['name']}")

    def test_watched_its_case_is_said_just_before_its_gate(self):
        """Where the person watching reads a case: Claude's words, just before
        the gate (rule 1)."""
        said = []

        def drive(prompt, options, gate, say):
            said.append(gate(*WRITTEN))
        from console.run import Run
        run = Run(self.beaky, drive=drive)
        self.addCleanup(lambda: run.live and run.end())
        run.start("make the beak longer", ceiling=10**6)
        deadline = time.monotonic() + WAIT_S
        while run.pending is None:
            self.assertLess(time.monotonic(), deadline, "the gate never stopped")
            time.sleep(0.02)
        kinds = [(e["kind"], e.get("text")) for e in run.events]
        self.assertEqual(kinds[-2:], [("text", CASE), ("gate", None)])

    def test_allowed_it_writes_the_spec(self):
        said = console_run.spec_written(self.beaky, WRITTEN[1])
        self.assertEqual((self.beaky / "spec.yaml").read_text(), "revision: 2\ndepth: 640\n")
        self.assertIn("spec.yaml", said)


if __name__ == "__main__":
    unittest.main()
