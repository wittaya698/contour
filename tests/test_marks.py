"""The mark store, and the one line `contour check` prints about it."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import marks


class StatusLineTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "marks.json"

    def write(self, *statuses):
        marks.save(self.path, [{"id": f"m{i}", "status": s}
                               for i, s in enumerate(statuses, 1)])

    def test_silent_when_there_is_no_file(self):
        self.assertIsNone(marks.status_line(self.path))

    def test_silent_when_nothing_is_open(self):
        self.write("closed", "closed")
        self.assertIsNone(marks.status_line(self.path))

    def test_counts_only_the_open_ones(self):
        self.write("open", "closed", "open")
        self.assertEqual(marks.status_line(self.path), "2 marks open")

    def test_says_mark_not_marks_when_there_is_one(self):
        self.write("open")
        self.assertEqual(marks.status_line(self.path), "1 mark open")


if __name__ == "__main__":
    unittest.main()
