"""The canvas loop: a click lands a mark, and the server stops when told.

These talk to the running server over HTTP, the way the page does. Nothing
here reaches inside the handler: a mark is real when it is on disk, and the
canvas is done when the port is free.
"""
import json
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.canvas import Canvas


def post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, json.loads(r.read() or b"null")


class CanvasTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.sheet = self.tmp / "sheet.png"
        self.sheet.write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")
        self.marks = self.tmp / "marks.json"
        self.canvas = Canvas(sheet=self.sheet, marks=self.marks)
        self.addCleanup(self.canvas.stop)
        self.canvas.start()

    def test_a_posted_mark_lands_in_marks_json(self):
        status, _ = post(self.canvas.url + "/marks",
                         {"view": "front", "pixel": [412, 208],
                          "text": "beak sits too low"})
        self.assertEqual(status, 200)
        stored = json.loads(self.marks.read_text())
        self.assertEqual(len(stored), 1)
        mark = stored[0]
        self.assertEqual(mark["view"], "front")
        self.assertEqual(mark["pixel"], [412, 208])
        self.assertEqual(mark["text"], "beak sits too low")
        self.assertEqual(mark["author"], "user")
        self.assertEqual(mark["status"], "open")
        self.assertTrue(mark["id"])

    def test_the_page_and_the_sheet_are_served(self):
        with urllib.request.urlopen(self.canvas.url + "/", timeout=5) as r:
            page = r.read().decode()
            self.assertEqual(r.status, 200)
            self.assertIn("text/html", r.headers["Content-Type"])
        self.assertIn("<canvas", page)
        with urllib.request.urlopen(self.canvas.url + "/sheet.png", timeout=5) as r:
            self.assertEqual(r.read(), self.sheet.read_bytes())
            self.assertEqual(r.headers["Content-Type"], "image/png")

    def test_the_page_fetches_nothing_from_the_internet(self):
        """ADR 0018's tripwire: needing a bundler means the scope went wrong."""
        with urllib.request.urlopen(self.canvas.url + "/", timeout=5) as r:
            page = r.read().decode()
        for smell in ("http://", "https://", "//cdn", "<script src", "<link"):
            self.assertNotIn(smell, page.replace("http://127.0.0.1", ""))

    def test_done_stops_the_server_and_reports_what_was_captured(self):
        post(self.canvas.url + "/marks",
             {"view": "top", "pixel": [10, 20], "text": "legs too close"})
        post(self.canvas.url + "/done", {})
        report = self.canvas.wait()
        self.assertTrue(report["ok"])
        self.assertIn("1 mark", " ".join(report["lines"]))
        with self.assertRaises(urllib.error.URLError):
            urllib.request.urlopen(self.canvas.url + "/", timeout=2)


if __name__ == "__main__":
    unittest.main()
