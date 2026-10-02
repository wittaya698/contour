"""A spec may change; it may not change silently (ADR 0016).

`lib/revision.py` is what `contour check` asks whether a changed spec was
bumped, and what `contour rename` refuses on — asked here of a throwaway
repository, as both ask it of a space.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import revision     # noqa: E402

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


class OfTest(unittest.TestCase):

    def test_a_spec_from_before_revisions_is_revision_0(self):
        self.assertEqual(revision.of("model: beaky\n"), 0)

    def test_the_field_is_read_at_column_0_only(self):
        """The word inside an indented block scalar is the user's prose."""
        self.assertEqual(revision.of("notes: |\n  revision: 9\nrevision: 3\n"), 3)


class UnbumpedTest(unittest.TestCase):

    def setUp(self):
        self.space = Path(tempfile.mkdtemp())
        self.spec = self.space / "spec.yaml"
        subprocess.run(["git", "init", "-q", str(self.space)], check=True)

    def commit(self, text):
        self.spec.write_text(text)
        for args in (["add", "spec.yaml"], ["commit", "-qm", "spec"]):
            subprocess.run(["git", "-C", str(self.space), *args], env=ENV, check=True)

    def test_a_spec_nobody_committed_is_being_created_not_changed(self):
        """Even at revision 0: a first draft has nothing to have been bumped past."""
        self.spec.write_text("model: widget\n")
        self.assertIsNone(revision.unbumped(self.space))

    def test_a_spec_as_committed_is_fine(self):
        self.commit("revision: 2\n")
        self.assertIsNone(revision.unbumped(self.space))

    def test_a_changed_spec_with_a_bump_is_fine(self):
        self.commit("revision: 2\n")
        self.spec.write_text("revision: 3\nnotes: confirmed\n")
        self.assertIsNone(revision.unbumped(self.space))

    def test_a_changed_spec_without_a_bump_is_said_with_both_numbers(self):
        self.commit("revision: 2\n")
        self.spec.write_text("revision: 2\nnotes: nobody confirmed this\n")
        self.assertEqual(revision.unbumped(self.space), (2, 2))


if __name__ == "__main__":
    unittest.main()
