"""A by-eye agent span: two free ends, and a number that says so (ADR 0022,
decisions 3 and 6; issue 44).

Where nothing snaps — a photograph of a real object, a soft gradient — the
agent may place a span's ends itself. Everything that shows such a span says it
was placed by eye, and until the user answers it, its number is not one the
agent may propose.

Everything here but reading the image is out of Blender, so these tests make it
with the scale already worked out.
"""
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


QUESTION = {"extent": "across", "of": None, "anchor": 1700.0,
            "tol": 0.05, "bg_tol": 0.10}


class ByEyeCase(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.marks = self.tmp / "marks.json"

    def by_eye(self, ends=([100, 400], [300, 400]), k=2.0):
        return span.by_eye(self.marks, "chair.jpg", ends, k, "the seat, side to side")

    def last(self):
        return [m for m in marks_store.load(self.marks) if m.get("to")][-1]["id"]

    def snapped(self):
        span.pinned(self.marks, "front.jpg", QUESTION,
                    ([99.5, 549.5], [299.5, 549.5]), 2.0, "the body")
        return self.last()

    def eyed(self):
        self.by_eye()
        return self.last()


class StoredTest(ByEyeCase):

    def test_the_span_is_the_agent_s_by_eye_and_has_no_question(self):
        said = self.by_eye()
        self.assertTrue(said["ok"], said["lines"])
        drawn = marks_store.load(self.marks)[0]
        self.assertEqual(drawn["ref"], "chair.jpg")
        self.assertEqual((drawn["pixel"], drawn["to"]), ([100, 400], [300, 400]))
        self.assertEqual(drawn["author"], "agent")
        self.assertEqual(drawn["placed"], "by eye")
        self.assertNotIn("question", drawn)
        self.assertEqual(drawn["scale"], 2.0)

    def test_the_answer_says_its_error_bar_covers_the_arithmetic_not_the_placing(self):
        """The bar is a pixel at each end, which is honest about the
        arithmetic and silent about where the agent put the ends. Silence
        there would read as cover, so the answer says it."""
        said = self.by_eye()
        drawn, answer = marks_store.load(self.marks)
        self.assertIn(f"span {drawn['id']}: 400 mm ±4 mm", answer["text"])
        for words in ("by eye", "not the placing"):
            with self.subTest(words=words):
                self.assertIn(words, answer["text"])
                self.assertIn(words, said["lines"][0])

    def test_with_no_scale_it_still_says_so(self):
        self.by_eye(k=None)
        answer = marks_store.load(self.marks)[1]["text"]
        self.assertIn("200 px", answer)
        self.assertIn("by eye", answer)

    def test_there_is_no_question_to_ask_again_and_the_refusal_says_by_eye(self):
        self.by_eye()
        mark_id = marks_store.load(self.marks)[0]["id"]
        said = span.asked(self.marks, mark_id)
        self.assertFalse(said["ok"])
        self.assertIn("by eye", said["lines"][0])

    def test_two_ends_on_one_pixel_are_refused_and_nothing_is_written(self):
        said = self.by_eye(ends=([5, 5], [5, 5]))
        self.assertFalse(said["ok"])
        self.assertEqual(marks_store.load(self.marks), [])


class StandingTest(ByEyeCase):
    """Whether a span's number may go into a proposal (ADR 0022, decision 6): asked of
    the span, and said in a line the agent reads before it proposes."""

    def test_an_unanswered_snapped_span_may_be_proposed_as_the_agent_s_own(self):
        mark_id = self.snapped()
        said = span.standing(self.marks, mark_id)
        self.assertTrue(said["ok"], said["lines"])
        self.assertTrue(said["proposable"])
        self.assertIn("the agent's own reading", said["lines"][0])
        self.assertIn("400 mm", "\n".join(said["lines"]))

    def test_an_unanswered_by_eye_span_may_not_be_proposed(self):
        mark_id = self.eyed()
        said = span.standing(self.marks, mark_id)
        self.assertTrue(said["ok"], said["lines"])
        self.assertFalse(said["proposable"])
        self.assertIn("by eye", said["lines"][0])
        self.assertIn("may not be proposed", said["lines"][0])

    def test_once_the_user_adopts_or_corrects_it_it_may(self):
        adopted, corrected = self.eyed(), self.eyed()
        marks_store.adopt(self.marks, adopted)
        marks_store.correct(self.marks, corrected, [100, 400], [350, 400],
                            span.reads([100, 400], [350, 400], 2.0))
        for mark_id, number in ((adopted, "400 mm"), (corrected, "500 mm")):
            with self.subTest(mark=mark_id):
                said = span.standing(self.marks, mark_id)
                self.assertTrue(said["proposable"], said["lines"])
                self.assertIn("the user's", said["lines"][0])
                self.assertIn(number, "\n".join(said["lines"]))

    def test_a_rejected_span_may_not_be_proposed_whoever_placed_it(self):
        for mark_id in (self.snapped(), self.eyed()):
            marks_store.reject(self.marks, mark_id, "the arm, not the seat")
            with self.subTest(mark=mark_id):
                said = span.standing(self.marks, mark_id)
                self.assertFalse(said["proposable"])
                self.assertIn("rejected", said["lines"][0])

    def test_asking_writes_nothing(self):
        ids = (self.snapped(), self.eyed())
        before = marks_store.load(self.marks)
        for mark_id in ids:
            span.standing(self.marks, mark_id)
        self.assertEqual(marks_store.load(self.marks), before)

    def test_what_is_not_a_span_is_refused_by_id(self):
        note = marks_store.append(self.marks, {"ref": "front.jpg", "pixel": [1, 2],
                                               "text": "a pin, not a span"})
        for mark_id in (note["id"], "m404"):
            with self.subTest(mark=mark_id):
                said = span.standing(self.marks, mark_id)
                self.assertFalse(said["ok"])
                self.assertIn(mark_id, said["lines"][0])


class StandingCommandTest(ByEyeCase):
    """`contour measure --standing ID`: the same answer, from the command the
    agent measures with. It reads `marks.json` only, so no Blender."""

    def contour(self, *args):
        (self.tmp / ".contour").mkdir(exist_ok=True)
        (self.tmp / ".contour" / "project").write_text("toolkit: stub\n")
        return subprocess.run([sys.executable, str(ROOT / "contour"), *args],
                              cwd=str(self.tmp), env=dict(os.environ),
                              capture_output=True, text=True, timeout=60)

    def test_it_says_whether_the_number_may_be_proposed(self):
        snapped, eyed = self.snapped(), self.eyed()
        may = self.contour("measure", "--standing", snapped)
        self.assertEqual(may.returncode, 0, may.stdout + may.stderr)
        self.assertIn("the agent's own reading", may.stdout)
        not_yet = self.contour("measure", "--standing", eyed)
        self.assertEqual(not_yet.returncode, 0, not_yet.stdout + not_yet.stderr)
        self.assertIn("may not be proposed", not_yet.stdout)

    def test_a_mark_that_is_not_a_span_fails(self):
        r = self.contour("measure", "--standing", "m404")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("m404", r.stdout)


class PageTest(ByEyeCase):

    def test_the_canvas_has_a_look_for_a_by_eye_span(self):
        """No JS runs here, so this proves the page's half: it knows the
        label and has a style for it. What it looks like is a HITL check."""
        from lib.canvas import Canvas
        from client import open_url
        canvas = Canvas(sheet=self.tmp / "sheet.png", marks=self.marks)
        self.addCleanup(canvas.stop)
        canvas.start()
        with open_url(canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn("'by eye'", page)
        self.assertIn(".byeye", page)


BLENDER = os.environ.get("BLENDER")
BEAKY = ROOT / "project" / "beaky" / "refs" / "front.jpg"


@unittest.skipUnless(BLENDER, "needs $BLENDER: the reference is read by Blender")
@unittest.skipUnless(BEAKY.exists(), "needs beaky's front reference on this machine")
class ByEyeCommandTest(unittest.TestCase):
    """`contour measure <ref> --by-eye --from X,Y --to X,Y`, on a copy of
    `beaky`'s front in a space of its own, so nothing of beaky's is written."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.space = cls.tmp / "eyed"
        cls.env = dict(os.environ, CONTOUR_SPACES=str(cls.tmp),
                       CONTOUR_HOME=str(cls.tmp / "home"),
                       GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        cls.contour("init", "eyed", cwd=cls.tmp)
        shutil.copy(BEAKY, cls.space / "refs" / "front.jpg")
        (cls.space / "spec.yaml").write_text(
            "model: eyed\nrevision: 1\ndimensions:\n  height: { value: 1700, tol: 5 }\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    @classmethod
    def contour(cls, *args, cwd=None):
        return subprocess.run([sys.executable, str(ROOT / "contour"), *args],
                              cwd=str(cwd or cls.space), env=cls.env,
                              capture_output=True, text=True, timeout=300)

    def stored(self):
        found = self.space / "marks.json"
        return marks_store.load(found) if found.exists() else []

    def test_two_free_ends_make_a_by_eye_span_answered_in_mm(self):
        """Rows count from the bottom, as every height `contour measure`
        reports does; the record counts from the top, as the canvas draws."""
        refs = self.space / "refs"
        before = {p.name: p.read_bytes() for p in refs.iterdir()}
        r = self.contour("measure", "refs/front.jpg", "--by-eye",
                         "--from", "400,250", "--to", "560,250", "the beak, by eye")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        drawn = [m for m in self.stored() if m.get("placed") == "by eye"][-1]
        height = int(r.stdout.split("x", 1)[1].split("px")[0])
        self.assertEqual((drawn["pixel"], drawn["to"]),
                         ([400, height - 1 - 250], [560, height - 1 - 250]))
        self.assertNotIn("question", drawn)
        self.assertIn(" mm ", r.stdout)
        self.assertIn("not the placing", r.stdout)
        self.assertEqual({p.name: p.read_bytes() for p in refs.iterdir()}, before)

    def test_an_end_given_as_a_pixel_without_by_eye_is_refused(self):
        """The by-eye spelling is its own, so a free end is never placed by
        accident: not on a bare query, and not alongside a snapped one."""
        for args in (("--from", "400,250", "--to", "560,250", "the beak"),
                     ("--by-eye", "--from", "400,250", "--to", "560,250",
                      "--extent", "across", "--silhouette", "the beak"),
                     ("--by-eye", "--from", "400,250", "the beak"),
                     ("--by-eye", "--from", "400,250", "--to", "99999,250", "the beak")):
            with self.subTest(args=args):
                n = len(self.stored())
                r = self.contour("measure", "refs/front.jpg", *args)
                self.assertNotEqual(r.returncode, 0, r.stdout)
                self.assertEqual(len(self.stored()), n)


if __name__ == "__main__":
    unittest.main()
