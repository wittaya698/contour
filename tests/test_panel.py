"""The sheet panel, labelled: which build the picture is of (ADR 0019, 13/23/27).

The sheet changes only when a build finishes, so the panel says which build it
was drawn from. `views.json` already carries that fingerprint, so a sheet the
build has moved past is labelled rather than quietly authoritative — the same
reasoning ADR 0018 used to refuse resolving a stale sheet, moved to where the
user is looking.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import anchor
from lib.canvas import Canvas

from client import get
from test_launcher import stub_blender

CONTOUR = Path(__file__).resolve().parent.parent / "contour"

VIEWS = [{"label": "front", "tile": [0, 0, 512, 512]}]


class PanelTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.out = self.tmp / "out"
        self.out.mkdir()
        self.sheet = self.tmp / "sheet.png"
        self.marks = self.tmp / "marks.json"
        # Named after the space, the way a real one is (ADR 0015).
        self.blend = self.out / f"{self.tmp.name}.blend"
        self.views = self.out / "views.json"

    def built(self, geometry=b"a blend"):
        """A build on disk, and a sheet drawn from it — what every check that
        got as far as saving leaves behind."""
        self.blend.write_bytes(geometry)
        self.sheet.write_bytes(b"\x89PNG\r\n\x1a\npixels")
        anchor.record(self.views, [1024, 1024], VIEWS, self.blend)

    def check(self, **kw):
        """`contour check` in this space, with Blender stubbed. What the page
        reads afterwards is what the launcher left behind."""
        (self.tmp / ".contour").mkdir(exist_ok=True)
        (self.tmp / ".contour" / "project").write_text("toolkit: stub\n")
        return subprocess.run(
            [sys.executable, str(CONTOUR), "check"], cwd=str(self.tmp),
            env=dict(os.environ, BLENDER=str(stub_blender(self.tmp, **kw))),
            capture_output=True, text=True, timeout=60)

    def panel(self):
        canvas = Canvas(sheet=self.sheet, marks=self.marks, views=self.views,
                        blend=self.blend,
                        verdict=self.tmp / ".contour" / "last-build.json")
        self.addCleanup(canvas.stop)
        canvas.start()
        return get(canvas, "/sheet.json")[1]

    def test_the_panel_names_the_build_the_sheet_was_drawn_from(self):
        self.built()
        panel = self.panel()
        self.assertEqual(panel["build"], anchor.fingerprint(self.blend))
        self.assertTrue(panel["current"], "a fresh sheet is of the build on disk")

    def test_a_sheet_the_build_has_moved_past_says_it_is_not_current(self):
        """The label's whole job. ADR 0018 already refuses to resolve marks
        against a stale sheet; this says so where the user is looking, instead
        of at the moment they press Done."""
        self.built()
        drawn = self.panel()["build"]
        self.blend.write_bytes(b"a later blend")
        panel = self.panel()
        self.assertFalse(panel["current"])
        self.assertEqual(panel["build"], drawn,
                         "the label names the build the sheet is of, not the "
                         "one the sheet is not")

    def test_a_space_that_has_never_built_serves_an_empty_panel(self):
        """No sheet, no `views.json`, no build: the first state every space is
        in. The panel is empty and says so, and the picture is simply missing
        rather than a request that raises inside the server."""
        panel = self.panel()
        self.assertIsNone(panel["build"])
        self.assertFalse(panel["current"])
        canvas = Canvas(sheet=self.sheet, marks=self.marks, views=self.views,
                        blend=self.blend)
        self.addCleanup(canvas.stop)
        canvas.start()
        with self.assertRaises(urllib.error.HTTPError) as caught:
            get(canvas, "/sheet.png")
        self.assertEqual(caught.exception.code, 404)
        caught.exception.close()      # an HTTPError is a response, and holds a socket

    def test_a_build_that_failed_leaves_the_last_good_sheet_labelled(self):
        """Red is the common state inside a fix loop, and a build that raised
        leaves the *previous* `.blend` on disk — so the two fingerprints agree
        and say `current` about a picture of a build that never finished. The
        verdict is what the page reads instead (ADR 0019, decision 29)."""
        self.built()
        self.assertTrue(self.panel()["current"])
        self.assertEqual(self.check(crash=True).returncode, 1)
        panel = self.panel()
        self.assertFalse(panel["current"])
        self.assertEqual(panel["build"], anchor.fingerprint(self.blend),
                         "still the build it is a picture of")
        self.assertIn("last build failed", panel["why"])

    def test_a_failed_build_says_that_marks_were_not_resolved(self):
        """A mark is born with a pixel and becomes a pin when a ray lands. No
        build means no rays, and leaving those marks silently pending returns
        ADR 0018's window through a side door — a mark that looks pinned and is
        not. The page says which it is (ADR 0019, decision 29)."""
        self.built()
        self.marks.write_text(json.dumps(
            [{"id": "m1", "view": "front", "pixel": [3, 4], "text": "too tall",
              "author": "user", "status": "open"}]))
        self.assertEqual(self.check(crash=True).returncode, 1)
        self.assertEqual(self.panel()["marks"],
                         "marks not resolved: last build failed")

    def test_nothing_is_said_about_marks_there_were_none_of(self):
        """ADR 0018's rule, kept: one line when there is something open and
        nothing at zero. A sentence that appears on every failed build whether or
        not it is about anything is furniture, and the next one nobody reads is
        the one that mattered."""
        self.built()
        self.assertEqual(self.check(crash=True).returncode, 1)
        panel = self.panel()
        self.assertFalse(panel["current"], "the build still failed")
        self.assertIsNone(panel["marks"])

    def test_the_panel_is_told_the_build_failed_and_never_what_failed(self):
        """No failing check is overlaid on the picture, and the page could not
        overlay one if it tried: it is never told which check failed.

        Refused because a check knows a number, not a location — so overlays
        would appear for some failures and not others, and teach the reader to
        distrust their absence. The report is the launcher's answer and the
        transcript is where it lands; the sheet stays a picture (ADR 0019, 27).
        """
        self.built()
        red = self.check(ok=False)
        self.assertEqual(red.returncode, 1)
        self.assertIn("stub ran build", red.stdout, "the report still says it")
        said = " ".join(str(v) for v in self.panel().values())
        for leak in ("stub", "FAIL", "verify"):
            self.assertNotIn(leak, said, f"the panel was handed {leak!r}")

    def test_the_launchers_own_canvas_labels_the_sheet(self):
        """`contour canvas` shows the same picture and can be just as wrong about
        which build it is of — ADR 0018 already refuses to resolve marks against a
        stale sheet, and this is that refusal said at the start instead of at the
        moment the user presses Done. The label belongs to the canvas, so both
        hosts have it and it cannot come to mean one thing under each.
        """
        self.built()
        (self.tmp / ".contour").mkdir(exist_ok=True)
        (self.tmp / ".contour" / "project").write_text("toolkit: stub\n")
        quiet = self.tmp / "no-browser"
        quiet.write_text("#!/bin/sh\nexit 0\n")      # $BROWSER, so none opens
        quiet.chmod(0o755)
        proc = subprocess.Popen(
            [sys.executable, str(CONTOUR), "canvas"], cwd=str(self.tmp),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            env=dict(os.environ, BROWSER=str(quiet)))
        self.addCleanup(proc.kill)
        url = re.search(r"http://\S+", proc.stdout.readline()).group(0)
        origin, token = url.split("/?")[0], url.split("t=")[1]
        req = urllib.request.Request(origin + "/sheet.json",
                                     headers={"X-Contour-Token": token})
        with urllib.request.urlopen(req, timeout=10) as r:
            said = json.loads(r.read())
        self.assertEqual(said["build"], anchor.fingerprint(self.blend))
        self.assertTrue(said["current"])


if __name__ == "__main__":
    unittest.main()
