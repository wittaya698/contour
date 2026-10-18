"""`contour worksheet`: every span drawn onto its reference, as one picture
(ADR 0022, decision 8; issue 45).

The user sees spans on the canvas; the agent cannot. The worksheet is the same
picture for the agent, once. What it says about each span is worked out here
without Blender: only reading the photographs and saving the image need it.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import marks as marks_store
from lib import span
from lib import worksheet

try:
    import numpy as np
    from lib import worksheet_draw
except ImportError:          # a bare clone: numpy comes with Blender, not here
    np = worksheet_draw = None

QUESTION = {"extent": "across", "of": None, "anchor": 1700.0,
            "tol": 0.05, "bg_tol": 0.10}


class SpanCase(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.marks = self.tmp / "marks.json"

    def last(self):
        return [m for m in marks_store.load(self.marks) if m.get("to")][-1]["id"]

    def snapped(self, ref="front.jpg"):
        span.pinned(self.marks, ref, QUESTION, ([10, 50], [110, 50]), 2.0, "the body")
        return self.last()

    def eyed(self, ref="front.jpg"):
        span.by_eye(self.marks, ref, ([10, 80], [60, 80]), 2.0, "the seat")
        return self.last()

    def labels(self):
        return {s["id"]: s["label"] for s in worksheet.spans(marks_store.load(self.marks))}


class LabelTest(SpanCase):
    """Each span says its id, its number, whose it is, how its ends were
    placed, and the user's answer to it, if any."""

    def test_an_unanswered_agent_span_says_whose_how_and_that_it_waits(self):
        snapped, eyed = self.snapped(), self.eyed()
        got = self.labels()
        self.assertEqual(got[snapped], [f"{snapped} 200 mm ±4",
                                        "agent, snapped, unanswered"])
        self.assertEqual(got[eyed], [f"{eyed} 100 mm ±4",
                                     "agent, by eye, unanswered"])

    def test_an_answered_span_says_the_answer_and_a_rejected_one_is_kept(self):
        """Adopted, it is the user's and keeps how it was placed; corrected,
        its ends are the user's own; rejected, it is still on the picture."""
        adopted, corrected, rejected = self.eyed(), self.snapped(), self.snapped()
        marks_store.adopt(self.marks, adopted)
        marks_store.correct(self.marks, corrected, [10, 50], [160, 50],
                            span.reads([10, 50], [160, 50], 2.0))
        marks_store.reject(self.marks, rejected, "the wing")
        got = self.labels()
        self.assertEqual(got[adopted][1], "user, by eye, adopted")
        self.assertEqual(got[corrected], [f"{corrected} 300 mm ±4",
                                          "user, by hand, corrected"])
        self.assertEqual(got[rejected][1], "agent, snapped, rejected")

    def test_a_user_s_span_says_it_is_theirs_and_whether_it_was_measured(self):
        drawn = marks_store.append(self.marks, {"ref": "side.jpg", "pixel": [1, 2],
                                                "to": [9, 2], "text": "the depth"})
        self.assertEqual(self.labels()[drawn["id"]],
                         [f"{drawn['id']} not measured", "user, by hand"])
        span.measure(self.marks, drawn["id"], 2.0)
        self.assertEqual(self.labels()[drawn["id"]][0], f"{drawn['id']} 16 mm ±4")

    def test_a_mark_that_is_not_a_span_is_not_on_it(self):
        note = marks_store.append(self.marks, {"ref": "side.jpg", "pixel": [1, 2],
                                               "text": "a pin"})
        sheet = marks_store.append(self.marks, {"view": "front", "pixel": [1, 2],
                                                "text": "on the sheet"})
        self.assertFalse({note["id"], sheet["id"]} & set(self.labels()))


class DirectionLabelTest(SpanCase):
    """A direction is on the worksheet apart from the spans: its own entry,
    saying it is one, whose, how its lines were placed, and the answer."""

    def directed(self, ref="front.jpg", eyed=False):
        lines = [{"from": [10, 20], "to": [110, 30], "placed": "snapped", "question": ["a", "b"]},
                 {"from": [10, 120], "to": [110, 110],
                  "placed": "by eye" if eyed else "snapped", "question": ["c", "d"]}]
        return marks_store.append(self.marks, {"ref": ref, "direction": "x", "lines": lines,
                                               "pixel": [60, 25], "text": "the long edges"},
                                  author="agent")["id"]

    def test_a_direction_says_it_is_one_and_is_not_a_span(self):
        snapped, eyed = self.directed(), self.directed(eyed=True)
        got = {d["id"]: d["label"] for d in worksheet.directions(marks_store.load(self.marks))}
        self.assertEqual(got[snapped], [f"{snapped} direction x", "agent, snapped, unanswered"])
        self.assertEqual(got[eyed], [f"{eyed} direction x", "agent, 1 line by eye, unanswered"])
        self.assertEqual(self.labels(), {})

    def test_a_direction_changes_what_the_worksheet_was_drawn_from(self):
        """And spans alone print as they did, so no worksheet drawn before
        directions existed is called stale by their arriving in the code."""
        self.snapped()
        kept = marks_store.load(self.marks)
        said = json.dumps(worksheet.spans(kept), sort_keys=True).encode()
        self.assertEqual(worksheet.fingerprint(kept), hashlib.sha256(said).hexdigest()[:12])
        self.directed()
        self.assertNotEqual(worksheet.fingerprint(marks_store.load(self.marks)),
                            worksheet.fingerprint(kept))


