"""A snapped agent span: the agent picks, code places (ADR 0022, decisions 2
and 4; issue 40).

The agent runs a scanline, says which two of the runs it found the question is
about and which distance between them, and the ends land on what was measured.
It never gives a pixel for an end. The span keeps the question that placed it,
so asking again places the same ends.

Everything here but reading the image is out of Blender, so these tests make it
with the runs already found.
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

LEGS = [(400, 429), (560, 589)]
"""Two runs of one scanline, as `cmd_measure` finds them: inclusive pixel
columns, left to right."""


class SnapTest(unittest.TestCase):
    """Picked runs into two ends, on the row the scanline crossed."""

    def test_centres_puts_each_end_on_the_middle_of_its_run(self):
        """Rows are counted from the bottom, as a height reads; a mark's pixel
        is counted from the top, as the canvas draws it."""
        ends = span.snap(LEGS, (1, 2), "centres", row=250, height=1000)
        self.assertEqual(ends, ([414.5, 749], [574.5, 749]))

    def test_each_distance_reads_what_the_scanline_already_reports(self):
        """The scanline prints a centre-to-centre, an inner gap and each run's
        width; a span asking for the same thing must read the same number, or
        the agent would see two answers to one question."""
        (a0, a1), (b0, b1) = LEGS
        for between, px in (("centres", (b0 + b1) / 2 - (a0 + a1) / 2),
                            ("gap", b0 - a1 - 1),
                            ("extent", b1 - a0 + 1)):
            with self.subTest(between=between):
                ends = span.snap(LEGS, (1, 2), between, row=250, height=1000)
                self.assertEqual(span.reading(*ends, 1.0)["px"], px)


def question(**over):
    """What the agent asked, in full: enough to ask it again."""
    return {"scanline": 250.0, "of": "#3B3F72", "runs": [1, 2],
            "between": "centres", "anchor": 1700.0,
            "tol": 0.05, "bg_tol": 0.10, "min_run": 3, **over}


class DrawCase(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.marks = self.tmp / "marks.json"

    def draw(self, k=2.0, found=LEGS, **over):
        return span.draw(self.marks, "front.jpg", question(**over), found,
                         row=250, height=1000, k=k,
                         text="the legs, centre to centre")


class PickTest(DrawCase):

    def test_a_run_the_scanline_did_not_find_is_refused_naming_those_it_did(self):
        """The agent picks from what it was shown; a number outside that is a
        run it imagined, and the refusal hands back the real list."""
        for picked in ([1, 3], [0, 2], [2, 2]):
            with self.subTest(picked=picked):
                said = self.draw(runs=picked)
                self.assertFalse(said["ok"])
                self.assertIn("run 1 x 400..429px", said["lines"][0])
                self.assertIn("run 2 x 560..589px", said["lines"][0])
        self.assertEqual(marks_store.load(self.marks), [])


class StoredTest(DrawCase):

    def test_the_span_is_the_agent_s_snapped_and_keeps_its_question(self):
        said = self.draw()
        self.assertTrue(said["ok"], said["lines"])
        drawn = marks_store.load(self.marks)[0]
        self.assertEqual(drawn["ref"], "front.jpg")
        self.assertEqual((drawn["pixel"], drawn["to"]), ([414.5, 749], [574.5, 749]))
        self.assertEqual(drawn["author"], "agent")
        self.assertEqual(drawn["placed"], "snapped")
        self.assertEqual(drawn["question"], question())
        self.assertEqual(drawn["text"], "the legs, centre to centre")

    def test_the_answer_is_pinned_between_its_ends_with_its_error_bar(self):
        """As a user's span is answered: a finding on the same reference, open,
        in millimetres with the bar one pixel at each end gives it."""
        self.draw()
        drawn, answer = marks_store.load(self.marks)
        self.assertEqual(answer["ref"], "front.jpg")
        self.assertEqual(answer["pixel"], span.midpoint(drawn["pixel"], drawn["to"]))
        self.assertEqual(answer["author"], "agent")
        self.assertEqual(answer["status"], "open")
        self.assertIn(f"span {drawn['id']}: 320 mm \u00b14 mm", answer["text"])


class NoAnchorTest(DrawCase):

    def test_with_no_anchor_the_span_is_drawn_and_answered_in_pixels_saying_why(self):
        """Unlike a user's span, which is refused: the agent asked a question
        of the picture, and where its ends landed is an answer in itself. The
        number it pins is plainly pixels, and says what would make it mm."""
        said = self.draw(k=None, anchor=None)
        self.assertTrue(said["ok"], said["lines"])
        drawn, answer = marks_store.load(self.marks)
        self.assertEqual(drawn["placed"], "snapped")
        self.assertIn("160 px", answer["text"])
        self.assertNotIn("mm", answer["text"])
        self.assertIn("no anchor", answer["text"])
        self.assertIn("anchor span", answer["text"])
        self.assertIn("160 px", said["lines"][0])


class AgainTest(DrawCase):
    """Asking a span's stored question again: the re-runnable basis."""

    def drawn(self):
        self.draw()
        return marks_store.load(self.marks)[0]["id"]

    def again(self, mark_id, found=LEGS, row=250):
        return span.again(self.marks, mark_id, found, row=row, height=1000)

    def test_the_stored_question_is_what_is_asked_again(self):
        mark_id = self.drawn()
        asked = span.asked(self.marks, mark_id)
        self.assertTrue(asked["ok"])
        self.assertEqual((asked["ref"], asked["question"]), ("front.jpg", question()))

    def test_the_same_runs_place_the_same_ends_and_it_says_so(self):
        mark_id = self.drawn()
        before = marks_store.load(self.marks)
        said = self.again(mark_id)
        self.assertTrue(said["ok"], said["lines"])
        self.assertIn("same ends", said["lines"][0])
        self.assertEqual(marks_store.load(self.marks), before)

    def test_runs_that_moved_or_went_are_said_and_nothing_is_rewritten(self):
        """A reference replaced, or an outline that shifted: the span's ends
        are what it was answered on, so they are reported against, never
        quietly moved."""
        mark_id = self.drawn()
        before = marks_store.load(self.marks)
        moved = self.again(mark_id, found=[(400, 429), (580, 609)])
        self.assertFalse(moved["ok"])
        self.assertIn("no longer", moved["lines"][0])
        self.assertIn("594.5", moved["lines"][0])
        gone = self.again(mark_id, found=[(400, 429)])
        self.assertFalse(gone["ok"])
        self.assertIn("no longer", gone["lines"][0])
        self.assertIn("run 1 x 400..429px", gone["lines"][0])
        self.assertEqual(marks_store.load(self.marks), before)

    def test_only_a_snapped_span_has_a_question_to_ask_again(self):
        """A user's span was placed by hand; there is nothing to re-run."""
        user = marks_store.append(self.marks, {"ref": "front.jpg", "pixel": [1, 2],
                                               "to": [9, 2], "text": "by hand"})
        for mark_id in (user["id"], "m404"):
            with self.subTest(mark_id=mark_id):
                said = span.asked(self.marks, mark_id)
                self.assertFalse(said["ok"])
                self.assertIn(mark_id, said["lines"][0])


