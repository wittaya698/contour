"""The card asks foundations first (ADR 0032, decision 6; issue 141).

A span's number waits on its reference's foundations: its directions and its
anchor span. The person answers those first, and the answer that completes
them turns the spans' numbers to millimetres there and then: the readings
are read again inside that answer, so undoing it puts them back too.

The reference is a box projected through a known camera (`test_camera`), so
every reading has a known answer.
"""
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import marks, span  # noqa: E402
from lib.canvas import PAGE, Canvas  # noqa: E402
from client import post  # noqa: E402
from test_anchor_span import SEEN, AnchorCase  # noqa: E402
from test_camera import BOX, edge  # noqa: E402
from test_found import function  # noqa: E402

READS = re.compile(r"(\d+) mm ±(\d+) mm")


class ReadAgainCase(AnchorCase):

    def setUp(self):
        super().setUp()
        (self.tmp / "sheet.png").write_bytes(b"\x89PNG\r\n\x1a\nsheet")
        self.canvas = Canvas(sheet=self.tmp / "sheet.png", marks=self.marks)
        self.addCleanup(self.canvas.stop)
        self.canvas.start()

    def span(self, *corners, text="the box's depth"):
        """An agent span, read as `contour measure` reads one."""
        reads = lambda a, b: span.through(marks.load(self.marks), "box.png", (a, b))  # noqa: E731
        span.by_eye(self.marks, "box.png", edge(SEEN, *corners), reads, text)
        return [m for m in marks.load(self.marks) if m.get("to")][-1]["id"]

    def reading(self, mark_id):
        return span.marked(self.marks, span.marked(self.marks, mark_id)["reading"])["text"]


class LastFoundationTest(ReadAgainCase):

    def test_answering_the_last_foundation_turns_a_span_to_millimetres(self):
        self.directions()
        anchor = self.anchor(answer=False)
        drawn = self.span((1, 0, 1), (1, 1, 1))
        self.assertIn("being answered", self.reading(drawn))
        post(self.canvas, "/adopt", {"id": anchor})
        got = READS.search(self.reading(drawn))
        self.assertIsNotNone(got, self.reading(drawn))
        self.assertLessEqual(abs(int(got[1]) - BOX[1]), int(got[2]) + 1)

    def test_undoing_that_answer_puts_the_readings_back_as_they_were(self):
        self.directions()
        anchor = self.anchor(answer=False)
        self.span((1, 0, 1), (1, 1, 1))
        before = self.marks.read_bytes()
        post(self.canvas, "/adopt", {"id": anchor})
        post(self.canvas, "/unanswer", {"id": anchor})
        self.assertEqual(self.marks.read_bytes(), before)


class DirectionTest(ReadAgainCase):
    """A direction is answered on the card as a span is, and moved by its
    lines' ends."""

    def test_a_direction_is_corrected_by_its_lines(self):
        self.directions(answer=False)
        drawn = next(m for m in marks.load(self.marks) if m.get("direction") == "x")
        mine = [{"from": [1, 2], "to": [30, 4]}, {"from": [2, 40], "to": [31, 44]}]
        post(self.canvas, "/correct", {"id": drawn["id"], "lines": mine})
        got = span.marked(self.marks, drawn["id"])
        self.assertEqual((got["answer"], got["lines"]), ("corrected", mine))


def asked_span(mark_id, ref="box.png", **more):
    """An agent span waiting on an answer, as `/marks` serves one."""
    return {"id": mark_id, "ref": ref, "pixel": [10, 10], "to": [60, 10],
            "author": "agent", "status": "open", "text": "the box's depth", **more}


def asked_direction(mark_id, ref="box.png", **more):
    return {"id": mark_id, "ref": ref, "pixel": [20, 12], "direction": "x",
            "lines": [{"from": [10, 10], "to": [30, 14]}, {"from": [10, 40], "to": [30, 46]}],
            "author": "agent", "status": "open", "text": "the long edges", **more}


