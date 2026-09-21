"""Pruning: the canvas drops closed marks that git already holds.

Every test here builds a real git repository and a real release tag, because
the rule is about what the tag contains, not about a timestamp we wrote
ourselves. Nothing is deleted that `git show <tag>:marks.json` cannot print.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import marks
from lib.canvas import Canvas


def git(space, *args):
    subprocess.run(("git",) + args, cwd=space, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class PruneTest(unittest.TestCase):
    def setUp(self):
        self.space = Path(tempfile.mkdtemp())
        self.path = self.space / marks.NAME
        git(self.space, "init", "-q")
        git(self.space, "config", "user.email", "t@example.com")
        git(self.space, "config", "user.name", "t")

    def release(self, tag, contents):
        """Commit these marks and tag them, the way release-model does."""
        marks.save(self.path, contents)
        git(self.space, "add", marks.NAME)
        git(self.space, "commit", "-qm", tag, "--allow-empty")
        git(self.space, "tag", "-a", tag, "-m", tag)

    def ids(self):
        return [m["id"] for m in marks.load(self.path)]

    def test_a_closed_mark_the_last_release_holds_is_dropped(self):
        self.release("beaky-v1", [
            {"id": "m1", "status": "closed", "text": "beak short"},
            {"id": "m2", "status": "open", "text": "legs too close"}])
        marks.save(self.path, marks.load(self.path) + [
            {"id": "m3", "status": "closed", "text": "said after the release"}])
        marks.prune(self.path)
        self.assertEqual(self.ids(), ["m2", "m3"])

    def test_an_open_mark_survives_every_release(self):
        """Age is not a reason to drop a finding; only the user closing it is."""
        self.release("beaky-v1", [{"id": "m1", "status": "open", "text": "gap"}])
        self.release("beaky-v2", marks.load(self.path))
        marks.prune(self.path)
        self.assertEqual(self.ids(), ["m1"])

    def test_nothing_is_pruned_before_the_first_release(self):
        """With no tag there is no archive, so there is nothing safe to drop."""
        marks.save(self.path, [{"id": "m1", "status": "closed", "text": "done"}])
        git(self.space, "add", marks.NAME)
        git(self.space, "commit", "-qm", "wip")
        self.assertIsNone(marks.prune(self.path))
        self.assertEqual(self.ids(), ["m1"])

    def test_the_canvas_prunes_when_it_starts(self):
        """Pruning is the canvas's job, so the page never lists a mark that
        git has already filed away."""
        self.release("beaky-v1", [
            {"id": "m1", "status": "closed", "text": "beak short"},
            {"id": "m2", "status": "open", "text": "legs too close"}])
        sheet = self.space / "sheet.png"
        sheet.write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")
        canvas = Canvas(sheet=sheet, marks=self.path)
        self.addCleanup(canvas.stop)
        canvas.start()
        self.assertEqual(self.ids(), ["m2"])

    def test_the_report_says_what_it_pruned(self):
        """Deleting lines from a tracked file silently is worse than not
        deleting them: the report names what went, and where it still is."""
        self.release("beaky-v1", [{"id": "m1", "status": "closed", "text": "x"}])
        sheet = self.space / "sheet.png"
        sheet.write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")
        canvas = Canvas(sheet=sheet, marks=self.path)
        self.addCleanup(canvas.stop)
        canvas.start()
        canvas.finish()
        line = " ".join(canvas.wait()["lines"])
        self.assertIn("1 mark", line)
        self.assertIn("beaky-v1", line)


if __name__ == "__main__":
    unittest.main()
