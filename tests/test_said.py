"""A size the chat said, as a value on the launch line (ADR 0033, issue 145).

End to end, `test_connector.CreateTest` carries one from `create` to the
console's first prompt, and `test_console` refuses a bad `--said`. These are
the value itself: one spelling, read back as it was written.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import said  # noqa: E402


class SaidTest(unittest.TestCase):
    def test_what_create_takes_reads_back_off_the_launch_line_unchanged(self):
        for dimension, mm in (("height", 1200), ("width", 300.5), ("depth", 0.25)):
            with self.subTest(dimension=dimension, mm=mm):
                self.assertEqual(said.read(said.value({"dimension": dimension, "mm": mm})),
                                 (dimension, mm))

    def test_a_whole_number_of_millimetres_is_said_as_one(self):
        """*300 mm wide*, never *300.0 mm wide*: a float off the launch line is
        the same size the chat said."""
        self.assertEqual(said.value({"dimension": "width", "mm": 300.0}), "width:300")
        self.assertEqual(said.size(*said.read("width:300")), "300 mm wide")
        self.assertEqual(said.size("height", 1200.5), "1200.5 mm tall")

    def test_anything_but_a_size_is_refused_on_either_side(self):
        for bad in ({"dimension": "length", "mm": 300}, {"dimension": "depth", "mm": float("nan")},
                    {"dimension": "depth", "mm": None}, None, ["width", 300]):
            with self.subTest(anchor=bad), self.assertRaises(ValueError):
                said.value(bad)
        for bad in ("width", "width:", "width:nan", "width:0", ":300", "300", "width:3:00"):
            with self.subTest(text=bad), self.assertRaises(ValueError):
                said.read(bad)


if __name__ == "__main__":
    unittest.main()
