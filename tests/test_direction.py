"""Claude proposes directions (ADR 0032, decision 2; issue 140).

A direction is lines along edges parallel in the object. The agent names the
edges and picks them from what measurement found, as it picks a span's runs:
along a row or a column of the picture, every place the colour changes
sharply is a numbered crossing, and a line is two crossings picked. Code
places the line; there is no spelling of a snapped one that takes a pixel.

The picture here is a box with flat-coloured faces, painted from its corners
as a camera sees them, so the edge each line should land on is known to a
fraction of a pixel. Painted in pure Python: finding the edges is arithmetic,
and only reading a real image needs Blender.
"""
import json
import math
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import direction  # noqa: E402
from lib import marks  # noqa: E402

SIZE = (400, 300)
BOX = (300.0, 200.0, 150.0)
EYE = (700.0, 600.0, 900.0)
FACES = {"top": ((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)),
         "front": ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
         "side": ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))}
COLOURS = {"top": (0.85, 0.80, 0.70), "front": (0.80, 0.30, 0.25), "side": (0.35, 0.40, 0.70)}
PAPER = (0.95, 0.95, 0.95)


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def corners(eye=EYE, f=650.0):
    """Where each corner lands, in pixels counted from the top, unrounded."""
    target = [c / 2 for c in BOX]
    forward = _unit([t - e for t, e in zip(target, eye)])
    right = _unit(_cross(forward, [0, 1, 0]))
    up = _cross(right, forward)
    seen = {}
    for i in (0, 1):
        for j in (0, 1):
            for k in (0, 1):
                d = [i * BOX[0] - eye[0], j * BOX[1] - eye[1], k * BOX[2] - eye[2]]
                depth = sum(a * b for a, b in zip(d, forward))
                seen[i, j, k] = (SIZE[0] / 2 + f * sum(a * b for a, b in zip(d, right)) / depth,
                                 SIZE[1] / 2 - f * sum(a * b for a, b in zip(d, up)) / depth)
    return seen


def _inside(p, quad):
    signs = []
    for n in range(4):
        (ax, ay), (bx, by) = quad[n], quad[(n + 1) % 4]
        signs.append((bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax) > 0)
    return all(signs) or not any(signs)


def paint(seen):
    """The picture, rows from the top, each pixel's colour taken at its centre."""
    quads = {name: [seen[c] for c in face] for name, face in FACES.items()}
    return [[next((COLOURS[n] for n, q in quads.items() if _inside((x, y), q)), PAPER)
             for x in range(SIZE[0])] for y in range(SIZE[1])]


def reader(picture):
    """What `contour measure` hands over: one row or one column of colours."""
    def strip(kind, index):
        return picture[index] if kind == "row" else [row[index] for row in picture]
    return strip


def off(point, a, b):
    """How far `point` is from the line through `a` and `b`, in pixels."""
    (ax, ay), (bx, by) = a, b
    return abs((bx - ax) * (point[1] - ay) - (by - ay) * (point[0] - ax)) / math.dist(a, b)


SEEN = corners()
STRIP = reader(paint(SEEN))


class LineTest(unittest.TestCase):

    def test_two_picked_crossings_land_on_the_edge_named(self):
        """Down a column across the box: paper to top face, top face to front,
        front to paper. The second crossing is the edge between top and front."""
        got = direction.line(STRIP, SIZE, "col:0.3#2", "col:0.55#2")
        self.assertTrue(got["ok"], got)
        truth = (SEEN[0, 1, 1], SEEN[1, 1, 1])
        for end in (got["from"], got["to"]):
            self.assertLessEqual(off(end, *truth), 1.0, got)


class AskedTest(unittest.TestCase):
    """How `contour measure` is asked for one, and what it shows to pick from."""

    def test_the_edges_a_strip_crosses_are_listed_to_pick_from(self):
        self.assertEqual(direction.edges(STRIP, SIZE, "col:0.3"),
                         "  edges column 120 crosses #1 at 81.5, #2 at 96.5, #3 at 198.5")

    def test_the_form_names_the_direction_its_lines_and_what_they_are(self):
        got = direction.form(["--direction", "x", "--line", "col:0.3#2,col:0.55#2",
                              "--line", "col:0.3#3,col:0.55#3",
                              "--line-by-eye", "108,194,253,248", "the long edges"])
        self.assertEqual(got, {"ok": True, "name": "x", "text": "the long edges",
                               "picks": [("col:0.3#2", "col:0.55#2"), ("col:0.3#3", "col:0.55#3"),
                                         {"by_eye": [[108.0, 194.0], [253.0, 248.0]]}]})

    def test_a_flag_the_form_does_not_take_is_refused(self):
        got = direction.form(["--direction", "x", "--line", "col:0.3#2,col:0.55#2",
                              "--from", "1,2", "edges"])
        self.assertFalse(got["ok"])
        self.assertIn("--from is not part of a direction", got["lines"][0])


class ProposedTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.marks = self.tmp / "marks.json"

    def kept(self):
        return json.loads(self.marks.read_text()) if self.marks.exists() else []

    def propose(self, lines, text="the box's long edges"):
        return direction.propose(self.marks, "box.png", "x", lines, STRIP, SIZE, text)

    def test_a_direction_is_one_question_with_its_lines_and_how_each_was_asked(self):
        got = self.propose([("col:0.3#2", "col:0.55#2"), ("col:0.3#3", "col:0.55#3")])
        self.assertTrue(got["ok"], got)
        (drawn,) = self.kept()
        self.assertEqual({k: drawn[k] for k in ("ref", "direction", "text", "author", "status")},
                         {"ref": "box.png", "direction": "x", "text": "the box's long edges",
                          "author": "agent", "status": "open"})
        self.assertEqual([l["placed"] for l in drawn["lines"]], ["snapped", "snapped"])
        self.assertEqual(drawn["lines"][1]["question"], ["col:0.3#3", "col:0.55#3"])
        truth = (SEEN[0, 0, 1], SEEN[1, 0, 1])
        for end in (drawn["lines"][1]["from"], drawn["lines"][1]["to"]):
            self.assertLessEqual(off(end, *truth), 1.0, drawn)
        self.assertIn(drawn["id"], got["lines"][0])

    def test_a_crossing_not_found_is_refused_naming_those_found(self):
        got = self.propose([("col:0.3#2", "col:0.55#2"), ("col:0.3#4", "col:0.55#3")])
        self.assertFalse(got["ok"])
        self.assertIn("column 120 crosses #1 at 81.5, #2 at 96.5, #3 at 198.5", got["lines"][0])
        self.assertEqual(self.kept(), [])

    def test_a_line_where_nothing_snaps_is_placed_by_eye_and_says_so(self):
        """A photograph's edge may be too soft to cross sharply; that line is
        the agent's own placing, labelled so, as a by-eye span's ends are."""
        got = self.propose([("col:0.3#2", "col:0.55#2"), {"by_eye": [[108, 194], [253, 248]]}])
        self.assertTrue(got["ok"], got)
        (drawn,) = self.kept()
        self.assertEqual(drawn["lines"][1], {"from": [108, 194], "to": [253, 248],
                                             "placed": "by eye"})
        self.assertIn("1 by eye", got["lines"][0])

    def test_one_line_is_not_a_direction(self):
        """Where lines meet needs two of them."""
        got = self.propose([("col:0.3#2", "col:0.55#2")])
        self.assertFalse(got["ok"])
        self.assertIn("at least two lines", got["lines"][0])
        self.assertEqual(self.kept(), [])



class AnsweredTest(unittest.TestCase):
    """Answered as a span is: adopt, correct, reject, through the same store
    and the same record of who drew it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.marks = self.tmp / "marks.json"
        direction.propose(self.marks, "box.png", "x",
                          [("col:0.3#2", "col:0.55#2"), ("col:0.3#3", "col:0.55#3")],
                          STRIP, SIZE, "the box's long edges")
        (self.drawn,) = marks.load(self.marks)

    def test_adopted_it_is_the_users_and_says_who_drew_it(self):
        self.assertIn("mark", marks.adopt(self.marks, self.drawn["id"]))
        (got,) = marks.load(self.marks)
        self.assertEqual((got["author"], got["drawn_by"], got["answer"]),
                         ("user", "agent", "adopted"))

    def test_rejected_it_is_closed_with_why(self):
        self.assertIn("mark", marks.reject(self.marks, self.drawn["id"], "those are the shadow"))
        (got,) = marks.load(self.marks)
        self.assertEqual((got["status"], got["answer"], got["why"]),
                         ("closed", "rejected", "those are the shadow"))

    def test_corrected_it_takes_the_users_lines_and_keeps_the_agents(self):
        mine = [{"from": [100, 91], "to": [258, 134]}, {"from": [108, 194], "to": [253, 248]}]
        self.assertIn("mark", marks.correct_lines(self.marks, self.drawn["id"], mine))
        (got,) = marks.load(self.marks)
        self.assertEqual((got["author"], got["drawn_by"], got["answer"]),
                         ("user", "agent", "corrected"))
        self.assertEqual(got["lines"], mine)
        self.assertEqual(got["agent_lines"], self.drawn["lines"])

    def test_a_direction_is_not_corrected_by_two_ends(self):
        got = marks.correct(self.marks, self.drawn["id"], [1, 1], [9, 9], "8 px")
        self.assertIn("corrected by its lines", got["refused"])

    def test_a_correction_still_needs_two_lines(self):
        got = marks.correct_lines(self.marks, self.drawn["id"], [{"from": [1, 1], "to": [9, 9]}])
        self.assertIn("at least two lines", got["refused"])


class SkillTest(unittest.TestCase):

    def test_the_skill_says_to_propose_directions_before_spans_on_an_angled_reference(self):
        skill = (Path(__file__).resolve().parent.parent / "templates" / "space" / ".claude"
                 / "skills" / "build-model" / "SKILL.md").read_text(encoding="utf-8")
        skill = " ".join(skill.split())
        self.assertIn("before any span on a reference that is not straight on", skill)
        self.assertIn("--edges col:", skill)
        self.assertIn("--direction x --line", skill)


if __name__ == "__main__":
    unittest.main()
