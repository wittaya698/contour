"""Part identity: a click lands on a named part, or on nothing at all.

The server is the authority here. The page keeps its own copy of the mask to
name a part under the cursor, but what a mark *records* is resolved from the
mask on disk, so there is one answer and it is the one these tests read.
"""
import json
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import mask as mask_store
from lib.canvas import Canvas

from client import get, open_url, post


class PartsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.sheet = self.tmp / "sheet.png"
        self.sheet.write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")
        self.marks = self.tmp / "marks.json"
        self.mask = self.tmp / "mask.png"
        self.parts = self.tmp / "parts.json"

    def paint(self, rows, parts):
        """A mask as `contour render` leaves one: one index per pixel, 0 for
        background, and a table saying what each index is called."""
        mask_store.write(self.mask, rows)
        self.parts.write_text(json.dumps(parts))

    def open_canvas(self):
        canvas = Canvas(sheet=self.sheet, marks=self.marks,
                        mask=self.mask, parts=self.parts)
        self.addCleanup(canvas.stop)
        canvas.start()
        return canvas

    def test_a_click_on_a_part_records_that_parts_name(self):
        self.paint([[0, 0, 0, 0],
                    [0, 1, 1, 0],
                    [0, 1, 1, 0],
                    [0, 0, 0, 0]], {"1": "plinth"})
        canvas = self.open_canvas()
        _, mark = post(canvas, "/marks",
                       {"view": "front", "pixel": [2, 1], "text": "too tall"})
        self.assertEqual(mark["part"], "plinth")
        self.assertEqual(json.loads(self.marks.read_text())[0]["part"], "plinth")

    def test_a_click_on_background_records_no_part_at_all(self):
        """Nearest-centroid was rejected in ADR 0018 precisely here: `this gap
        is too wide` is a remark about the gap, not about whatever is beside
        it. A pixel no part owns names no part."""
        self.paint([[1, 1, 0, 0],
                    [1, 1, 0, 0],
                    [0, 0, 0, 2],
                    [0, 0, 2, 2]], {"1": "left leg", "2": "right leg"})
        canvas = self.open_canvas()
        _, mark = post(canvas, "/marks",
                       {"view": "front", "pixel": [2, 1], "text": "gap too wide"})
        self.assertIsNone(mark.get("part"))
        self.assertNotIn("part", json.loads(self.marks.read_text())[0])

    def test_a_space_with_no_mask_still_takes_marks(self):
        """A space rendered before this slice has a sheet and no mask. The
        canvas is not allowed to refuse it: a located comment without a part
        is what every mark was until now."""
        canvas = Canvas(sheet=self.sheet, marks=self.marks,
                        mask=self.mask, parts=self.parts)   # neither on disk
        self.addCleanup(canvas.stop)
        canvas.start()
        _, mark = post(canvas, "/marks",
                       {"view": "top", "pixel": [2, 1], "text": "still works"})
        self.assertEqual(mark["text"], "still works")
        self.assertIsNone(mark.get("part"))

    def test_the_mask_and_the_parts_table_are_served_to_the_page(self):
        """Hover has to be instant, so the page gets its own copy once rather
        than asking per mouse move. The mask is read from disk by the server
        and never goes anywhere near the conversation."""
        self.paint([[0, 1], [1, 1]], {"1": "pillar"})
        canvas = self.open_canvas()
        with open_url(canvas, "/mask.png", timeout=5) as r:
            self.assertEqual(r.read(), self.mask.read_bytes())
            self.assertEqual(r.headers["Content-Type"], "image/png")
        status, table = get(canvas, "/parts.json")
        self.assertEqual(status, 200)
        self.assertEqual(table, {"1": "pillar"})

    def test_the_page_names_a_part_under_the_cursor_without_asking_the_server(self):
        """No JS runs here, so this pins the page's half of the contract: it
        takes one copy of the mask and the table, and reads the pixel itself.
        `getImageData` is the proof that hover costs no request — that the
        name actually appears beside the cursor is a HITL check."""
        self.paint([[0, 1], [1, 1]], {"1": "pillar"})
        canvas = self.open_canvas()
        with open_url(canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn("/mask.png", page)
        self.assertIn("/parts.json", page)
        self.assertIn("mousemove", page)
        self.assertIn("getImageData", page)
        hover = page.split("mousemove", 1)[1].split("addEventListener", 1)[0]
        self.assertNotIn("fetch", hover)


if __name__ == "__main__":
    unittest.main()