def paper(h=200, w=300):
    """A reference with nothing on it: white, as `beaky`'s paper is."""
    return np.ones((h, w, 3), dtype=np.float32)


@unittest.skipUnless(np, "needs numpy, which the worksheet is drawn with")
class ComposeTest(SpanCase):
    """The picture itself: references with spans, laid out as one image."""

    def compose(self, pictures):
        return worksheet_draw.compose(pictures, marks_store.load(self.marks))

    def at(self, placed, ref, point):
        """Where a pixel of a reference landed on the worksheet."""
        x, y, k = placed[ref]
        return int(round(y + point[1] * k)), int(round(x + point[0] * k))

    def test_a_direction_is_drawn_across_its_reference_to_show_where_it_meets(self):
        """Its lines run past their ends, to the picture's edge, where a span
        stops at its own: the point is where they would cross."""
        lines = [{"from": [10, 20], "to": [110, 30], "placed": "snapped"},
                 {"from": [10, 120], "to": [110, 110], "placed": "snapped"}]
        marks_store.append(self.marks, {"ref": "side.jpg", "direction": "x", "lines": lines,
                                        "pixel": [60, 25], "text": "the long edges"},
                           author="agent")
        image, placed = self.compose({"side.jpg": paper()})
        self.assertEqual(set(placed), {"side.jpg"})
        y, x = self.at(placed, "side.jpg", (250, 44))
        np.testing.assert_allclose(image[y, x], worksheet_draw.AGENT, atol=1e-6)

    def test_only_references_with_a_span_are_on_it(self):
        self.snapped("front.jpg")
        image, placed = self.compose({"front.jpg": paper(), "side.jpg": paper()})
        self.assertEqual(set(placed), {"front.jpg"})
        self.assertEqual(image.ndim, 3)

    def test_each_span_is_drawn_in_the_colour_of_whose_it_is(self):
        """The canvas's colours: blue for the agent's, red for the user's,
        and grey for a rejected one, which is drawn and not left off."""
        agent, rejected = self.snapped("front.jpg"), self.snapped("side.jpg")
        marks_store.reject(self.marks, rejected, "the wing")
        mine = marks_store.append(self.marks, {"ref": "top.jpg", "pixel": [10, 50],
                                               "to": [110, 50], "text": "by hand"})
        image, placed = self.compose({r: paper() for r in ("front.jpg", "side.jpg",
                                                           "top.jpg")})
        for ref, colour in (("front.jpg", worksheet_draw.AGENT), ("side.jpg", worksheet_draw.REJECTED),
                            ("top.jpg", worksheet_draw.USER)):
            with self.subTest(ref=ref):
                y, x = self.at(placed, ref, (60, 50))
                np.testing.assert_allclose(image[y, x], colour, atol=1e-6)
        self.assertTrue(agent and mine)

    def test_a_by_eye_span_is_broken_where_a_snapped_one_is_solid(self):
        self.snapped("front.jpg")
        span.by_eye(self.marks, "side.jpg", ([10, 50], [110, 50]), 2.0, "the seat")
        image, placed = self.compose({"front.jpg": paper(), "side.jpg": paper()})

        def inked(ref):
            return sum(np.allclose(image[self.at(placed, ref, (x, 50))], worksheet_draw.AGENT)
                       for x in range(20, 100))
        self.assertEqual(inked("front.jpg"), 80)
        self.assertLess(inked("side.jpg"), 60)
        self.assertGreater(inked("side.jpg"), 20)

    def test_no_label_covers_a_span(self):
        """Found on `beaky`'s side: a span's label sat on the line of the
        span drawn just above it."""
        for y in (50, 63):
            span.pinned(self.marks, "front.jpg", QUESTION, ([10, y], [110, y]),
                        2.0, "the body")
        image, placed = self.compose({"front.jpg": paper()})
        for y in (50, 63):
            with self.subTest(y=y):
                inked = sum(np.allclose(image[self.at(placed, "front.jpg", (x, y))],
                                        worksheet_draw.AGENT) for x in range(12, 108))
                self.assertEqual(inked, 96)

    def test_each_line_carries_its_id_beside_it(self):
        """A label moved off a crowd of spans is no longer beside its own, so
        the id is also printed at the line's left end, where it cannot drift."""
        span.pinned(self.marks, "front.jpg", QUESTION, ([60, 50], [110, 50]),
                    2.0, "the body")
        image, placed = self.compose({"front.jpg": paper()})
        y, x = self.at(placed, "front.jpg", (60, 50))
        left = image[y - 10:y + 10, x - 50:x - 6]
        self.assertTrue(np.any(np.all(np.isclose(left, worksheet_draw.INK), axis=-1)))

    def test_the_same_marks_and_references_make_the_same_image(self):
        self.snapped()
        self.eyed()
        first, _ = self.compose({"front.jpg": paper()})
        again, _ = self.compose({"front.jpg": paper()})
        np.testing.assert_array_equal(first, again)


