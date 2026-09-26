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

from lib import marks as marks_store
from lib.canvas import Canvas
from client import get, open_url, post


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
        status, _ = post(self.canvas, "/marks",
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
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
            self.assertEqual(r.status, 200)
            self.assertIn("text/html", r.headers["Content-Type"])
        self.assertIn("<canvas", page)
        with open_url(self.canvas, "/sheet.png", timeout=5) as r:
            self.assertEqual(r.read(), self.sheet.read_bytes())
            self.assertEqual(r.headers["Content-Type"], "image/png")

    def test_the_page_fetches_nothing_from_the_internet(self):
        """ADR 0018's tripwire: needing a bundler means the scope went wrong."""
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        for smell in ("http://", "https://", "//cdn", "<script src", "<link"):
            self.assertNotIn(smell, page.replace("http://127.0.0.1", ""))

    def test_closing_a_mark_takes_it_out_of_the_open_count(self):
        """Only the user closes a mark, and this is the action they take."""
        _, mark = post(self.canvas, "/marks",
                       {"view": "front", "pixel": [1, 2], "text": "beak short"})
        status, closed = post(self.canvas, "/close", {"id": mark["id"]})
        self.assertEqual(status, 200)
        self.assertEqual(closed["status"], "closed")
        on_disk = json.loads(self.marks.read_text())
        self.assertEqual([m["status"] for m in on_disk], ["closed"])
        self.assertIsNone(marks_store.status_line(self.marks))

    def test_marks_from_an_earlier_session_are_served_and_closable(self):
        """A mark outlives its session, so the page must be able to see one
        it did not place — otherwise closing reaches almost nothing."""
        marks_store.append(self.marks, {"view": "top", "pixel": [9, 9],
                                        "text": "legs too close"})
        status, served = get(self.canvas, "/marks")
        self.assertEqual(status, 200)
        self.assertEqual([m["text"] for m in served], ["legs too close"])
        post(self.canvas, "/close", {"id": served[0]["id"]})
        self.assertIsNone(marks_store.status_line(self.marks))

    def test_the_page_loads_the_marks_on_file_and_offers_to_close_one(self):
        """No JS runs here, so this proves only the page's half of the
        contract: it asks for the marks on file, and it has a close action
        that needs no typing. What a closed one looks like is a HITL check."""
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn("'/marks'", page)
        self.assertIn("'/close'", page)
        self.assertIn(".closed", page)

    def test_done_stops_the_server_and_reports_what_was_captured(self):
        post(self.canvas, "/marks",
             {"view": "top", "pixel": [10, 20], "text": "legs too close"})
        post(self.canvas, "/done", {})
        report = self.canvas.wait()
        self.assertTrue(report["ok"])
        self.assertIn("1 mark", " ".join(report["lines"]))
        with self.assertRaises(urllib.error.URLError):
            open_url(self.canvas, "/", timeout=2)

    def test_the_page_beats_so_a_closed_tab_can_be_told_from_a_quiet_one(self):
        """Read from the source, as the no-internet tripwire above is: there is
        no browser here to run it, and a page that did not beat would leave the
        console's whole lifetime rule waiting for a signal nobody sends."""
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn("/beat", page)
        self.assertIn("setInterval", page)

    def test_a_beat_leaves_the_canvas_serving(self):
        """The page beats so the console can tell a closed tab from a quiet one,
        and the same page is served to both. The canvas records the beat and acts
        on nothing: its session ends when the user presses Done (ADR 0018), and a
        lifetime rule that moved in here would end one because a browser was
        slow to say anything."""
        status, _ = post(self.canvas, "/beat", {})
        self.assertEqual(status, 200)
        self.assertFalse(self.canvas.done)
        with open_url(self.canvas, "/", timeout=5) as r:
            self.assertEqual(r.status, 200)


if __name__ == "__main__":
    unittest.main()
