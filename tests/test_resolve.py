"""Anchoring as a lifecycle: a mark stops being a pixel and becomes a place on
a part, and costs one Blender startup per canvas session to do it.

These were the part of `tests/test_anchor.py` that never touched the module it
was named after. They ask the record and the canvas, not the geometry —
`lib/views.py` and `lib/badges.py` have their own files now (slice 20), and
the ray itself is asked of the fixture, in `contour selftest`.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import marks as marks_store
from lib.canvas import Canvas

from client import post


class ResolveTest(unittest.TestCase):
    def setUp(self):
        self.marks = Path(tempfile.mkdtemp()) / "marks.json"

    def add(self, **mark):
        return marks_store.append(self.marks, mark)["id"]

    def test_a_resolved_mark_carries_a_place_on_a_part_and_no_longer_a_pixel(self):
        """A pixel is only ever a way of asking the question. Once the ray has
        answered it, leaving the pixel behind would leave something that looks
        authoritative and is wrong the moment the model is rebuilt."""
        one = self.add(view="front", pixel=[128, 384], text="cap too round")
        two = self.add(view="top", pixel=[10, 520], text="unresolved still")
        marks_store.anchor(self.marks, {one: {"part": "cap", "local": [0.0, 0.0, 0.03]}})
        first, second = json.loads(self.marks.read_text())
        self.assertEqual(first["part"], "cap")
        self.assertEqual(first["anchor"], {"local": [0.0, 0.0, 0.03]})
        self.assertNotIn("pixel", first)
        self.assertEqual(first["text"], "cap too round")
        self.assertEqual(second["pixel"], [10, 520])
        self.assertNotIn("anchor", second)

    def test_only_marks_that_still_carry_a_pixel_are_put_to_the_ray(self):
        """One ray per unresolved mark, once. A mark already anchored is
        answered, and asking again in a later session would only let a
        rebuilt sheet move a pin that was already right."""
        one = self.add(view="front", pixel=[128, 384], text="cap too round")
        two = self.add(view="right", pixel=[600, 100], text="pillar thin")
        marks_store.anchor(self.marks, {one: {"part": "cap", "local": [0, 0, 0.03]}})
        self.assertEqual([m["id"] for m in marks_store.unresolved(marks_store.load(self.marks))],
                         [two])

    def test_a_ref_mark_is_never_put_to_the_ray(self):
        """A reference is a photograph: nothing in it knows what a part is,
        and its pixels never move. Ref marks land in 0018-5, but this is the
        slice that could break them, so the exemption is pinned here."""
        self.add(view="front", pixel=[128, 384], text="cap too round")
        ref = self.add(ref="beaky-front.png", pixel=[300, 120], text="that gap")
        got = [m["id"] for m in marks_store.unresolved(marks_store.load(self.marks))]
        self.assertNotIn(ref, got)


class OrphanTest(unittest.TestCase):
    def setUp(self):
        self.marks = Path(tempfile.mkdtemp()) / "marks.json"
        mark = marks_store.append(self.marks, {"view": "front", "pixel": [128, 384],
                                               "text": "cap too round"})
        marks_store.anchor(self.marks, {mark["id"]: {"part": "cap", "local": [0, 0, 0.03]}})

    def on_disk(self):
        return json.loads(self.marks.read_text())[0]

    def test_a_mark_whose_part_is_gone_is_orphaned_rather_than_drawn_somewhere_wrong(self):
        """Deleting a part does not answer the question asked about it. The
        pin has nowhere to be, so it says so in the file instead of being
        re-projected against whatever is nearest."""
        marks_store.orphan(self.marks, {"plinth", "pillar"})
        self.assertTrue(self.on_disk()["orphaned"])
        self.assertEqual(self.on_disk()["part"], "cap")

    def test_an_orphan_comes_home_when_its_part_does(self):
        """Usually a rename, or a part briefly commented out of build.py. The
        flag says what the last build found, not what once went wrong, or a
        mark would stay marked homeless forever."""
        marks_store.orphan(self.marks, {"plinth"})
        marks_store.orphan(self.marks, {"plinth", "cap"})
        self.assertFalse(self.on_disk().get("orphaned"))


class CanvasResolveTest(unittest.TestCase):
    """Anchoring costs one Blender startup per session. The canvas is what
    spends it, so this is where the count is pinned — the run itself is
    stubbed, because what it does to geometry is the fixture's business."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.sheet = self.tmp / "sheet.png"
        self.sheet.write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")
        self.marks = self.tmp / "marks.json"
        self.runs = []

    def resolver(self):
        self.runs.append(1)
        return {"ok": True, "lines": ["widget resolve 1 mark anchored"]}

    def open_canvas(self):
        canvas = Canvas(sheet=self.sheet, marks=self.marks, resolve=self.resolver)
        self.addCleanup(canvas.stop)
        canvas.start()
        return canvas

    def test_the_session_ends_by_anchoring_what_it_captured_once(self):
        canvas = self.open_canvas()
        post(canvas, "/marks", {"view": "front", "pixel": [128, 384], "text": "a"})
        post(canvas, "/marks", {"view": "top", "pixel": [10, 520], "text": "b"})
        post(canvas, "/done", {})
        report = canvas.wait()
        self.assertEqual(len(self.runs), 1)
        self.assertIn("1 mark anchored", " ".join(report["lines"]))

    def test_a_session_with_nothing_to_anchor_starts_no_blender(self):
        """Closing a mark, or just looking, is the common session. It must
        cost what it always cost: a page and a port."""
        mark = marks_store.append(self.marks, {"view": "front", "pixel": [1, 2],
                                               "text": "already placed"})
        marks_store.anchor(self.marks, {mark["id"]: {"part": "cap", "local": [0, 0, 0.03]}})
        canvas = self.open_canvas()
        post(canvas, "/close", {"id": mark["id"]})
        post(canvas, "/done", {})
        canvas.wait()
        self.assertEqual(self.runs, [])


if __name__ == "__main__":
    unittest.main()