class NoSpansTest(SpanCase):
    """With nothing to draw, nothing is written, and the launcher says so
    without starting Blender."""

    def contour(self, *args):
        (self.tmp / ".contour").mkdir(exist_ok=True)
        (self.tmp / ".contour" / "project").write_text("toolkit: stub\n")
        return subprocess.run([sys.executable, str(ROOT / "contour"), *args],
                              cwd=str(self.tmp), env=dict(os.environ, BLENDER="/nonexistent"),
                              capture_output=True, text=True, timeout=60)

    def test_a_space_with_references_and_no_spans_says_so_and_writes_nothing(self):
        (self.tmp / "refs").mkdir()
        (self.tmp / "refs" / "front.jpg").write_bytes(b"not read")
        marks_store.append(self.marks, {"ref": "front.jpg", "pixel": [1, 2],
                                        "text": "a pin, not a span"})
        r = self.contour("worksheet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("no spans", r.stdout)
        self.assertFalse((self.tmp / worksheet.NAME).exists())

    def test_a_direction_alone_is_something_to_draw(self):
        lines = [{"from": [1, 2], "to": [9, 3]}, {"from": [1, 8], "to": [9, 7]}]
        marks_store.append(self.marks, {"ref": "front.jpg", "direction": "x",
                                        "lines": lines, "pixel": [5, 2], "text": "edges"},
                           author="agent")
        r = self.contour("worksheet")
        self.assertNotIn("nothing to draw", r.stdout)


BLENDER = os.environ.get("BLENDER")
BEAKY = ROOT / "project" / "beaky" / "refs"


@unittest.skipUnless(BLENDER, "needs $BLENDER: the references are read by Blender")
@unittest.skipUnless((BEAKY / "front.jpg").exists(), "needs beaky's references on this machine")
class CommandTest(unittest.TestCase):
    """`contour worksheet` on copies of `beaky`'s references, in a space of
    their own, so nothing of beaky's is written."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.space = cls.tmp / "sheeted"
        cls.env = dict(os.environ, CONTOUR_SPACES=str(cls.tmp),
                       CONTOUR_HOME=str(cls.tmp / "home"),
                       GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        cls.contour("init", "sheeted", cwd=cls.tmp)
        for name in ("front.jpg", "side.jpg"):
            shutil.copy(BEAKY / name, cls.space / "refs" / name)
        (cls.space / "spec.yaml").write_text(
            "model: sheeted\nrevision: 1\ndimensions:\n  height: { value: 1700, tol: 5 }\n")
        for args in (("refs/front.jpg", "--silhouette", "--extent", "across", "the body"),
                     ("refs/side.jpg", "--by-eye", "--from", "500,600", "--to", "900,600",
                      "the depth, by eye"),
                     ("refs/front.jpg", "--scanline", "250", "--of", "#3B3F72",
                      "--runs", "1,2", "--between", "centres", "the legs")):
            r = cls.contour("measure", *args)
            assert r.returncode == 0, r.stdout + r.stderr
        legs = [m for m in marks_store.load(cls.space / "marks.json") if m.get("to")][-1]
        marks_store.reject(cls.space / "marks.json", legs["id"], "the feet")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    @classmethod
    def contour(cls, *args, cwd=None):
        return subprocess.run([sys.executable, str(ROOT / "contour"), *args],
                              cwd=str(cwd or cls.space), env=cls.env,
                              capture_output=True, text=True, timeout=300)

    def sums(self):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.space / "refs").iterdir()}

    def test_it_writes_one_image_and_names_it_and_the_count(self):
        """Three spans, the rejected one counted: it is on the picture."""
        r = self.contour("worksheet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(worksheet.NAME, r.stdout)
        self.assertIn("3 spans on 2 references", r.stdout)
        self.assertTrue((self.space / worksheet.NAME).read_bytes().startswith(b"\x89PNG"))

    def test_no_reference_changes(self):
        before = self.sums()
        r = self.contour("worksheet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.sums(), before)

    def test_two_runs_over_the_same_marks_write_identical_images(self):
        self.contour("worksheet")
        first = (self.space / worksheet.NAME).read_bytes()
        self.contour("worksheet")
        self.assertEqual((self.space / worksheet.NAME).read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
