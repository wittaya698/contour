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


def stub_blender(dirpath, ok=True, crash=False):
    """A Blender that writes the report the launcher reads, names the stage it
    was asked for, and records it.

    `ok=False` is a verify-red check: the build saved, the spec was not met — so
    it is the *build* stage that reports red and a render of that build still
    succeeds. `crash` is a `build.py` that raised, which leaves no report at all
    and no geometry, and is a different event with a different sheet (ADR 0019,
    decision 27). The trace is how a test can tell what the launcher did.
    """
    verdict = "true" if ok else "false"
    script = dirpath / "blender-stub"
    lines = [
        "#!/bin/sh",
        f'echo "$@" >> "{dirpath / "stages"}"',
        'for a in "$@"; do last="$a"; done',
        "ok=true; code=0",
        f'if [ "$last" = build ]; then ok={verdict}; code={0 if ok else 1}; fi',
    ]
    if crash:
        lines.append("exit 1")                # no report: Blender died mid-stage
    else:
        lines += [
            'printf \'{"ok": %s, "lines": ["stub ran %s"], '
            '"results": [{"name": "stub", "ok": %s}]}\' '
            '"$ok" "$last" "$ok" > "$CONTOUR_REPORT"',
            "exit $code",
        ]
    script.write_text("\n".join(lines) + "\n")
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

    def stages(self):
        """Which stages the launcher ran, in order — one Blender process each."""
        trace = self.tmp / "stages"
        return [line.rsplit(" -- ", 1)[-1].split()[0]
                for line in trace.read_text().splitlines()] \
            if trace.exists() else []

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

    def test_a_green_check_renders_for_the_page(self):
        """Every build renders; only a checkpoint renders for the agent (ADR
        0019, decision 23). The sheet was rate-limited because it cost the
        agent's context, not because rendering is expensive — and a sheet going
        to a page costs no context at all, so the panel can be current."""
        r = self.run_contour("check")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.stages(), ["build", "render"])

    def test_a_verify_red_check_still_renders(self):
        """Red is the common state inside a fix loop, and a red verify has
        geometry: the build saved before verify judged it. The wrong model is
        exactly what the user needs to see, so the panel shows it. What must
        never be drawn is a scene that was never finished — that is the next
        test, and it is a different event."""
        r = self.run_contour("check", blender=stub_blender(self.tmp, ok=False))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.stages(), ["build", "render"])

    def test_the_check_report_says_nothing_about_the_render(self):
        """The render is for the page, and the page costs no context. If the
        check's report named it — or named the sheet — the agent would be
        invited to read a picture outside a checkpoint, which is the one thing
        decision 23 keeps intact while making the panel current."""
        r = self.run_contour("check")
        self.assertEqual(r.returncode, 0)
        self.assertIn("stub ran build", r.stdout)
        self.assertNotIn("render", r.stdout)
        self.assertNotIn("sheet", r.stdout)

    def test_a_build_that_never_finished_renders_nothing(self):
        """The most dangerous option available, refused: a picture of a model
        that has never existed, in the panel where every other picture is real.
        A `build.py` that raised leaves the scene unfinished and the previous
        `.blend` untouched, so there is nothing new to draw and drawing anyway
        would draw whatever half a scene happens to hold (ADR 0019, 27)."""
        r = self.run_contour("check", blender=stub_blender(self.tmp, crash=True))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.stages(), ["build"])


if __name__ == "__main__":
    unittest.main()
