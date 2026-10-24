"""The span being asked about is the one you see (issue 131).

The card zoomed into one agent span and nothing on the big picture pointed
back to it. The page's decisions about the asked span are small functions of
its script, run here under node as the browser gets them: there is no browser
in this suite. How they look is for eyes on a real console.
"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.canvas import PAGE             # noqa: E402
from test_found import function         # noqa: E402
from test_tiers import rules            # noqa: E402


def span(mark_id, ref="megaphone.png", **more):
    """An agent span waiting on an answer, as `/marks` serves one."""
    return {"id": mark_id, "ref": ref, "pixel": [10, 10], "to": [60, 10],
            "author": "agent", "status": "open", "text": "red end cap, across", **more}


def note(mark_id, **more):
    """A plain mark on the sheet: not a question."""
    return {"id": mark_id, "pixel": [5, 5], "view": "front", "text": "too thin",
            "author": "user", "status": "open", **more}


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class AskedTest(unittest.TestCase):

    def run_page(self, names, expression, **given):
        page = PAGE.read_text(encoding="utf-8")
        js = ("".join(function(page, n) for n in names)
              + "".join(f"const {k} = {json.dumps(v)};\n" for k, v in given.items())
              + f"console.log(JSON.stringify({expression}));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def asking(self, marks, skipped=()):
        return self.run_page(["spanState", "foundation", "named", "asking"], "asking(marks, new Set(skipped))",
                             marks=marks, skipped=list(skipped))

    def test_the_card_names_the_span_by_the_number_on_its_badge(self):
        """The badge is the mark's place in the list, so the card counts the
        same way: the two can never name different spans."""
        marks = [note("m1"), span("m2", answer="adopted"), note("m3"), span("m4"), span("m5")]
        said = self.asking(marks)
        self.assertEqual(said["mark"]["id"], "m4")
        self.assertEqual(said["number"], "span 4")
        self.assertEqual(said["open"], 2)

    def test_a_skipped_span_is_passed_over_and_still_counted(self):
        said = self.asking([span("m1"), span("m2")], skipped=["m1"])
        self.assertEqual((said["mark"]["id"], said["number"], said["open"]), ("m2", "span 2", 2))

    def test_nothing_is_asked_when_every_question_is_answered_or_skipped(self):
        self.assertIsNone(self.asking([span("m1", answer="adopted"), note("m2")])["mark"])
        self.assertIsNone(self.asking([span("m1")], skipped=["m1"])["mark"])

    def parked(self, marks, parked, skipped=()):
        return self.run_page(["spanState", "foundation", "named", "asking"],
                             "asking(marks, new Set(skipped), null, parked)",
                             marks=marks, skipped=list(skipped), parked=parked)

    def test_at_a_park_the_card_asks_only_what_the_run_waits_on_and_counts_it(self):
        """*1 of 2*: the spans the run waits on, and no other question
        (ADR 0035, decision 3; issue 158)."""
        marks = [span("m1", placed="snapped"), span("m2", placed="by eye"),
                 span("m3", placed="by eye")]
        said = self.parked(marks, ["m2", "m3"])
        self.assertEqual((said["mark"]["id"], said["of"]), ("m2", "1 of 2"))
        marks[1]["answer"] = "adopted"
        said = self.parked(marks, ["m2", "m3"])
        self.assertEqual((said["mark"]["id"], said["of"]), ("m3", "2 of 2"))
        self.assertIsNone(self.parked(marks, ["m2", "m3"], skipped=["m3"])["mark"])

    def test_with_no_park_there_is_no_count(self):
        self.assertIsNone(self.asking([span("m1")])["of"])

    def stroke(self, mark, asked):
        return self.run_page(["stroke"], "stroke(mark, asked)", mark=mark, asked=asked)

    def test_the_asked_span_is_drawn_heavier_and_the_others_fade(self):
        asked = span("m4")
        heavy = self.stroke(asked, asked)
        other = self.stroke(span("m5"), asked)
        self.assertGreater(heavy["width"], other["width"])
        self.assertFalse(heavy["faded"])
        self.assertTrue(other["faded"])
        self.assertFalse(heavy["dashed"])

    def test_only_the_asked_span_and_its_own_reading_stay_bright(self):
        """Readings are pins, and bright pins outshone the span being asked
        (seen on a real reference). Its own reading carries the number the
        card shows, so it stays; every other mark on the picture fades."""
        asked = span("m4", reading="m9")
        self.assertFalse(self.stroke(note("m9", ref="megaphone.png"), asked)["faded"])
        self.assertTrue(self.stroke(note("m7", ref="megaphone.png"), asked)["faded"])

    def test_an_asked_span_placed_by_eye_stays_broken(self):
        """ADR 0022, decision 3: a number nothing measured never passes for
        one that was, not even while it is the one being asked."""
        asked = span("m4", placed="by eye")
        self.assertTrue(self.stroke(asked, asked)["dashed"])

    def test_with_no_question_every_span_is_drawn_as_it_always_was(self):
        plain = self.stroke(span("m4"), None)
        self.assertEqual(plain, {"width": 1, "dashed": False, "faded": False})
        self.assertTrue(self.stroke(span("m4", placed="by eye"), None)["dashed"])

    def follow(self, showing, asked, followed=None, busy=False):
        return self.run_page(["follow"], "follow(showing, asked, followed, busy)",
                             showing=showing, asked=asked, followed=followed, busy=busy)

    def test_a_question_on_another_picture_brings_that_picture_up(self):
        said = self.follow(None, span("m4", ref="megaphone.png"))
        self.assertEqual(said, {"show": "megaphone.png", "followed": "m4"})

    def test_a_question_already_followed_lets_the_person_look_elsewhere(self):
        """They went back to the sheet on purpose; the same question does not
        pull them away from it again."""
        said = self.follow(None, span("m4"), followed="m4")
        self.assertEqual(said, {"show": None, "followed": "m4"})

    def test_a_question_on_the_picture_already_showing_switches_nothing(self):
        said = self.follow("megaphone.png", span("m4"))
        self.assertEqual(said, {"show": None, "followed": "m4"})

    def test_a_person_part_way_through_is_never_moved_and_is_moved_after(self):
        """A mark being typed, or a drag held: the switch waits, and happens
        once they are done, because the question is still not followed."""
        held = self.follow(None, span("m4"), followed="m3", busy=True)
        self.assertEqual(held, {"show": None, "followed": "m3"})
        after = self.follow(None, span("m4"), followed=held["followed"])
        self.assertEqual(after, {"show": "megaphone.png", "followed": "m4"})

    def test_no_question_switches_nothing(self):
        self.assertEqual(self.follow("megaphone.png", None, followed="m4"),
                         {"show": None, "followed": "m4"})


class CursorTest(unittest.TestCase):

    def test_the_cursor_says_whether_a_click_marks(self):
        """A crosshair where a click marks or draws; the perspective is to look
        at and never to mark, so it has none. Buttons point, from `look.css`."""
        css = rules()
        self.assertEqual(css["canvas"]["cursor"], "crosshair")
        self.assertEqual(css["#sheet.look"]["cursor"], "default")
        page = PAGE.read_text(encoding="utf-8")
        shown = page.split("function show(", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("cv.classList.toggle('look', name === PERSP)", shown)
        self.assertIn("button { cursor: pointer; }", (ROOT / "lib" / "look.css").read_text())


if __name__ == "__main__":
    unittest.main()
