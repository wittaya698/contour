"""A span is moved by its ends, and you see it move (issue 132).

*Let me move it* once changed a hint line and waited for a whole new span,
drawn blind. Now Claude's span keeps its place with a handle on each end, on
the big picture and on the card's zoom, and the end that is wrong is dragged.
The page's decisions are small functions of its script, run here under node as
the browser gets them: there is no browser in this suite. How they look is for
eyes on a real console.
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

PICTURE = {"width": 1600, "height": 1200}
CARD = {"width": 536, "height": 320}


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class MovedTest(unittest.TestCase):

    def run_page(self, names, expression, **given):
        page = PAGE.read_text(encoding="utf-8")
        js = ("".join(function(page, n) for n in names)
              + "".join(f"const {k} = {json.dumps(v)};\n" for k, v in given.items())
              + f"console.log(JSON.stringify({expression}));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_a_point_on_the_card_is_the_same_picture_pixel_as_on_the_big_picture(self):
        """The card is the place for fine work, so a drag there has to land
        where the same drag on the big picture would: through the zoom's own
        framing, not a second guess at it."""
        a, b = [700, 500], [900, 540]
        frame = self.run_page(["crop"], "crop(a, b, picture, card)",
                              a=a, b=b, picture=PICTURE, card=CARD)
        # Where the two ends are drawn on the card, carried back to the picture.
        drawn = [[(p[0] - frame["x"]) * frame["k"], (p[1] - frame["y"]) * frame["k"]] for p in (a, b)]
        back = self.run_page(["crop", "fromCard"],
                             "drawn.map(p => fromCard(p, crop(a, b, picture, card)))",
                             a=a, b=b, picture=PICTURE, card=CARD, drawn=drawn)
        self.assertEqual(back, [a, b])

    def test_the_framing_keeps_the_span_inside_the_picture_and_unstretched(self):
        """Near a corner the crop slides to stay on the picture; it is the
        card's shape, so a circle stays a circle."""
        frame = self.run_page(["crop"], "crop(a, b, picture, card)",
                              a=[5, 5], b=[60, 5], picture=PICTURE, card=CARD)
        self.assertEqual((frame["x"], frame["y"]), (0, 0))
        self.assertAlmostEqual(frame["w"] / frame["h"], CARD["width"] / CARD["height"])

    def grab(self, point, reach=12, ends=([100, 100], [130, 100])):
        return self.run_page(["grab"], "grab(ends, point, reach)",
                             ends=list(ends), point=point, reach=reach)

    def test_a_press_near_an_end_takes_that_end(self):
        self.assertEqual(self.grab([103, 98]), 0)
        self.assertEqual(self.grab([125, 104]), 1)

    def test_between_two_close_ends_the_nearer_is_taken(self):
        """Both are in reach of a press in the middle-ish: the one nearer wins,
        so a short span can still have either end moved."""
        self.assertEqual(self.grab([113, 100], reach=20), 0)
        self.assertEqual(self.grab([117, 100], reach=20), 1)

    def test_a_press_away_from_both_ends_takes_nothing(self):
        """Out of reach, a press is not a handle: nothing moves."""
        self.assertIsNone(self.grab([115, 140]))

    def test_save_sends_the_moved_end_and_the_other_where_claude_put_it(self):
        """A drag is many moves; the last is where the end is. Save is the
        correction `/correct` already takes, so the server does not change."""
        said = self.run_page(
            ["moved", "correction"],
            "(() => { let ends = [mark.pixel, mark.to];"
            " for (const p of path) ends = moved(ends, 1, p);"
            " return { body: correction(mark, ends), mark }; })()",
            mark={"id": "m4", "pixel": [100, 100], "to": [130, 100]},
            path=[[131, 101], [134, 103], [136, 102]])
        self.assertEqual(said["body"], {"id": "m4", "pixel": [100, 100], "to": [136, 102]})
        self.assertEqual(said["mark"]["to"], [130, 100],
                         "Claude's span is untouched until Save: Cancel puts nothing back")

    def test_the_span_being_moved_is_the_cards_question(self):
        """The list's *correct* can start a move on a span the card is not on,
        a skipped one; Save and Cancel are on the card, so the card asks it."""
        marks = [{"id": "m1", "ref": "a.png", "pixel": [1, 1], "to": [9, 1], "author": "agent",
                  "status": "open", "text": "seat"},
                 {"id": "m2", "ref": "a.png", "pixel": [1, 5], "to": [9, 5], "author": "agent",
                  "status": "open", "text": "back"}]
        said = self.run_page(["spanState", "foundation", "named", "asking"], "asking(marks, new Set(['m2']), marks[1])",
                             marks=marks)
        self.assertEqual((said["mark"]["id"], said["number"], said["open"]), ("m2", "span 2", 2))


class PageTest(unittest.TestCase):
    """The wiring, read off the page's source as `test_questions` reads it."""

    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")
        self.card = self.page.split('<section id="questions"', 1)[1].split("</section>", 1)[0]

    def script(self, name):
        self.assertEqual(self.page.count(f"function {name}("), 1)
        return function(self.page, name)

    def handler(self, cls):
        """The whole handler the card wires to a button, up to the next one."""
        wired = self.script("askedAnswers")
        return wired.split(f"on('{cls}'", 1)[1].split("\n  on(", 1)[0]

    def test_save_and_cancel_take_the_answers_place_while_a_span_moves(self):
        for part in ('class="save"', 'class="cancel"'):
            self.assertIn(part, self.card)
        asked = self.script("questions")
        self.assertIn("'.answers').hidden = !!(moving || rejecting)", asked)   # and while a reason is typed (issue 143)
        self.assertIn("'.moving').hidden = !moving", asked)

    def test_save_records_the_correction(self):
        self.assertIn("answered('/correct', correction(moving.mark, moving.ends))",
                      self.handler(".save"))

    def test_cancel_sends_nothing_and_the_question_stands(self):
        cancel = self.handler(".cancel")
        self.assertIn("moving = null", cancel)
        self.assertNotIn("ask(", cancel)
        self.assertNotIn("answered(", cancel)
        self.assertNotIn("skipped", cancel)
        self.assertIn("draw()", cancel, "the span is drawn back where Claude put it")

    def test_a_new_span_is_drawn_while_the_mouse_is_down(self):
        """The same missing feedback as a moved end: on a reference, the line
        from where the press went down follows the mouse."""
        page = self.page
        self.assertIn("if (down && sketch) { sketch = [down, at(e)]; draw(); return; }", page)
        self.assertIn("ctx.moveTo(sketch[0][0], sketch[0][1]);", self.script("draw"))

    def test_while_a_span_moves_a_press_off_its_handles_marks_nothing(self):
        self.assertIn("down = showing && !moving ? at(e) : null;", self.page)
        self.assertIn("if (moving) { down = null; return; }", self.page)


class CursorTest(unittest.TestCase):

    def test_over_a_handle_a_hand_and_holding_one_a_closed_hand(self):
        css = rules()
        for sel, cursor in (("#sheet.grab", "grab"), ("#questions .zoom.grab", "grab"),
                            ("#sheet.grabbing", "grabbing"),
                            ("#questions .zoom.grabbing", "grabbing")):
            self.assertEqual(css.get(sel, {}).get("cursor"), cursor, sel)


if __name__ == "__main__":
    unittest.main()
