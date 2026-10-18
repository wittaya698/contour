"""The anchor is a span (ADR 0032, decision 3; issue 139).

The scale used to be the spec's height over the foreground box's, which read
nothing on a reference whose stated size is a width, and read the deck under
a photographed object as the object. Now the anchor is a span on each
reference: the agent proposes the one the stated size is the length of, the
user answers it, and with the reference's directions answered too, a span
reads in millimetres through the camera. Until then it reads pixels, and
says what it waits on.

The reference is a box projected through a known camera (`test_camera`), so
every reading has a known answer.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import marks, span  # noqa: E402
from lib.canvas import Canvas  # noqa: E402
from client import post  # noqa: E402
from test_camera import BOX, SIZE, STEEP, edge, lines, picture  # noqa: E402

SEEN = picture(STEEP)
READS = re.compile(r"(\d+) mm ±(\d+) mm")


class AnchorCase(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.marks = self.tmp / "marks.json"

    def directions(self, answer=True):
        for axis, name in enumerate("xyz"):
            drawn = marks.append(self.marks, {
                "ref": "box.png", "direction": name, "text": f"edges along {name}",
                "lines": [{"from": list(p), "to": list(q), "placed": "snapped"}
                          for p, q in lines(SEEN, axis)],
                "pixel": list(SEEN[0, 0, 0])}, author="agent")
            if answer:
                marks.adopt(self.marks, drawn["id"])

    def anchor(self, answer=True):
        a, b = edge(SEEN, (0, 0, 1), (1, 0, 1))
        drawn = marks.append(self.marks, {
            "ref": "box.png", "pixel": list(a), "to": list(b), "text": "the box, end to end",
            "placed": "by eye", "claims": {"dimension": "width", "mm": BOX[0]},
            "size": list(SIZE)}, author="agent")
        if answer:
            marks.adopt(self.marks, drawn["id"])
        return drawn["id"]

    def through(self, *corners):
        return span.through(marks.load(self.marks), "box.png", edge(SEEN, *corners))


class ThroughTest(AnchorCase):

    def test_a_width_anchor_answered_gives_a_span_its_millimetres(self):
        self.directions()
        self.anchor()
        said = self.through((1, 0, 1), (1, 1, 1))
        got = READS.search(said)
        self.assertIsNotNone(got, said)
        self.assertLessEqual(abs(int(got[1]) - BOX[1]), int(got[2]) + 1, said)


class WaitsTest(AnchorCase):
    """Pixels, and what the millimetres wait on, so the person knows which
    question to answer."""

    def test_with_no_anchor_span_it_says_to_propose_one(self):
        self.directions()
        said = self.through((1, 0, 1), (1, 1, 1))
        self.assertRegex(said, r"^\d+ px ±2 px")
        self.assertIn("no anchor span on box.png", said)

    def test_with_the_anchor_span_unanswered_it_names_it(self):
        self.directions()
        drawn = self.anchor(answer=False)
        said = self.through((1, 0, 1), (1, 1, 1))
        self.assertRegex(said, r"^\d+ px ±2 px")
        self.assertIn(f"waits on {drawn}, the anchor span, being answered", said)

    def test_with_the_directions_unanswered_it_says_so(self):
        self.directions(answer=False)
        self.anchor()
        said = self.through((1, 0, 1), (1, 1, 1))
        self.assertRegex(said, r"^\d+ px ±2 px")
        self.assertIn("waits on box.png's directions: none is answered", said)

    def test_the_cameras_own_refusal_is_said(self):
        self.directions()
        self.anchor()
        said = self.through((0, 1, 0), (1, 1, 0))
        self.assertRegex(said, r"^\d+ px ±2 px")
        self.assertIn("it is tied to nothing", said)


class ClaimsTest(AnchorCase):
    """The anchor span is proposed as the length of a size the spec states,
    and asks the user whether it is."""

    def spec(self, dimensions):
        path = self.tmp / "spec.yaml"
        path.write_text("model: m\nrevision: 1\ndimensions:\n" + dimensions)
        return path

    def test_any_size_the_spec_states_can_be_claimed(self):
        spec = self.spec("  width: { value: 300, tol: 3 }\n")
        self.assertEqual(span.claimed(spec, "width"), {"dimension": "width", "mm": 300.0})

    def test_a_size_the_spec_does_not_state_is_refused(self):
        spec = self.spec("  width: { value: 300, tol: 3 }\n")
        got = span.claimed(spec, "height")
        self.assertIn("the spec states no height: it states width", got["refused"])

    def test_the_anchor_span_keeps_its_claim_and_asks_it(self):
        a, b = edge(SEEN, (0, 0, 1), (1, 0, 1))
        span.by_eye(self.marks, "box.png", (a, b), None, "the box, end to end",
                    claims={"dimension": "width", "mm": 300.0}, size=SIZE)
        drawn, said = marks.load(self.marks)
        self.assertEqual((drawn["claims"], drawn["size"]),
                         ({"dimension": "width", "mm": 300.0}, list(SIZE)))
        self.assertIn("is this the width you told me, 300 mm?", said["text"])

    def test_a_snapped_anchor_span_keeps_its_claim_and_asks_it(self):
        question = {"extent": "across", "of": None, "tol": 0.05, "bg_tol": 0.10}
        span.draw_extent(self.marks, "box.png", question, (100, 399, 50, 250), SIZE[1],
                         None, "the box, side to side",
                         claims={"dimension": "width", "mm": 300.0}, size=SIZE)
        drawn, said = marks.load(self.marks)
        self.assertEqual(drawn["claims"], {"dimension": "width", "mm": 300.0})
        self.assertEqual(said["text"], f"span {drawn['id']}: is this the width you told "
                                       f"me, 300 mm? (300 px)")


class CorrectedTest(AnchorCase):
    """The user's ends are read again as the agent's were: through the camera,
    from the marks, with no image and no spec on the canvas's side."""

    def setUp(self):
        super().setUp()
        (self.tmp / "sheet.png").write_bytes(b"\x89PNG\r\n\x1a\nsheet")
        self.canvas = Canvas(sheet=self.tmp / "sheet.png", marks=self.marks)
        self.addCleanup(self.canvas.stop)
        self.canvas.start()

    def correct(self, mark_id, ends):
        post(self.canvas, "/correct", {"id": mark_id, "pixel": list(ends[0]), "to": list(ends[1])})
        got = span.marked(self.marks, mark_id)
        return span.marked(self.marks, got["reading"])["text"]

    def test_a_corrected_span_reads_through_the_camera(self):
        self.directions()
        self.anchor()
        reads = lambda a, b: span.through(marks.load(self.marks), "box.png", (a, b))  # noqa: E731
        span.by_eye(self.marks, "box.png", edge(SEEN, (1, 0, 1), (1, 1, 0)), reads, "the corner")
        drawn = [m for m in marks.load(self.marks) if m.get("to")][-1]["id"]
        said = self.correct(drawn, edge(SEEN, (1, 0, 1), (1, 1, 1)))
        got = READS.search(said)
        self.assertIsNotNone(got, said)
        self.assertLessEqual(abs(int(got[1]) - BOX[1]), int(got[2]) + 1, said)

    def test_a_corrected_anchor_span_asks_again_at_its_new_ends(self):
        self.directions()
        drawn = self.anchor(answer=False)
        said = self.correct(drawn, edge(SEEN, (0, 0, 1), (1, 0, 0)))
        self.assertIn("is this the width you told me, 300 mm?", said)


ROOT = Path(__file__).resolve().parent.parent


class NoForegroundScaleTest(unittest.TestCase):
    """No millimetre anywhere comes from the foreground box."""

    def test_anchor_on_the_command_line_is_refused_naming_what_replaced_it(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / ".contour").mkdir()
        (tmp / ".contour" / "project").write_text("toolkit: stub\n")
        r = subprocess.run([sys.executable, str(ROOT / "contour"), "measure", "refs/a.png",
                            "--anchor", "1700", "--silhouette"],
                           cwd=str(tmp), env=dict(os.environ, BLENDER="/nonexistent"),
                           capture_output=True, text=True, timeout=60)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("the foreground box sets no scale", r.stdout)
        self.assertIn("--claims", r.stdout)

    def test_nothing_reads_a_scale_off_the_silhouette(self):
        """The old anchor read only a height, and divided it by the box's."""
        for path in (ROOT / "lib").glob("*.py"):
            self.assertNotIn("anchor_mm", path.read_text(encoding="utf-8"), path.name)
        measure = (ROOT / "lib" / "cmd_measure.py").read_text(encoding="utf-8")
        self.assertNotIn("S.k", measure)


if __name__ == "__main__":
    unittest.main()
