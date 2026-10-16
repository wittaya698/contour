"""The perspective beside the sheet (ADR 0005, amended 2026-10-16).

The sheet holds four flat views; the render draws the perspective as a picture
of its own. The page shows it to look at, and the host says whether there is
one, so a space whose last sheet predates it offers no button that shows
nothing.
"""
import shutil
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.canvas import Canvas
from client import get, open_url

PNG = b"\x89PNG\r\n\x1a\n"


class PerspTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "sheet.png").write_bytes(PNG + b"sheet")
        self.persp = self.tmp / "out" / "persp.png"

    def canvas(self, **kw):
        canvas = Canvas(sheet=self.tmp / "sheet.png", marks=self.tmp / "marks.json", **kw)
        self.addCleanup(canvas.stop)
        canvas.start()
        return canvas

    def test_a_drawn_perspective_is_served_and_said_to_be_there(self):
        self.persp.parent.mkdir()
        self.persp.write_bytes(PNG + b"persp")
        canvas = self.canvas(persp=self.persp)
        self.assertTrue(get(canvas, "/sheet.json")[1]["persp"])
        with open_url(canvas, "/persp.png", timeout=5) as r:
            self.assertEqual(r.headers["Content-Type"], "image/png")
            self.assertEqual(r.read(), PNG + b"persp")

    def test_a_sheet_with_no_perspective_beside_it_says_so(self):
        """An older sheet, or a host that serves none: no button, no picture."""
        for canvas in (self.canvas(persp=self.persp), self.canvas()):
            self.assertFalse(get(canvas, "/sheet.json")[1]["persp"])
            with self.assertRaises(urllib.error.HTTPError) as no:
                open_url(canvas, "/persp.png", timeout=5)
            self.assertEqual(no.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
