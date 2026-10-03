"""A snapped span across an extent: the silhouette's, or one colour's (ADR 0022,
decisions 2 and 4; issue 41).

Slice 40 snaps a span to the runs of a scanline. The other two things `contour
measure` finds are extents, and a span drawn across one lands on the edges the
report already gives, specks ignored (ADR 0017): never a second reading of the
same picture.

As in slice 40, everything but reading the image is out of Blender, so these
tests make the span with the extent already found.
"""
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

BOX = (100, 299, 50, 849)
"""An extent as `cmd_measure.bbox` reports it: x0, x1, y0, y1, inclusive pixel
columns and rows, rows counted from the bottom."""


class EdgesTest(unittest.TestCase):

    def test_each_extent_reads_what_the_report_prints_for_it(self):
        """The report prints w as x1 - x0 + 1 and h as y1 - y0 + 1; a span
        across or up the same extent must read the same number."""
        x0, x1, y0, y1 = BOX
        for extent, px in (("across", x1 - x0 + 1), ("up", y1 - y0 + 1)):
            with self.subTest(extent=extent):
                ends = span.edges(BOX, extent, height=1000)
                self.assertEqual(span.reading(*ends, 1.0)["px"], px)

    def test_the_ends_lie_on_the_extent_s_own_edges_counted_from_the_top(self):
        """Across at the extent's middle height, up through its middle column;
        rows flipped, as a mark's pixel is counted from the top."""
        self.assertEqual(span.edges(BOX, "across", height=1000),
                         ([99.5, 549.5], [299.5, 549.5]))
        self.assertEqual(span.edges(BOX, "up", height=1000),
                         ([199.5, 149.5], [199.5, 949.5]))


def question(**over):
    """What the agent asked, in full: enough to ask it again. No `of` is the
    silhouette, as a scanline with no `--of` runs across the whole figure."""
    return {"extent": "across", "of": None, "anchor": 1700.0,
            "tol": 0.05, "bg_tol": 0.10, **over}


