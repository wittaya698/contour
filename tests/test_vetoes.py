"""The veto count below the console (ADR 0024, decision 3).

The console page and the connector both say *n vetoes uncommitted*, and both
ask `lib/vetoes.py`, so the two cannot disagree. What is counted is what `HEAD`
does not hold, asked of git.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import vetoes  # noqa: E402

V1 = {"id": "v1", "tool": "Edit", "reason": "not that tolerance"}
V2 = {"id": "v2", "tool": "Bash", "reason": "no"}


class UncommittedTest(unittest.TestCase):
    def setUp(self):
        self.space = Path(tempfile.mkdtemp())
        self.file = self.space / vetoes.NAME

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.space), "-c", "user.name=t",
                        "-c", "user.email=t@t", *args],
                       check=True, capture_output=True)

    def test_a_space_with_no_vetoes_has_none_at_risk(self):
        self.assertEqual(vetoes.uncommitted(self.space), 0)

    def test_a_space_that_is_no_repository_has_every_veto_at_risk(self):
        """Not an error to raise at the page: nothing is committed, so the
        count says all of them."""
        self.file.write_text(json.dumps([V1, V2]))
        self.assertEqual(vetoes.uncommitted(self.space), 2)

    def test_what_head_holds_is_not_counted(self):
        self.git("init", "-q")
        self.file.write_text(json.dumps([V1]))
        self.git("add", vetoes.NAME)
        self.git("commit", "-qm", "v1")
        self.file.write_text(json.dumps([V1, V2]))
        self.assertEqual(vetoes.uncommitted(self.space), 1)


if __name__ == "__main__":
    unittest.main()
