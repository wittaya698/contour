"""A spec gate names spans still unanswered (ADR 0035, decision 7; issue 159).

A spec write's gate, shown while by-eye agent spans are unanswered, adds a
line naming them by what they measure and their ids, with a way to their
cards. It does not stop Allow: rule 1's confirm is still the user's to give.
Skipped at a park, or drawn after it, a span is still unanswered.
"""
import shutil
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import one_run    # noqa: E402,F401  one suite run per machine (issue 94)
from test_span_park import WAIT_S, ParkCase    # noqa: E402

from console.run import SPEC_TOOL, Run    # noqa: E402
from lib.canvas import PAGE    # noqa: E402
import test_asked    # noqa: E402
from test_asked import span    # noqa: E402
from test_found import function    # noqa: E402

SPEC = "revision: 1\ndepth: 600\n"
WRITE = (SPEC_TOOL, {"content": SPEC,
                     "case": "A new spec: revision 1, and depth 600 mm, which you gave."})


class GateCase(ParkCase):

    def gated(self):
        """A watched run's spec gate, as the page is sent it, and the run."""
        given = []

        def drive(prompt, options, gate, say):
            given.append(gate(*WRITE))
        run = Run(self.space, drive=drive)
        self.addCleanup(lambda: run.live and run.end())
        run.start("draft the spec", ceiling=10**6)
        deadline = time.monotonic() + WAIT_S
        while run.pending is None:
            self.assertLess(time.monotonic(), deadline, "the gate never stopped")
            time.sleep(0.01)
        [event] = [e for e in run.events if e["kind"] == "gate"]
        return event["said"], run, given


class NamedTest(GateCase):

    def test_by_eye_spans_unanswered_are_named_on_the_spec_gate(self):
        width, grille = self.drawn("width"), self.drawn("grille")
        said, _, _ = self.gated()
        self.assertEqual(said["unanswered"], {
            "spans": [width, grille],
            "text": f"2 of Claude's spans are still unanswered: width ({width}), "
                    f"grille ({grille}). Their numbers are not in this spec"})

    def test_with_none_unanswered_the_line_is_not_there(self):
        from lib import marks
        marks.adopt(self.space / marks.NAME, self.drawn("width"))
        said, _, _ = self.gated()
        self.assertIsNone(said["unanswered"])

    def test_a_snapped_span_unanswered_is_not_named(self):
        """Its number is already the agent's reading to propose (ADR 0035,
        decision 2)."""
        self.drawn("height", placed="snapped")
        width = self.drawn("width")
        said, _, _ = self.gated()
        self.assertEqual(said["unanswered"]["spans"], [width])
        self.assertTrue(said["unanswered"]["text"].startswith(
            f"1 of Claude's spans is still unanswered: width ({width}). Its number is"))

    def test_a_span_skipped_at_a_park_is_still_named(self):
        from lib import worksheet
        width = self.drawn("width")
        worksheet.skip(self.space / ".contour", "an earlier run", {width})
        said, _, _ = self.gated()
        self.assertEqual(said["unanswered"]["spans"], [width])


class AllowTest(GateCase):

    def test_allow_writes_the_spec_with_the_line_there(self):
        self.drawn("width")
        said, run, given = self.gated()
        self.assertIsNotNone(said["unanswered"])
        run.answer(run.pending["id"], True)
        deadline = time.monotonic() + WAIT_S
        while not given:
            self.assertLess(time.monotonic(), deadline, "the gate never answered")
            time.sleep(0.01)
        # The write itself is the tool's once allowed (`spec_written`).
        self.assertEqual(given[0][0], True)

    def test_deny_writes_nothing_with_the_line_there(self):
        self.drawn("width")
        _, run, given = self.gated()
        run.answer(run.pending["id"], False, "not yet")
        deadline = time.monotonic() + WAIT_S
        while not given:
            self.assertLess(time.monotonic(), deadline, "the gate never answered")
            time.sleep(0.01)
        self.assertEqual(given[0], (False, "not yet"))
        self.assertFalse((self.space / "spec.yaml").exists())


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class CardTest(unittest.TestCase):
    """The way from the gate to a span's card: the card asks the span named."""

    run_page = test_asked.AskedTest.run_page

    def wanted(self, marks, skipped, wanted):
        return self.run_page(["spanState", "foundation", "named", "asking"],
                             "asking(marks, new Set(skipped), null, null, wanted)",
                             marks=marks, skipped=skipped, wanted=wanted)["mark"]

    def test_the_card_asks_the_span_the_gate_named_skipped_or_not(self):
        marks = [span("m1", placed="by eye"), span("m2", placed="by eye")]
        self.assertEqual(self.wanted(marks, [], "m2")["id"], "m2")
        self.assertEqual(self.wanted(marks, ["m2"], "m2")["id"], "m2")

    def test_once_answered_the_card_goes_on_to_the_next(self):
        marks = [span("m1", placed="by eye"), span("m2", placed="by eye", answer="adopted")]
        self.assertEqual(self.wanted(marks, [], "m2")["id"], "m1")


class PageTest(unittest.TestCase):
    """How it looks is for eyes on a real console; that it is wired is here."""

    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")

    def test_the_gate_card_has_a_place_for_the_line(self):
        gate = self.page.split('<template id="gate">', 1)[1].split("</template>", 1)[0]
        self.assertIn('<p class="unanswered" hidden></p>', gate)

    def test_the_gate_says_the_line_and_each_span_goes_to_its_card(self):
        drawn = function(self.page, "gate")
        self.assertIn("said.unanswered", drawn)
        self.assertIn("toCard(id)", drawn)
        self.assertIn("wanted = id;", function(self.page, "toCard"))
        for name in ("draw", "questions"):
            self.assertIn("parkedOn, wanted)", function(self.page, name), name)


if __name__ == "__main__":
    unittest.main()
