"""The picture fills its space (issue 133).

The big picture was drawn at its own pixel size and only ever shrunk, so a
reference 490 px wide stayed 490 px on any screen. It is now as large as the
space beside the column allows, whole and in its own shape, and marks stay in
the picture's own pixels, so a click lands where it would at natural size. The
page's arithmetic runs here under node, as the browser gets it: there is no
browser in this suite. How it looks is for eyes on a real console.
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


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class FitTest(unittest.TestCase):

    def run_page(self, names, expression, prelude=""):
        page = PAGE.read_text(encoding="utf-8")
        js = ("".join(function(page, n) for n in names) + prelude
              + f"console.log(JSON.stringify({expression}));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def fit(self, picture, room):
        return self.run_page(["fit"], f"fit({json.dumps(picture)}, {json.dumps(room)})")

    def test_a_small_reference_is_enlarged_to_the_space_whole_and_in_its_shape(self):
        """490 by 368 in a room 1200 by 800: height runs out first."""
        said = self.fit({"width": 490, "height": 368}, {"width": 1200, "height": 800})
        self.assertEqual(said["height"], 800)
        self.assertAlmostEqual(said["width"] / said["height"], 490 / 368, places=2)

    def test_a_wide_picture_is_held_by_the_width(self):
        """The sheet, wider than it is tall, in a tall narrow room."""
        said = self.fit({"width": 2000, "height": 1000}, {"width": 600, "height": 900})
        self.assertEqual((said["width"], said["height"]), (600, 300))

    def test_a_click_on_an_enlarged_picture_lands_on_the_same_picture_pixel(self):
        """Pixel (245, 184) of a 490 by 368 reference, clicked where it is
        drawn at natural size and where it is drawn fitted to 1065 by 800."""
        def clicked(size, left=12, top=40):
            drawn = self.fit({"width": 490, "height": 368}, {"width": size, "height": size})
            sx, sy = drawn["width"] / 490, drawn["height"] / 368
            prelude = ("const cv = { width: 490, height: 368, getBoundingClientRect: () =>"
                       f" ({{ left: {left}, top: {top}, width: {drawn['width']},"
                       f" height: {drawn['height']} }}) }};\n")
            event = {"clientX": left + 245 * sx, "clientY": top + 184 * sy}
            return self.run_page(["at"], f"at({json.dumps(event)})", prelude)
        self.assertEqual(clicked(490), [245, 184])
        self.assertEqual(clicked(1065), [245, 184])


class PageTest(unittest.TestCase):
    """The wiring, read off the page's source as `test_questions` reads it."""

    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")

    def test_the_picture_is_fitted_to_its_room_on_load_and_whenever_the_room_changes(self):
        """The room is the space beside the column under the strip: a window
        resized, or the column dragged (issue 134), changes it. The sheet, the
        perspective and every reference are the one canvas, so all fit."""
        self.assertIn('<div id="room"><div id="wrap"><canvas id="sheet">', self.page)
        refit = function(self.page, "refit")
        self.assertIn("fit({ width: cv.width, height: cv.height }", refit)
        self.assertIn("cv.style.width", refit)
        self.assertIn("cv.style.height", refit)
        self.assertIn("new ResizeObserver(refit).observe(room)", self.page)
        loaded = self.page.split("img.onload = () => {", 1)[1].split("};", 1)[0]
        self.assertIn("refit()", loaded)


if __name__ == "__main__":
    unittest.main()
