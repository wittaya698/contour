"""A clip as one picture (ADR 0023, issue 55).

Six frames from the side in one row, six from the front in another, on the
sheet's grid. What is decided without Blender is decided here: which frames,
at what scale, of which clip. The picture itself is the fixture's to show, in
`tests/test_fixture.py`.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import filmstrip, views


class FramesTest(unittest.TestCase):
    def test_a_loop_is_cut_into_six_with_no_pose_twice(self):
        """A loop's frame N is its frame 0 again, so drawing both would spend a
        sixth of the strip on a pose already in it."""
        self.assertEqual(filmstrip.frames(30, loop=True), [0, 5, 10, 15, 20, 25])

    def test_a_clip_that_stops_is_drawn_to_where_it_stops(self):
        """Where a wave ends is half of what it is."""
        self.assertEqual(filmstrip.frames(30, loop=False), [0, 6, 12, 18, 24, 30])

    def test_a_clip_that_does_not_divide_by_six_lands_on_whole_frames(self):
        """The fixture's sway is 20 frames: a frame is a whole number, and the
        nearest one to each sixth is the one keyed."""
        self.assertEqual(filmstrip.frames(20, loop=True), [0, 3, 7, 10, 13, 17])


class ScaleTest(unittest.TestCase):
    """One scale for all twelve tiles, so a part reads the same size in every
    frame and both rows: the sheet's, unless the widest frame would not fit a
    sixth of the width, and then only as much further out as it takes."""

    def test_a_model_narrow_enough_is_drawn_at_the_sheets_scale(self):
        lo, hi = (-0.06, -0.05, 0.0), (0.06, 0.05, 0.2)    # the fixture
        self.assertEqual(filmstrip.scale(lo, hi), views.sheet_scale(lo, hi))

    def test_a_model_too_wide_for_a_tile_is_drawn_further_out_until_it_fits(self):
        """beaky, hand to hand: 0.88 m is wider than the 0.83 m a tile shows
        at the sheet's scale, and a filmstrip that cut its hands off would show
        a walk with no arms swinging."""
        lo, hi = (-0.44, -0.3, 0.0), (0.44, 0.3, 1.7)
        s = filmstrip.scale(lo, hi)
        w, h = filmstrip.TILE
        self.assertGreater(s, views.sheet_scale(lo, hi))
        self.assertAlmostEqual(s * w / h, 0.88 * 1.12)


class ClipTest(unittest.TestCase):
    SWAY = {"clips": {"sway": {"frames": 20, "fps": 24, "loop": True}}}

    def test_a_spec_with_one_clip_needs_it_named_by_nobody(self):
        self.assertEqual(filmstrip.clip(self.SWAY, None), ("sway", ""))

    def test_a_clip_the_spec_does_not_have_is_refused_with_the_ones_it_does(self):
        self.assertEqual(filmstrip.clip(self.SWAY, "walk"),
                         (None, "no clip walk in the spec: it has sway"))

    def test_a_spec_with_several_clips_is_asked_which(self):
        spec = {"clips": {"walk": {}, "idle": {}}}
        self.assertEqual(filmstrip.clip(spec, None),
                         (None, "which clip? the spec has idle, walk"))

    def test_a_spec_with_no_clips_has_no_filmstrip(self):
        self.assertEqual(filmstrip.clip({"parts": []}, None),
                         (None, "no clips in the spec: nothing moves to draw"))


if __name__ == "__main__":
    unittest.main()
