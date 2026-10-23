"""An issue's number and an ADR's number each name one file.

A number is the highest file's plus one on whatever branch it is written on,
so two branches filing at once both take the same next number, and nothing
says so until both are merged. Issues and ADRs are filed on master for that
reason; this catches the one that slips past.
"""
import re
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def numbers(folder):
    """The number each numbered file in `folder` starts with."""
    return [m.group(1) for p in sorted(folder.glob("*.md"))
            if (m := re.match(r"(\d+)-", p.name))]


def taken_twice(folder):
    return sorted(n for n, k in Counter(int(n) for n in numbers(folder)).items() if k > 1)


class NumberingTest(unittest.TestCase):

    def test_no_two_issues_share_a_number(self):
        self.assertEqual(taken_twice(ROOT / "docs" / "issues"), [])

    def test_no_two_adrs_share_a_number(self):
        self.assertEqual(taken_twice(ROOT / "docs" / "adr"), [])

    def test_a_number_taken_twice_is_found(self):
        """`7-` and `007-` are the same number to a reader."""
        with tempfile.TemporaryDirectory() as d:
            for name in ("7-a.md", "007-b.md", "8-c.md", "README.md"):
                (Path(d) / name).write_text("", encoding="utf-8")
            self.assertEqual(taken_twice(Path(d)), [7])


if __name__ == "__main__":
    unittest.main()
