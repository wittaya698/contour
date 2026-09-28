"""Where a badge may go: never over the model it remarks on, never over
another badge, and never outside the tile it belongs to (ADR 0018).

The search is handed a `clear` predicate rather than a mask, so every claim
here is asked without a render. Whether the mask says the right thing about
the geometry is the fixture's business, in `contour selftest`.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import badges


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
        spot = badges.badge_spot(self.clear_of((100, 100, 100, 100)),
                                 150, 150, 30, 12, (512, 512))
        self.assertIsNotNone(spot)
        self.assertTrue(self.clear_of((100, 100, 100, 100))(*spot, 30, 12))

    def test_a_badge_stays_on_the_tile_it_belongs_to(self):
        """A pin near the edge must not push its badge into the next view."""
        spot = badges.badge_spot(self.clear_of((0, 0, 40, 512)), 10, 250, 30, 12,
                                 (512, 512))
        x, y = spot
        self.assertTrue(0 <= x and x + 30 <= 512)
        self.assertTrue(0 <= y and y + 12 <= 512)

    def test_a_badge_with_nowhere_to_go_is_not_drawn_at_all(self):
        """Better a pin that is missing from a crowded tile than one painted
        over the geometry the whole sheet exists to show."""
        self.assertIsNone(badges.badge_spot(lambda *a: False, 250, 250, 30, 12,
                                            (512, 512)))

    def test_two_pins_in_one_place_do_not_print_over_each_other(self):
        """Two remarks about the same joint is the normal case, not the odd
        one — and two badges in the same 24 px is one unreadable smudge."""
        empty = lambda *a: True
        first = badges.badge_spot(empty, 250, 250, 30, 12, (512, 512))
        second = badges.badge_spot(empty, 254, 252, 30, 12, (512, 512),
                                   taken=[(*first, 30, 12)])
        fx, fy = first
        sx, sy = second
        self.assertFalse(sx < fx + 30 and fx < sx + 30
                         and sy < fy + 12 and fy < sy + 12)


if __name__ == "__main__":
    unittest.main()
