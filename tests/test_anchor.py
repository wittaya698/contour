"""Anchoring: a mark stops being a pixel and becomes a place on a part.

The sheet is rebuilt every build, so a pixel pin starts lying the moment
geometry moves. These tests cover the half of that which geometry does not
decide: which view a pixel fell in, what a resolved mark looks like on disk,
and when resolution must refuse. Whether the ray hits the right part is a
question about geometry, so it is asked of the fixture, in `contour selftest`.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import anchor
from lib import store
from lib import marks as marks_store
from lib.canvas import Canvas

from client import post


def sheet(res=1024):
    """A views record as `contour render` leaves one: four tiles, top-left to
    bottom-right, each with the camera that drew it."""
    t = res // 2
    return {"resolution": res, "build": "0" * 12,
            "views": [{"label": "front", "tile": [0, 0, t, t]},
                      {"label": "right", "tile": [t, 0, t, t]},
                      {"label": "top", "tile": [0, t, t, t]},
                      {"label": "persp", "tile": [t, t, t, t]}]}


class AimTest(unittest.TestCase):
    def test_a_sheet_pixel_names_its_view_and_where_in_the_frame_it_fell(self):
        """The click arrives in sheet pixels, top-left origin, the way the
        browser and the mask count. A camera frame counts from the bottom
        left in 0..1, so the view is found by tile and the row is flipped."""
        view, u, v = anchor.aim(sheet(), [128, 384])
        self.assertEqual(view["label"], "front")
        self.assertAlmostEqual(u, 0.25, places=2)
        self.assertAlmostEqual(v, 0.25, places=2)

    def test_each_quadrant_belongs_to_the_view_that_drew_it(self):
        s = sheet()
        got = [anchor.aim(s, p)[0]["label"]
               for p in ([10, 10], [520, 10], [10, 520], [520, 520])]
        self.assertEqual(got, ["front", "right", "top", "persp"])


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


class BuildWindowTest(unittest.TestCase):
    """The ray has to hit the geometry the sheet was rendered from. That
    window is normally shut by resolving at session close; these cover what
    happens when it is not."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.blend = self.tmp / "smoke.blend"
        self.blend.write_bytes(b"a build, as bytes")
        self.views = self.tmp / "views.json"

    def record(self):
        anchor.record(self.views, 1024,
                      [{"label": "front", "tile": [0, 0, 512, 512]}], self.blend)
        # Read back through the store, which is where reading a JSON file
        # lives now: `anchor.record` writes a sheet, and `anchor.load` was a
        # generic reader that only happened to sit here (slice 16).
        return store.load(self.views, None)

    def test_a_sheet_records_the_build_it_was_drawn_from(self):
        sheet = self.record()
        self.assertEqual(sheet["resolution"], 1024)
        self.assertEqual([v["label"] for v in sheet["views"]], ["front"])
        self.assertIsNone(anchor.stale(sheet, self.blend))

    def test_resolution_refuses_when_the_build_has_moved_on(self):
        """Mark a sheet, rebuild, then resolve, and every ray lands in a scene
        the user never saw. It must refuse and say so, never guess — a pin
        placed in the wrong scene is worse than no pin, because it looks
        deliberate."""
        sheet = self.record()
        self.blend.write_bytes(b"a different build entirely")
        message = anchor.stale(sheet, self.blend)
        self.assertTrue(message)
        self.assertIn("render", message)

    def test_a_build_that_is_gone_is_just_as_refused_as_one_that_changed(self):
        sheet = self.record()
        self.blend.unlink()
        self.assertTrue(anchor.stale(sheet, self.blend))


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


class BadgeTest(unittest.TestCase):
    """A badge marks a point that is, by definition, on a part — so it cannot
    be drawn there. It is pushed off into the background and leashed back."""

    def clear_of(self, solid):
        """`clear(x, y)` over a tile with one solid rectangle in it."""
        sx, sy, sw, sh = solid
        def clear(x, y, w, h):
            return not (x < sx + sw and sx < x + w and y < sy + sh and sy < y + h)
        return clear

    def test_a_badge_is_pushed_off_the_part_it_points_at(self):
        spot = anchor.badge_spot(self.clear_of((100, 100, 100, 100)),
                                 150, 150, 30, 12, (512, 512))
        self.assertIsNotNone(spot)
        self.assertTrue(self.clear_of((100, 100, 100, 100))(*spot, 30, 12))

    def test_a_badge_stays_on_the_tile_it_belongs_to(self):
        """A pin near the edge must not push its badge into the next view."""
        spot = anchor.badge_spot(self.clear_of((0, 0, 40, 512)), 10, 250, 30, 12,
                                 (512, 512))
        x, y = spot
        self.assertTrue(0 <= x and x + 30 <= 512)
        self.assertTrue(0 <= y and y + 12 <= 512)

    def test_a_badge_with_nowhere_to_go_is_not_drawn_at_all(self):
        """Better a pin that is missing from a crowded tile than one painted
        over the geometry the whole sheet exists to show."""
        self.assertIsNone(anchor.badge_spot(lambda *a: False, 250, 250, 30, 12,
                                            (512, 512)))


class FollowTest(unittest.TestCase):
    """Why the anchor is local and not a world point: the part is allowed to
    move. These are the three ways it can, and the pin survives all three."""

    def test_a_pin_moves_with_the_part_it_is_on(self):
        shifted = [1, 0, 0, 0.5,   0, 1, 0, 0,   0, 0, 1, 0.2,   0, 0, 0, 1]
        self.assertEqual(anchor.place(shifted, [0, 0, 0.03]), (0.5, 0.0, 0.23))

    def test_a_pin_turns_with_the_part_it_is_on(self):
        """A quarter turn about Z: a pin on the beak's tip is still on the
        tip, pointing wherever the beak now points."""
        turned = [0, -1, 0, 0,   1, 0, 0, 0,   0, 0, 1, 0,   0, 0, 0, 1]
        x, y, z = anchor.place(turned, [0.03, 0, 0])
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 0.03)

    def test_a_pin_stays_on_the_same_spot_when_the_part_is_resized(self):
        """The pin is a fraction of the part, not a distance from it: double
        the cap and the pin is still on its surface, not floating inside."""
        doubled = [2, 0, 0, 0,   0, 2, 0, 0,   0, 0, 2, 0,   0, 0, 0, 1]
        self.assertEqual(anchor.place(doubled, [0, 0, 0.03]), (0.0, 0.0, 0.06))

    def test_two_pins_in_one_place_do_not_print_over_each_other(self):
        """Two remarks about the same joint is the normal case, not the odd
        one — and two badges in the same 24 px is one unreadable smudge."""
        empty = lambda *a: True
        first = anchor.badge_spot(empty, 250, 250, 30, 12, (512, 512))
        second = anchor.badge_spot(empty, 254, 252, 30, 12, (512, 512),
                                   taken=[(*first, 30, 12)])
        fx, fy = first
        sx, sy = second
        self.assertFalse(sx < fx + 30 and fx < sx + 30
                         and sy < fy + 12 and fy < sy + 12)
