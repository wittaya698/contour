"""The arithmetic under every space's `build.py`, testable without Blender.

`lib/kit.py` is what each space's build calls, and it lives in the Blender half,
so nothing pure can import it. What in it is arithmetic or validation lives in
`lib/units.py` instead, and `kit` calls it: millimetres to metres, a size that is
three lengths, a hex colour to the linear values Blender stores (issue 26).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import units  # noqa: E402


class MillimetreTest(unittest.TestCase):
    def test_one_length_is_one_number_in_metres(self):
        self.assertEqual(units.mm(50), 0.05)

    def test_several_lengths_are_a_tuple(self):
        self.assertEqual(units.mm(1, 2, 3), (0.001, 0.002, 0.003))


class SizeTest(unittest.TestCase):
    """A box is three lengths. Two, or a zero, used to reach bmesh and fail
    there, inside Blender, in words about vectors rather than about the box."""

    def test_three_lengths_in_millimetres_come_back_in_metres(self):
        self.assertEqual(units.size((120, 100, 40)), (0.12, 0.1, 0.04))

    def test_two_lengths_are_refused_naming_what_was_given(self):
        with self.assertRaisesRegex(ValueError, r"three lengths.*\(120, 100\)"):
            units.size((120, 100))

    def test_a_length_that_is_not_positive_is_refused(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            units.size((120, 0, 40))
        with self.assertRaisesRegex(ValueError, "positive"):
            units.size((120, -1, 40))


class ColourTest(unittest.TestCase):
    """What the user picks is sRGB hex; what Blender stores is linear."""

    def test_white_and_black_are_the_ends(self):
        self.assertEqual(units.linear("#FFFFFF"), (1.0, 1.0, 1.0))
        self.assertEqual(units.linear("#000000"), (0.0, 0.0, 0.0))

    def test_the_curve_and_the_straight_part_below_it(self):
        """0x80 is on the power curve, 0x0A on the linear toe below 0.04045."""
        r, g, b = units.linear("#800A80")
        self.assertAlmostEqual(r, 0.2158605, places=6)
        self.assertAlmostEqual(g, 10 / 255 / 12.92, places=9)
        self.assertEqual(r, b)

    def test_the_hash_is_optional_and_case_does_not_matter(self):
        self.assertEqual(units.linear("8a8f98"), units.linear("#8A8F98"))

    def test_a_colour_that_is_not_six_hex_digits_is_refused_by_name(self):
        for bad in ("#8A8F9", "red", "#GG0000", "#8A8F98FF"):
            with self.assertRaisesRegex(ValueError, f"'{bad}'"):
                units.linear(bad)


if __name__ == "__main__":
    unittest.main()
