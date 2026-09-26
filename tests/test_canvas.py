"""The canvas loop: a click lands a mark, and the server stops when told.

These talk to the running server over HTTP, the way the page does. Nothing
here reaches inside the handler: a mark is real when it is on disk, and the
canvas is done when the port is free.
"""
import json
import re
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

    def test_the_launcher_says_it_can_mark_and_nothing_more(self):
        """One page, two hosts, and the page asks rather than assumes (ADR 0019).

        The launcher's answer is the whole of what a zero-dependency clone can
        do, and that is marking: ADR 0018 made the sheet the surface both
        parties point at, so a toolkit that could not mark without the console
        would have moved an existing capability behind an install.
        """
        status, said = get(self.canvas, "/can")
        self.assertEqual(status, 200)
        self.assertEqual(said, {"can": ["marks"]})

    def test_the_pages_console_surface_is_declared_not_assumed(self):
        """Read from the source, as the no-internet tripwire above is: there is
        no browser in this suite. What it pins is the page's side of the
        bargain — a console-only affordance says which capability it needs, and
        the launcher's ending says which capability it stands in for, so neither
        host is hard-coded into markup the other one is also served.
        """
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn('data-needs="drive"', page)
        self.assertIn('data-unless="drive"', page)

    def test_one_rule_applies_every_declaration(self):
        """The page asks its host once and enforces the answer in one place.

        Counted, not merely present: a second site that consults the answer is
        the beginning of a page that is really two pages, which is the mistake
        ADR 0019 named when it rejected sharing components between surfaces. A
        new affordance should need a declaration and no new code at all.
        """
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn("/can", page)
        # The script alone: the stylesheet names the same attributes to keep them
        # off screen until the answer lands, which is the same rule and not a
        # second one. What must stay singular is the code that acts on `can`.
        script = page.split("<script>", 1)[1]
        self.assertEqual(script.count("[data-needs]"), 1)
        self.assertEqual(script.count("[data-unless]"), 1)
        self.assertIn(".remove()", script)

    def test_nothing_reaches_for_an_affordance_its_host_removed(self):
        """Every declared element may be absent, so nothing may assume it.

        An unguarded `getElementById('done').addEventListener` throws under the
        console, which the launcher's own tests would never notice: the page
        works here and is broken there, from markup both are served. Each id
        that carries a declaration is checked, so a new affordance cannot be
        wired up the unsafe way either.
        """
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        declared = re.findall(r'id="([^"]+)"[^>]*data-(?:needs|unless)=', page)
        self.assertTrue(declared, "no declared affordance found to check")
        for got in declared:
            self.assertNotIn(f"getElementById('{got}').", page,
                             f"#{got} can be removed by its host, so reaching "
                             f"through it without a guard breaks the page")

    def test_an_unknown_capability_changes_nothing(self):
        """A host naming something this page has never heard of is not an error.

        The page's rule removes what the host lacks, so a name it does not know
        matches no element and does nothing — which is what makes a newer console
        safe in front of an older page. Nothing is reported, either: `/can` is
        written by us, and an unrecognised name there is our bug, not something
        to put in front of the user. `lib/policy.py` says its strangers out loud
        for the opposite reason — the user wrote that file.
        """
        odd = Canvas(sheet=self.sheet, marks=self.marks,
                     can=("marks", "teleport"))
        self.addCleanup(odd.stop)
        odd.start()
        status, said = get(odd, "/can")
        self.assertEqual(status, 200)
        self.assertEqual(said, {"can": ["marks", "teleport"]})
        # and the surface the name has nothing to do with is untouched
        status, _ = post(odd, "/marks", {"view": "front", "pixel": [10, 10],
                                         "text": "still works"})
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(self.marks.read_text())), 1)
        with open_url(odd, "/", timeout=5) as r:
            self.assertEqual(r.status, 200)

    def test_there_is_one_page_and_the_console_did_not_add_a_second(self):
        """ADR 0019 rejected two surfaces sharing components as *a bundler with
        a delay*. The page degrading to its host is what replaced that, so a
        second page appearing beside this one means the replacement was
        abandoned — and the sheet stops being the one surface both parties point
        at, which is ADR 0018's whole argument. If the page does outgrow one
        file, the console's extra views are served beside it, not bundled in.
        """
        from lib import canvas as canvas_lib
        pages = sorted(Path(canvas_lib.__file__).parent.glob("*.html"))
        self.assertEqual([p.name for p in pages], ["canvas.html"])

    def test_no_affordance_is_shown_before_the_host_has_answered(self):
        """`/can` is a request, so there is a moment before the answer arrives.

        Painted in that moment, the launcher's page shows the console's panel and
        the console's page shows the canvas's ending — each host briefly offering
        the other's surface, which is exactly what this slice exists to prevent.
        So whatever depends on the answer stays hidden until there is one.
        """
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn("body:not(.asked) [data-needs]", page)
        self.assertIn("body:not(.asked) [data-unless]", page)
        self.assertIn("classList.add('asked')", page)


if __name__ == "__main__":
    unittest.main()
