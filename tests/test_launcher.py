"""The launcher, run as the user runs it.

Blender is stubbed: `contour check` shells out to $BLENDER and reads the JSON
report it leaves behind, so a four-line shell script stands in for it and these
stay fast. What is under test is the launcher's own behaviour around that call,
not Blender's.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTOUR = ROOT / "contour"


def stub_blender(dirpath, ok=True):
    rep = json.dumps({"ok": ok, "lines": ["ok   build  stub" if ok
                                          else "FAIL verify  stub"]})
    script = dirpath / "blender-stub"
    script.write_text(f"#!/bin/sh\nprintf '%s' '{rep}' > \"$CONTOUR_REPORT\"\n"
                      f"exit {0 if ok else 1}\n")
    script.chmod(0o755)
    return script


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.space = self.tmp / "widget"
        (self.space / ".contour").mkdir(parents=True)
        (self.space / ".contour" / "project").write_text("toolkit: stub\n")

    def run_contour(self, *args, cwd=None, blender=None):
        env = dict(os.environ, BLENDER=str(blender or stub_blender(self.tmp)))
        return subprocess.run([sys.executable, str(CONTOUR), *args],
                              cwd=str(cwd or self.space), env=env,
                              capture_output=True, text=True, timeout=60)

    def mark(self, status="open"):
        path = self.space / "marks.json"
        stored = json.loads(path.read_text()) if path.exists() else []
        stored.append({"id": f"m{len(stored) + 1}", "view": "front",
                       "pixel": [1, 2], "text": "x", "author": "user",
                       "status": status})
        path.write_text(json.dumps(stored))

    def test_canvas_outside_a_model_space_says_so_and_fails(self):
        r = self.run_contour("canvas", cwd=self.tmp)
        self.assertEqual(r.returncode, 2)
        self.assertIn("not in a model space", r.stderr)

    def test_check_reports_open_marks(self):
        self.mark()
        self.mark()
        r = self.run_contour("check")
        self.assertEqual(r.returncode, 0)
        self.assertIn("2 marks open", r.stdout)

    def test_check_says_nothing_about_marks_when_none_are_open(self):
        self.mark(status="closed")
        r = self.run_contour("check")
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("open", r.stdout)

    def test_the_marks_line_never_changes_the_exit_code(self):
        self.mark()
        red = self.run_contour("check", blender=stub_blender(self.tmp, ok=False))
        self.assertEqual(red.returncode, 1)
        self.assertIn("1 mark open", red.stdout)

    def test_a_green_check_leaves_every_mark_exactly_as_it_was(self):
        """Only the user closes a mark. Green does not dispose of a finding —
        a mark exists precisely because the spec did not catch the thing."""
        self.mark()
        self.mark(status="closed")
        before = (self.space / "marks.json").read_bytes()
        r = self.run_contour("check")
        self.assertEqual(r.returncode, 0)
        self.assertEqual((self.space / "marks.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
