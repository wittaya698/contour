"""Ref marks: pointing at the user's intent instead of at our render (ADR 0018).

A sheet mark says *the build is wrong* and has to be resolved against geometry.
A ref mark says *here is what I meant*, and a photograph does not change, so
there is nothing to resolve and nothing to anchor — rule 1 guarantees the thing
it points at stays exactly where it was. These tests cover that the canvas can
show a reference, take a mark on one, and never write to `refs/` while doing it.
"""
import json
import shutil
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import marks as marks_store
from lib.canvas import Canvas
from client import get, open_url, post

# Two bytes that are honestly a PNG header and honestly nothing else: what is
# being tested is which file comes back, never how it decodes.
PNG = b"\x89PNG\r\n\x1a\nreference"


class RefListingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.refs = self.tmp / "refs"
        self.refs.mkdir()
        (self.tmp / "sheet.png").write_bytes(PNG)

    def open_canvas(self, refs):
        canvas = Canvas(sheet=self.tmp / "sheet.png", marks=self.tmp / "marks.json",
                        refs=refs)
        self.addCleanup(canvas.stop)
        canvas.start()
        return canvas

    def test_the_canvas_lists_the_images_in_the_refs_directory(self):
        (self.refs / "persp.webp").write_bytes(PNG)
        (self.refs / "front.png").write_bytes(PNG)
        canvas = self.open_canvas(self.refs)
        status, listing = get(canvas, "/refs.json")
        self.assertEqual(status, 200)
        self.assertEqual(listing, ["front.png", "persp.webp"])

    def test_a_space_with_no_references_simply_offers_none(self):
        """The fixture has no `refs/` at all, and neither does a space on its
        first day. The strip is then empty and the canvas is otherwise the
        canvas it always was — an absent reference is not an error."""
        canvas = self.open_canvas(None)
        self.assertEqual(get(canvas, "/refs.json"), (200, []))
        with open_url(canvas, "/", timeout=5) as r:
            self.assertEqual(r.status, 200)

    def test_a_reference_is_served_as_the_image_it_is(self):
        """The page draws it on the same canvas the sheet uses, so it has to
        arrive as an image and not as a download."""
        (self.refs / "persp.webp").write_bytes(PNG + b"-persp")
        canvas = self.open_canvas(self.refs)
        with open_url(canvas, "/ref?name=persp.webp", timeout=5) as r:
            self.assertEqual(r.status, 200)
            self.assertEqual(r.headers["Content-Type"], "image/webp")
            self.assertEqual(r.read(), PNG + b"-persp")

    def test_only_a_listed_reference_is_ever_served(self):
        """The name arrives from a page, so it is a request and not an
        instruction: anything the listing does not already name is refused
        outright rather than resolved and then judged."""
        (self.refs / "persp.webp").write_bytes(PNG)
        secret = self.tmp / "spec.yaml"
        secret.write_text("dimensions: {height_mm: 1700}\n")
        canvas = self.open_canvas(self.refs)
        for asked in ("../spec.yaml", "/etc/hosts", "notes.md", ""):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                open_url(canvas, "/ref?name=" + urllib.parse.quote(asked), timeout=5)
            self.assertEqual(caught.exception.code, 404, asked)


class RefMarkTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.refs = self.tmp / "refs"
        self.refs.mkdir()
        (self.refs / "persp.webp").write_bytes(PNG)
        (self.tmp / "sheet.png").write_bytes(PNG)
        self.marks = self.tmp / "marks.json"
        self.canvas = Canvas(sheet=self.tmp / "sheet.png", marks=self.marks,
                             refs=self.refs)
        self.addCleanup(self.canvas.stop)
        self.canvas.start()

    def test_a_click_on_a_reference_records_the_image_the_pixel_and_the_words(self):
        """And nothing else. Nothing in a photograph knows what a part is, and
        no view of ours drew it, so a ref mark carries neither."""
        post(self.canvas, "/marks",
             {"ref": "persp.webp", "pixel": [880, 410],
              "text": "the gap between the legs is what I meant"})
        mark, = json.loads(self.marks.read_text())
        self.assertEqual(mark["ref"], "persp.webp")
        self.assertEqual(mark["pixel"], [880, 410])
        self.assertEqual(mark["text"], "the gap between the legs is what I meant")
        self.assertEqual(mark["status"], "open")
        self.assertNotIn("part", mark)
        self.assertNotIn("view", mark)

    def test_a_session_of_ref_marks_alone_never_starts_blender(self):
        """There is nothing to cast a ray at. A photograph has no geometry, and
        rule 1 says it will be the same photograph tomorrow, so its pixel is
        already the whole answer — the one Blender run this session is allowed
        is not spent (ADR 0018)."""
        asked = []
        self.canvas.resolve = lambda: asked.append(1) or {"lines": []}
        post(self.canvas, "/marks",
             {"ref": "persp.webp", "pixel": [880, 410], "text": "here"})
        self.assertEqual(self.canvas.anchor(), [])
        self.assertEqual(asked, [])

    def test_a_sheet_mark_beside_it_still_does(self):
        """The companion to the above, so it is proving that ref marks are
        skipped rather than that resolution is broken."""
        asked = []
        self.canvas.resolve = lambda: asked.append(1) or {"lines": ["resolved"]}
        post(self.canvas, "/marks",
             {"ref": "persp.webp", "pixel": [880, 410], "text": "here"})
        post(self.canvas, "/marks",
             {"view": "front", "pixel": [260, 120], "text": "and there"})
        self.assertEqual(self.canvas.anchor(), ["resolved"])
        self.assertEqual(len(asked), 1)

    def test_both_kinds_of_mark_count_as_one_thing_outstanding(self):
        """`contour check` reports findings, not sheet findings. A remark about
        the reference is every bit as unanswered as a remark about the build,
        and the user is owed one number, not two."""
        post(self.canvas, "/marks",
             {"ref": "persp.webp", "pixel": [880, 410], "text": "here"})
        self.assertEqual(marks_store.status_line(self.marks), "1 mark open")
        post(self.canvas, "/marks",
             {"view": "front", "pixel": [260, 120], "text": "and there"})
        self.assertEqual(marks_store.status_line(self.marks), "2 marks open")

    def test_a_whole_session_leaves_the_references_exactly_as_it_found_them(self):
        """Rule 1, pinned. The references are the user's intent in pictures and
        the only copy of it; a mark *about* one is a new line in the marks file,
        never a change to the picture. This is a guard, not a driven behaviour:
        `lib/refs` has no function that writes, and this is what says so."""
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.refs.iterdir()}
        get(self.canvas, "/refs.json")
        open_url(self.canvas, "/ref?name=persp.webp",
                               timeout=5).read()
        post(self.canvas, "/marks",
             {"ref": "persp.webp", "pixel": [880, 410], "text": "here"})
        self.canvas.close(json.loads(self.marks.read_text())[0]["id"])
        after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.refs.iterdir()}
        self.assertEqual(after, before)

    def test_a_ref_marks_pixel_outlives_the_build_that_moved_everything_else(self):
        """Resolution rewrites every sheet mark it can place, and orphans the
        ones whose part has gone. A ref mark is offered to neither: its pixel is
        in a photograph, which no build of ours has any say over."""
        post(self.canvas, "/marks",
             {"ref": "persp.webp", "pixel": [880, 410], "text": "here"})
        post(self.canvas, "/marks",
             {"view": "front", "pixel": [260, 120], "text": "and there"})
        was, sheet = json.loads(self.marks.read_text())

        # What a build does to the marks file, without a build: the sheet mark
        # lands on a part, and then that part is deleted from build.py.
        marks_store.anchor(self.marks, {sheet["id"]: {"part": "neck",
                                                "local": [0.0, 0.1, 0.0]}})
        marks_store.orphan(self.marks, {"torso", "head"})

        now = next(m for m in json.loads(self.marks.read_text())
                   if m["id"] == was["id"])
        self.assertEqual(now, was)

    def test_no_build_outcome_green_or_red_closes_a_ref_mark(self):
        """A ref mark says *here is what I meant*. A green build does not mean
        we understood it, and a red one does not mean we misunderstood it: the
        finding is answered by a measurement or a spec revision, both of which
        happen elsewhere and neither of which is a build (ADR 0018).

        A guard. The store has exactly one way to close a mark and only the page
        reaches it; this is what will notice if a second way ever appears.
        """
        post(self.canvas, "/marks",
             {"ref": "persp.webp", "pixel": [880, 410], "text": "here"})
        mid = json.loads(self.marks.read_text())[0]["id"]
        marks_store.anchor(self.marks, {mid: {"part": "neck", "local": [0, 0, 0]}})
        marks_store.orphan(self.marks, set())
        marks_store.prune(self.marks)
        marks_store.status_line(self.marks)
        mark, = json.loads(self.marks.read_text())
        self.assertEqual(mark["status"], "open")
        self.assertNotIn("anchor", mark)      # nor did a stray id anchor it
        self.assertNotIn("orphaned", mark)


if __name__ == "__main__":
    unittest.main()