BLENDER = os.environ.get("BLENDER")
BEAKY = ROOT / "project" / "beaky" / "refs" / "front.jpg"


@unittest.skipUnless(BLENDER, "needs $BLENDER: the reference is read by Blender")
@unittest.skipUnless(BEAKY.exists(), "needs beaky's front reference on this machine")
class BeakyTest(unittest.TestCase):
    """ADR 0022's tracer bullet, on the reference ADR 0017 measured: a copy of
    `beaky`'s front, in a space of its own, so nothing of beaky's is written."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.space = cls.tmp / "legs"
        cls.env = dict(os.environ, CONTOUR_SPACES=str(cls.tmp),
                       CONTOUR_HOME=str(cls.tmp / "home"),
                       GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        cls.contour("init", "legs", cwd=cls.tmp)
        shutil.copy(BEAKY, cls.space / "refs" / "front.jpg")
        (cls.space / "spec.yaml").write_text(
            "model: legs\nrevision: 1\ndimensions:\n  height: { value: 1700, tol: 5 }\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    @classmethod
    def contour(cls, *args, cwd=None):
        return subprocess.run([sys.executable, str(ROOT / "contour"), *args],
                              cwd=str(cwd or cls.space), env=cls.env,
                              capture_output=True, text=True, timeout=300)

    def drawn(self):
        return [m for m in json.loads((self.space / "marks.json").read_text())
                if m.get("placed") == "snapped"]

    def test_the_legs_centre_to_centre_read_168_within_the_error_bar(self):
        refs = self.space / "refs"
        before = {p.name: p.read_bytes() for p in refs.iterdir()}
        r = self.contour("measure", "refs/front.jpg", "--scanline", "250",
                         "--of", "#3B3F72", "--runs", "1,2", "--between", "centres",
                         "the legs, centre to centre")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        span_mark = self.drawn()[-1]
        got = span.reading(span_mark["pixel"], span_mark["to"],
                           1700 / self.silhouette_px())
        self.assertLessEqual(abs(got["mm"] - 168), got["tol"], got)
        self.assertIn("168 mm", r.stdout)
        again = self.contour("measure", "--again", span_mark["id"])
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertIn("same ends", again.stdout)
        self.assertEqual({p.name: p.read_bytes() for p in refs.iterdir()}, before)

    def silhouette_px(self):
        r = self.contour("measure", "refs/front.jpg", "--silhouette")
        line = next(l for l in r.stdout.splitlines() if "silhouette" in l)
        y0, y1 = line.split("y ")[1].split(" px")[0].split("..")
        return int(y1) - int(y0) + 1

    def test_no_spelling_of_the_span_takes_a_pixel_for_an_end(self):
        for extra in (("--pixel", "400,700"), ("--to", "560,700"),
                      ("--from", "400,700"), ("--end", "560,700")):
            with self.subTest(extra=extra):
                n = len(self.drawn()) if (self.space / "marks.json").exists() else 0
                r = self.contour("measure", "refs/front.jpg", "--scanline", "250",
                                 "--of", "#3B3F72", "--runs", "1,2",
                                 "--between", "gap", *extra, "the gap")
                self.assertNotEqual(r.returncode, 0, r.stdout)
                self.assertIn(extra[0], r.stdout + r.stderr)
                after = len(self.drawn()) if (self.space / "marks.json").exists() else 0
                self.assertEqual(after, n)


if __name__ == "__main__":
    unittest.main()
