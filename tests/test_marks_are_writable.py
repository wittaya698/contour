"""marks.json is a file both parties write to, so nothing may stand in the way.

Two things could: the spec guard, which denies writes to the user's
references, and the space's .gitignore, which would make a mark untracked and
therefore invisible to the history (ADR 0016's lesson).
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "tools" / "guards" / "spec.py"
CONTOUR = ROOT / "contour"


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True)


class MarksAreWritableTest(unittest.TestCase):
    def setUp(self):
        self.space = Path(tempfile.mkdtemp()) / "widget"
        r = subprocess.run([sys.executable, str(CONTOUR), "init", "widget"],
                           cwd=str(self.space.parent), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def guard(self, path):
        # `tool_name` as well as the input, because the guard asks `lib.intent`
        # what the call means and the answer depends on which tool made it. A
        # PreToolUse event always carries both; a fixture that carried one was
        # passing by accident of the guard reading only the path.
        ev = json.dumps({"cwd": str(self.space), "tool_name": "Write",
                         "tool_input": {"file_path": str(path)}})
        return subprocess.run([sys.executable, str(GUARD)], input=ev,
                              capture_output=True, text=True,
                              env=dict(os.environ, CLAUDE_PROJECT_DIR=str(self.space)))

    def test_the_spec_guard_allows_a_write_to_marks_json(self):
        (self.space / "marks.json").write_text("[]\n")
        git(self.space, "add", "marks.json")
        self.assertEqual(self.guard(self.space / "marks.json").returncode, 0)

    def test_the_spec_guard_still_refuses_a_tracked_reference(self):
        (self.space / "refs" / "side.jpg").write_bytes(b"jpeg")
        git(self.space, "add", "refs/side.jpg")
        r = self.guard(self.space / "refs" / "side.jpg")
        self.assertEqual(r.returncode, 2)
        self.assertIn("refused", r.stderr)

    def test_a_fresh_space_does_not_ignore_marks_json(self):
        (self.space / "marks.json").write_text("[]\n")
        self.assertNotEqual(git(self.space, "check-ignore", "marks.json").returncode, 0)


if __name__ == "__main__":
    unittest.main()
