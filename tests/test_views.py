"""The sheet's camera frames: which view a pixel fell in, where a pin lands
once the part has moved, and when a sheet is too old to resolve against.

These cover the half of anchoring that geometry does not decide. Whether the
ray hits the right part is a question about geometry, so it is asked of the
fixture, in `contour selftest`.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import store
from lib import views


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
        view, u, v = views.aim(sheet(), [128, 384])
        self.assertEqual(view["label"], "front")
        self.assertAlmostEqual(u, 0.25, places=2)
        self.assertAlmostEqual(v, 0.25, places=2)

    def test_each_quadrant_belongs_to_the_view_that_drew_it(self):
        s = sheet()
        got = [views.aim(s, p)[0]["label"]
               for p in ([10, 10], [520, 10], [10, 520], [520, 520])]
        self.assertEqual(got, ["front", "right", "top", "persp"])


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
        views.record(self.views, 1024,
                     [{"label": "front", "tile": [0, 0, 512, 512]}], self.blend)
        # Read back through the store, which is where reading a JSON file
        # lives now: `views.record` writes a sheet, and the generic reader that
        # used to sit beside it went to `lib/store.py` (slice 16).
        return store.load(self.views, None)

    def test_a_sheet_records_the_build_it_was_drawn_from(self):
        sheet = self.record()
        self.assertEqual(sheet["resolution"], 1024)
        self.assertEqual([v["label"] for v in sheet["views"]], ["front"])
        self.assertIsNone(views.stale(sheet, self.blend))

    def test_resolution_refuses_when_the_build_has_moved_on(self):
        """Mark a sheet, rebuild, then resolve, and every ray lands in a scene
        the user never saw. It must refuse and say so, never guess — a pin
        placed in the wrong scene is worse than no pin, because it looks
        deliberate."""
        sheet = self.record()
        self.blend.write_bytes(b"a different build entirely")
        message = views.stale(sheet, self.blend)
        self.assertTrue(message)
        self.assertIn("render", message)

    def test_a_build_that_is_gone_is_just_as_refused_as_one_that_changed(self):
        sheet = self.record()
        self.blend.unlink()
        self.assertTrue(views.stale(sheet, self.blend))


class FollowTest(unittest.TestCase):
    """Why a pin is local and not a world point: the part is allowed to
    move. These are the three ways it can, and the pin survives all three."""

    def test_a_pin_moves_with_the_part_it_is_on(self):
        shifted = [1, 0, 0, 0.5,   0, 1, 0, 0,   0, 0, 1, 0.2,   0, 0, 0, 1]
        self.assertEqual(views.place(shifted, [0, 0, 0.03]), (0.5, 0.0, 0.23))

    def test_a_pin_turns_with_the_part_it_is_on(self):
        """A quarter turn about Z: a pin on the beak's tip is still on the
        tip, pointing wherever the beak now points."""
        turned = [0, -1, 0, 0,   1, 0, 0, 0,   0, 0, 1, 0,   0, 0, 0, 1]
        x, y, z = views.place(turned, [0.03, 0, 0])
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 0.03)

    def test_a_pin_stays_on_the_same_spot_when_the_part_is_resized(self):
        """The pin is a fraction of the part, not a distance from it: double
        the cap and the pin is still on its surface, not floating inside."""
        doubled = [2, 0, 0, 0,   0, 2, 0, 0,   0, 0, 2, 0,   0, 0, 0, 1]
        self.assertEqual(views.place(doubled, [0, 0, 0.03]), (0.0, 0.0, 0.06))


if __name__ == "__main__":
    unittest.main()