class DrawCase(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.marks = self.tmp / "marks.json"

    def draw(self, box=BOX, k=2.0, **over):
        return span.draw_extent(self.marks, "front.jpg", question(**over), box,
                                height=1000, k=k, text="the body, side to side")


class StoredTest(DrawCase):

    def test_the_span_has_slice_40_s_shape_and_keeps_its_question(self):
        """Nothing that reads a span needs to know which query placed it: the
        same keys, the same author, the same answer pinned between its ends."""
        said = self.draw()
        self.assertTrue(said["ok"], said["lines"])
        drawn, answer = marks_store.load(self.marks)
        self.assertEqual(drawn["ref"], "front.jpg")
        self.assertEqual((drawn["pixel"], drawn["to"]), span.edges(BOX, "across", 1000))
        self.assertEqual(drawn["author"], "agent")
        self.assertEqual(drawn["placed"], "snapped")
        self.assertEqual(drawn["question"], question())
        self.assertEqual(drawn["text"], "the body, side to side")
        self.assertEqual(answer["pixel"], span.midpoint(drawn["pixel"], drawn["to"]))
        self.assertEqual(answer["status"], "open")
        self.assertIn(f"span {drawn['id']}: 400 mm \u00b14 mm", answer["text"])
        self.assertIn("400 mm", said["lines"][0])


class AbsentTest(DrawCase):

    def test_a_colour_the_reference_does_not_contain_is_refused_and_draws_nothing(self):
        """No extent is no edges: there is nothing to snap to, and a span
        across nothing would be a number about a region that is not there."""
        said = self.draw(box=None, of="#00FF00")
        self.assertFalse(said["ok"])
        self.assertIn("#00FF00", said["lines"][0])
        self.assertIn("--tol 0.05", said["lines"][0])
        self.assertEqual(marks_store.load(self.marks), [])


class AgainTest(DrawCase):

    def drawn(self):
        self.draw(extent="up")
        return marks_store.load(self.marks)[0]["id"]

    def test_the_stored_question_re_runs_to_the_same_ends(self):
        mark_id = self.drawn()
        self.assertEqual(span.asked(self.marks, mark_id)["question"], question(extent="up"))
        before = marks_store.load(self.marks)
        said = span.again_extent(self.marks, mark_id, BOX, height=1000)
        self.assertTrue(said["ok"], said["lines"])
        self.assertIn("same ends", said["lines"][0])
        self.assertEqual(marks_store.load(self.marks), before)

    def test_an_extent_that_moved_or_went_is_said_and_nothing_is_rewritten(self):
        mark_id = self.drawn()
        before = marks_store.load(self.marks)
        moved = span.again_extent(self.marks, mark_id, (100, 299, 50, 899), height=1000)
        self.assertFalse(moved["ok"])
        self.assertIn("no longer", moved["lines"][0])
        self.assertIn("99.5", moved["lines"][0])
        gone = span.again_extent(self.marks, mark_id, None, height=1000)
        self.assertFalse(gone["ok"])
        self.assertIn("no longer", gone["lines"][0])
        self.assertEqual(marks_store.load(self.marks), before)


BLENDER = os.environ.get("BLENDER")
BEAKY = ROOT / "project" / "beaky" / "refs"


@unittest.skipUnless(BLENDER, "needs $BLENDER: the reference is read by Blender")
@unittest.skipUnless((BEAKY / "front.jpg").exists() and (BEAKY / "side.jpg").exists(),
                     "needs beaky's front and side references on this machine")
class BeakyTest(unittest.TestCase):
    """ADR 0017's width and depth, as spans: copies of `beaky`'s front and side
    in a space of their own, so nothing of beaky's is written."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.space = cls.tmp / "body"
        cls.env = dict(os.environ, CONTOUR_SPACES=str(cls.tmp),
                       CONTOUR_HOME=str(cls.tmp / "home"),
                       GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        cls.contour("init", "body", cwd=cls.tmp)
        for name in ("front.jpg", "side.jpg"):
            shutil.copy(BEAKY / name, cls.space / "refs" / name)
        (cls.space / "spec.yaml").write_text(
            "model: body\nrevision: 1\ndimensions:\n  height: { value: 1700, tol: 5 }\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    @classmethod
    def contour(cls, *args, cwd=None):
        return subprocess.run([sys.executable, str(ROOT / "contour"), *args],
                              cwd=str(cwd or cls.space), env=cls.env,
                              capture_output=True, text=True, timeout=300)

    def drawn(self):
        store = self.space / "marks.json"
        return [m for m in json.loads(store.read_text())
                if m.get("placed") == "snapped"] if store.exists() else []

    def test_the_silhouettes_read_888_across_the_front_and_597_across_the_side(self):
        refs = self.space / "refs"
        before = {p.name: p.read_bytes() for p in refs.iterdir()}
        for ref, mm in (("front.jpg", 888), ("side.jpg", 597)):
            with self.subTest(ref=ref):
                r = self.contour("measure", f"refs/{ref}", "--silhouette",
                                 "--extent", "across", "the body, side to side")
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                said = self.drawn()[-1]
                k = said["question"]["anchor"] / self.silhouette_px(ref)
                got = span.reading(said["pixel"], said["to"], k)
                self.assertLessEqual(abs(got["mm"] - mm), got["tol"], got)
                self.assertIn(f"{mm} mm", r.stdout)
                again = self.contour("measure", "--again", said["id"])
                self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
                self.assertIn("same ends", again.stdout)
        self.assertEqual({p.name: p.read_bytes() for p in refs.iterdir()}, before)

    def silhouette_px(self, ref):
        r = self.contour("measure", f"refs/{ref}", "--silhouette")
        line = next(l for l in r.stdout.splitlines() if "silhouette" in l)
        y0, y1 = line.split("y ")[1].split(" px")[0].split("..")
        return int(y1) - int(y0) + 1

    def test_a_region_span_runs_up_one_colour_and_asks_again_the_same(self):
        r = self.contour("measure", "refs/front.jpg", "--region", "#3B3F72",
                         "--extent", "up", "the legs, bottom to top")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        said = self.drawn()[-1]
        self.assertEqual(said["question"]["of"], "#3B3F72")
        self.assertEqual(said["pixel"][0], said["to"][0])
        again = self.contour("measure", "--again", said["id"])
        self.assertIn("same ends", again.stdout, again.stdout + again.stderr)

    def test_a_colour_not_in_the_reference_is_refused_and_draws_nothing(self):
        n = len(self.drawn())
        r = self.contour("measure", "refs/front.jpg", "--region", "#00FF00",
                         "--extent", "across", "nothing green")
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("#00FF00", r.stdout)
        self.assertEqual(len(self.drawn()), n)

    def test_no_spelling_of_it_takes_a_pixel_or_mixes_its_queries(self):
        for extra in (("--pixel", "400,700"), ("--to", "560,700"),
                      ("--scanline", "250"), ("--region", "#3B3F72")):
            with self.subTest(extra=extra):
                n = len(self.drawn())
                r = self.contour("measure", "refs/front.jpg", "--silhouette",
                                 "--extent", "across", *extra, "the body")
                self.assertNotEqual(r.returncode, 0, r.stdout)
                self.assertIn(extra[0], r.stdout + r.stderr)
                self.assertEqual(len(self.drawn()), n)


if __name__ == "__main__":
    unittest.main()