def asked_anchor(mark_id, ref="box.png"):
    return asked_span(mark_id, ref, claims={"dimension": "width", "mm": 300.0})


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class CardTest(unittest.TestCase):
    """The page's decisions, run under node as the browser gets them."""

    def run_page(self, names, expression, **given):
        page = PAGE.read_text(encoding="utf-8")
        js = ("".join(function(page, n) for n in names)
              + "".join(f"const {k} = {json.dumps(v)};\n" for k, v in given.items())
              + f"console.log(JSON.stringify({expression}));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def order(self, all_marks, skipped=()):
        """Every question the card would ask, in turn, skipping none it is told."""
        return self.run_page(
            ["spanState", "foundation", "named", "asking"],
            "(() => { const seen = new Set(skipped), got = []; let m;"
            " while ((m = asking(marks, seen).mark)) { got.push(m.id); seen.add(m.id); }"
            " return got; })()", marks=all_marks, skipped=list(skipped))

    def test_a_reference_asks_its_directions_then_its_anchor_then_its_spans(self):
        all_marks = [asked_span("m1"), asked_span("m2", ref="pot.png"),
                     asked_direction("m3"), asked_anchor("m4"),
                     asked_direction("m5", ref="pot.png"), asked_direction("m6")]
        self.assertEqual(self.order(all_marks), ["m3", "m6", "m4", "m1", "m5", "m2"])

    def test_skip_puts_a_foundation_off_and_its_spans_are_still_asked(self):
        all_marks = [asked_span("m1"), asked_direction("m2"), asked_anchor("m3")]
        self.assertEqual(self.order(all_marks, skipped=["m2"]), ["m3", "m1"])

    def test_a_direction_is_asked_by_its_badge_and_whether_its_edges_are_parallel(self):
        all_marks = [asked_span("m1"), asked_direction("m2")]
        said = self.run_page(["spanState", "foundation", "named", "asking", "phrased"],
                             "[asking(marks, new Set()).number, phrased(marks[1])]",
                             marks=all_marks)
        self.assertEqual(said, ["direction 2", "Are these the long edges, parallel on the object?"])

    def test_an_anchor_span_asks_whether_it_is_the_size_told(self):
        said = self.run_page(["phrased"], "[phrased(marks[0]), phrased(marks[1])]",
                             marks=[asked_anchor("m1"), asked_span("m2")])
        self.assertEqual(said, ["Is this the box's depth \u2014 the width you told me, 300 mm?",
                                "Is this the box's depth?"])

    def test_a_direction_is_moved_by_any_of_its_lines_ends_and_saved_as_lines(self):
        """Every line end is a handle; the one dragged moves and the rest stay."""
        said = self.run_page(
            ["endsOf", "grab", "moved", "correction"],
            "(() => { const mark = marks[0]; let ends = endsOf(mark);"
            " const which = grab(ends, [29, 45], 12); ends = moved(ends, which, [31, 48]);"
            " return [which, correction(mark, ends)]; })()",
            marks=[asked_direction("m2")])
        self.assertEqual(said, [3, {"id": "m2", "lines": [{"from": [10, 10], "to": [30, 14]},
                                                         {"from": [10, 40], "to": [31, 48]}]}])

    def test_a_span_is_still_moved_and_saved_by_its_two_ends(self):
        said = self.run_page(["endsOf", "correction"], "correction(marks[0], endsOf(marks[0]))",
                             marks=[asked_span("m1")])
        self.assertEqual(said, {"id": "m1", "pixel": [10, 10], "to": [60, 10]})

    def number(self, text):
        return self.run_page(["oldWay", "numbered"], "numbered(text)", text=text)

    def test_a_span_asked_before_its_foundations_shows_pixels_and_why(self):
        said = self.number("span m5: 246 px \u00b12 px  (waits on m4, the anchor span, "
                           "being answered)  by eye: the bar covers the arithmetic")
        self.assertEqual(said, {"number": "246 px \u00b12 px",
                                "why": "waits on m4, the anchor span, being answered"})

    def test_a_span_read_through_the_camera_shows_its_millimetres_alone(self):
        said = self.number("span m5: 196 mm \u00b119 mm  (through the camera, along y, "
                           "against m4)")
        self.assertEqual(said, {"number": "196 mm \u00b119 mm", "why": ""})

    def test_an_anchor_spans_number_is_its_pixels_since_its_question_is_asked_above(self):
        said = self.number("span m4: is this the width you told me, 300 mm? (155 px)  "
                           "by eye: the bar covers the arithmetic")
        self.assertEqual(said, {"number": "155 px", "why": ""})

    def test_a_direction_shows_how_many_lines_it_is(self):
        said = self.run_page(["numberOf", "oldWay", "numbered"], "numberOf(marks[0], marks)",
                             marks=[asked_direction("m2")])
        self.assertEqual(said, {"number": "2 lines", "why": ""})

    def test_what_a_span_waits_on_is_named_by_its_badge_as_the_card_names_it(self):
        """The card says *span 3*; the reading says m4. The person sees one."""
        all_marks = [asked_span("m1"), asked_span("m2"), asked_anchor("m4"),
                     {"id": "m5", "ref": "box.png", "pixel": [1, 1], "author": "agent",
                      "status": "open", "text": "span m1: 115 px \u00b12 px  (waits on m4, "
                                                "the anchor span, being answered)"}]
        all_marks[0]["reading"] = "m5"
        said = self.run_page(["named", "oldWay", "numbered", "numberOf"], "numberOf(marks[0], marks)",
                             marks=all_marks)
        self.assertEqual(said, {"number": "115 px \u00b12 px",
                                "why": "waits on span 3, the anchor span, being answered"})


if __name__ == "__main__":
    unittest.main()
