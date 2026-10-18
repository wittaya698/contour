"""The column is as wide as you set it (issue 134).

The column was meant to be 300 px and had no hard limit: the card's 536 px
zoom or a wide transcript line pushed it out, and the picture shrank to make
room. A divider now sets its width, kept per browser as a viewer's
convenience, bounded so neither side becomes unusable, and double-click puts
it back. The page's arithmetic runs here under node, as the browser gets it:
there is no browser in this suite. How it looks is for eyes on a real console.
"""
import json
import re
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


def limits(page):
    """The page's own constants for the column, so a test reads them and does
    not restate them."""
    found = re.findall(r"^const COLUMN_\w+ = .*$", page, re.M)
    assert found, "the page names no COLUMN_ constants"
    return "\n".join(found) + "\n"


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class WidthTest(unittest.TestCase):

    def run_page(self, names, expression, prelude=""):
        page = PAGE.read_text(encoding="utf-8")
        js = (limits(page) + "".join(function(page, n) for n in names) + prelude
              + f"console.log(JSON.stringify({expression}));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_a_width_inside_the_bounds_is_the_width_set(self):
        self.assertEqual(self.run_page(["bounded"], "bounded(480, 1400)"), 480)

    def test_neither_side_goes_below_its_minimum(self):
        """Dragged hard left the picture keeps its minimum; hard right the
        column keeps its own. A window too small for both keeps the column,
        which holds the controls."""
        said = self.run_page(["bounded"],
                             "[bounded(10, 1400), bounded(1390, 1400), bounded(500, 300),"
                             " COLUMN_MIN, PICTURE_MIN]")
        low, high, cramped, column_min, picture_min = said
        self.assertEqual(low, column_min)
        self.assertEqual(high, 1400 - picture_min)
        self.assertEqual(cramped, column_min)

    def test_a_width_set_is_read_back_after_a_reload(self):
        said = self.run_page(
            ["kept", "keep"], "(() => { keep(store, 480); return kept(store); })()",
            "const box = {}; const store = { getItem: k => box[k] ?? null,"
            " setItem: (k, v) => { box[k] = String(v); }, removeItem: k => { delete box[k]; } };\n")
        self.assertEqual(said, 480)

    def test_a_browser_that_keeps_nothing_starts_from_the_default(self):
        """A private window, blocked site data, or a value that is not a
        width: nothing is read back and nothing throws, so the column takes
        the default."""
        said = self.run_page(
            ["kept", "keep", "forget"],
            "[kept(refusing), (keep(refusing, 480), forget(refusing), 'still here'),"
            " kept(garbled), kept(empty)]",
            "const refusing = { getItem() { throw new Error('denied'); },"
            " setItem() { throw new Error('denied'); }, removeItem() { throw new Error('denied'); } };\n"
            "const garbled = { getItem: () => 'wide' };\n"
            "const empty = { getItem: () => null };\n")
        self.assertEqual(said, [None, "still here", None, None])


class PageTest(unittest.TestCase):
    """The wiring, read off the page's source as `test_questions` reads it."""

    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")

    def test_a_divider_stands_between_the_picture_and_the_column(self):
        between = self.page.split('<p id="build"></p>', 1)[1].split("<aside>", 1)[0]
        self.assertIn('<div id="divider"', between)
        self.assertIn('role="separator"', between)

    def test_dragging_the_divider_sets_the_width_and_keeps_it(self):
        """The width is where the mouse is from the right edge, bounded. The
        picture's room changes with it, and 133's observer refits the picture."""
        column = function(self.page, "column")
        self.assertIn("aside.style.width = bounded(", column)
        self.assertIn("divider.addEventListener('mousedown'", self.page)
        dragged = self.page.split("divider.addEventListener('mousedown'", 1)[1]
        self.assertIn("column(", dragged)
        self.assertIn("keep(storage(), ", dragged)

    def test_double_click_puts_the_default_back(self):
        reset = self.page.split("divider.addEventListener('dblclick'", 1)[1].split("});", 1)[0]
        self.assertIn("aside.style.width = ''", reset)
        self.assertIn("forget(storage())", reset)

    def test_a_kept_width_is_used_on_load_and_rebounded_when_the_window_changes(self):
        self.assertIn("const width = kept(storage());", self.page)
        self.assertIn("window.addEventListener('resize'", self.page)


class StyleTest(unittest.TestCase):

    def setUp(self):
        self.css = rules()

    def test_nothing_in_the_column_widens_it(self):
        """The width is set, not grown into: the column neither grows nor
        shrinks as a flex item, a long word breaks, and a wide line scrolls
        inside the column rather than pushing it out."""
        aside = self.css["aside"]
        self.assertEqual(aside.get("flex"), "none")
        self.assertEqual(aside.get("overflow-wrap"), "anywhere")
        self.assertEqual(aside.get("overflow-x"), "hidden")

    def test_the_divider_says_it_can_be_dragged(self):
        self.assertEqual(self.css["#divider"].get("cursor"), "col-resize")
        self.assertEqual(self.css["body.resizing"].get("cursor"), "col-resize",
                         "the cursor holds while the mouse is off the divider")
        self.assertEqual(self.css["body.resizing"].get("user-select"), "none")

    def test_a_two_digit_mark_number_is_not_cut_off(self):
        """Marks 10 and up had their numbers clipped at the column's left edge."""
        self.assertEqual(self.css["#list"].get("padding-left"), "2.4em")

    def test_the_cards_zoom_grows_and_shrinks_with_the_column(self):
        zoom = self.css["#questions .zoom"]
        self.assertEqual(zoom.get("width"), "100%")
        self.assertEqual(self.css["canvas"].get("height"), "auto", "and keeps its shape")


if __name__ == "__main__":
    unittest.main()
