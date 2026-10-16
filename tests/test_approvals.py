"""A gate sets its act aside, and the run goes on (ADR 0028, decisions 1, 4
and 5; issue 96).

In a run nobody is watching, a gate the run cannot pass does not park: the call
is not made, it is kept in the space as an approval waiting, and the agent is
told so and carries on. Driven in-process, as `test_run_record` drives the run.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_run_record import CASE, RecordCase    # noqa: E402

from console.run import SPEC_TOOL, Run    # noqa: E402
from lib import last_run    # noqa: E402

SPEC_WRITE = (SPEC_TOOL, {"content": "revision: 2\ndepth: 640\n",
                          "case": "Span m4 reads 640 mm, so the depth is 640."})


class AsideCase(RecordCase):

    def setUp(self):
        super().setUp()
        (self.space / "spec.yaml").write_text("revision: 1\ndepth: 600\n")
        self.home = Path(tempfile.mkdtemp())
        patched = mock.patch.dict(os.environ, {"CONTOUR_HOME": str(self.home)})
        patched.start()
        self.addCleanup(patched.stop)

    def ran(self, *calls, requester="the nightly agent"):
        """A run whose agent makes `calls` in turn and then closes, and what
        each gate gave it back."""
        given = []

        def drive(prompt, options, gate, say):
            say("text", text=CASE)
            for tool, call in calls:
                given.append(gate(tool, dict(call)))
            say("text", text="The beak is 10% longer.")
        run = Run(self.space, drive=drive)
        run.start("make the beak longer", ceiling=10**6, requester=requester)
        self.addCleanup(lambda: run.live and run.end())
        return run, given


class AsideTest(AsideCase):

    def test_a_floor_gate_sets_its_act_aside_and_the_run_finishes(self):
        _, given = self.ran(SPEC_WRITE)
        said = self.until("finished")
        # Its account is withheld from a requester: with something set aside,
        # it is the case for it (issue 100's tracer bullet).
        self.assertEqual(said["closing"], last_run.WITHHELD)
        self.assertEqual(said["approvals"], ["Claude wants to change the spec"])
        [(allow, _)] = given
        self.assertFalse(allow)
        self.assertEqual((self.space / "spec.yaml").read_text(), "revision: 1\ndepth: 600\n")

    def test_a_gate_not_on_the_ask_list_does_the_same(self):
        """No ask-list at all, so a build is not let through either."""
        self.ran(("Bash", {"command": "contour check"}), SPEC_WRITE)
        said = self.until("finished")
        self.assertEqual(said["approvals"], ["Claude wants to build the model to check its work",
                                             "Claude wants to change the spec"])

    def test_the_agent_is_told_the_act_waits_for_the_user(self):
        _, given = self.ran(SPEC_WRITE)
        self.until("finished")
        [(_, why)] = given
        self.assertIn("set aside for the user", why)
        self.assertIn("do not try it another way", why)


class KeptTest(AsideCase):
    """What is kept is what the gate would have shown; what the record says is
    only the act (ADR 0028, decision 5)."""

    def kept(self):
        def drive(prompt, options, gate, say):
            say("text", text="Span m4 reads 640 mm, so the depth is 640.")
            gate(SPEC_WRITE[0], dict(SPEC_WRITE[1]))
            say("text", text="The spec change waits for you.")
        run = Run(self.space, drive=drive)
        run.start("make the beak longer", ceiling=10**6, requester="the nightly agent")
        self.addCleanup(lambda: run.live and run.end())
        self.until("finished")
        from console import approvals
        return approvals.load(self.space)

    def test_the_call_as_written_the_act_the_diff_and_the_case(self):
        [kept] = self.kept()
        # An Edit of the whole spec as it read, which is what a later allow
        # applies; its case is kept beside it (ADR 0029).
        self.assertEqual((kept["tool"], kept["call"]),
                         ("Edit", {"file_path": str(self.space / "spec.yaml"),
                                   "old_string": "revision: 1\ndepth: 600\n",
                                   "new_string": SPEC_WRITE[1]["content"]}))
        self.assertEqual(kept["said"]["act"], "Claude wants to change the spec")
        self.assertEqual(kept["said"]["changes"], ["revision 1 → 2", "depth 600 → 640"])
        self.assertEqual(kept["case"], "Span m4 reads 640 mm, so the depth is 640.")

    def test_the_record_holds_the_act_and_nothing_under_it(self):
        self.kept()
        record = last_run.path(self.space).read_text()
        for leaked in ("640", "depth", "spec.yaml", "Edit", "m4"):
            self.assertNotIn(leaked, record)

    def test_it_is_kept_where_a_space_ignores_it(self):
        self.kept()
        from console import approvals
        self.assertEqual(approvals.path(self.space).parent, self.space / ".contour")


class NoBannerTest(unittest.TestCase):
    """Nothing is blocked while the person is away, so nothing has to reach
    them: the banner is withdrawn (ADR 0028, decision 4)."""

    def test_nothing_in_the_toolkit_posts_a_notification(self):
        root = Path(__file__).resolve().parent.parent
        sources = [root / "contour", *root.glob("lib/*.py"), *root.glob("console/*.py")]
        for source in sources:
            text = source.read_text()
            for posting in ("osascript", "display notification", "notify-send",
                            "CONTOUR_NOTIFIER"):
                self.assertNotIn(posting, text, source.name)


class AttendedTest(AsideCase):

    def test_an_attended_runs_gate_still_waits_for_the_person(self):
        run, given = self.ran(SPEC_WRITE, requester=None)
        said = self.until("waiting for you")
        self.assertEqual(said["act"], "Claude wants to change the spec")
        self.assertIsNotNone(run.pending)
        self.assertNotIn("approvals", said)
        from console import approvals
        self.assertEqual(approvals.load(self.space), [])


if __name__ == "__main__":
    unittest.main()
