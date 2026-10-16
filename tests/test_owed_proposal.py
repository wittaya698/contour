"""An approved first green still proposes (ADR 0030, decision 4 as amended;
issue 121).

A model's first green can come from an approved check: an unattended run set
its build aside, the person allowed it on the page, and the check ran with no
agent there to read *propose topics*. The space keeps that it is owed one, and
the next run in it is told, once. Driven in-process, as `test_approvals` drives
a run, with Blender stubbed.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_approvals import AsideCase    # noqa: E402
from test_launcher import stub_blender    # noqa: E402

from console import approvals    # noqa: E402
from console.run import Run    # noqa: E402
from lib import lock, topics    # noqa: E402

BUILD = ("Bash", {"command": "contour check"})
ASKED = "propose topics to find this model by"


class OwedCase(AsideCase):

    def setUp(self):
        super().setUp()
        patched = mock.patch.dict(os.environ, {"BLENDER": str(stub_blender(self.space))})
        patched.start()
        self.addCleanup(patched.stop)

    def allowed_build(self):
        """An unattended run's build, set aside and then allowed on the page:
        what became of it."""
        self.ran(BUILD)
        self.until("finished")
        [waiting] = approvals.load(self.space)
        return approvals.answer(self.space, waiting["id"], True)


class OwedTest(OwedCase):

    def test_an_approved_first_green_says_the_next_run_proposes(self):
        answered = self.allowed_build()
        self.assertEqual(answered["outcome"], "applied")
        self.assertIn("the next run here proposes topics", answered["said"])

    def test_the_next_run_is_told_to_propose_and_the_one_after_is_not(self):
        self.allowed_build()
        self.assertIn(ASKED, self.prompted())
        self.assertNotIn(ASKED, self.prompted())

    def test_a_run_refused_the_space_leaves_it_owed(self):
        self.allowed_build()
        held = lock.take(self.space, "contour check")
        with self.assertRaises(lock.Held):
            Run(self.space, drive=lambda *a: None).start("add a tail")
        lock.release(self.space, held)
        self.assertIn(ASKED, self.prompted())

    def test_a_space_past_its_first_green_is_owed_nothing(self):
        (self.space / ".contour" / "first-green").write_text("")
        self.assertEqual(self.allowed_build()["said"], "")
        self.assertNotIn(ASKED, self.prompted())

    def test_a_space_labelled_before_its_next_run_is_not_asked(self):
        """The lobby's pass, say, between the allow and the next run."""
        self.allowed_build()
        topics.add(self.space, "crate")
        self.assertNotIn(ASKED, self.prompted())

    def prompted(self, prose="add a tail"):
        """The prompt the agent of the next run in this space is given."""
        given = []

        def drive(prompt, options, gate, say):
            given.append(prompt)
        run = Run(self.space, drive=drive)
        run.start(prose)
        self.addCleanup(lambda: run.live and run.end())
        self.until("finished")
        [prompt] = given
        self.assertIn(prose, prompt)
        return prompt


if __name__ == "__main__":
    unittest.main()
