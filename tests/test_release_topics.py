"""A release carries its topics (ADR 0030, decision 9; issue 119).

The `.glb` in `release/v<N>/` carries the model's topics as they stood at
release, as glTF `extras` on the root, and keeps them. A working `contour
export` carries none: a file handed over mid-work would ship words nobody
approved for release.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import one_run    # noqa: E402,F401  one suite run per machine (issue 94)

from lib import glb, revision, topics    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SMOKE = ROOT / "tests" / "data" / "smoke.glb"
"""`contour export` of the smoke fixture, committed: a working export as Blender
wrote it."""


class ReleaseTest(unittest.TestCase):

    def setUp(self):
        self.space = Path(tempfile.mkdtemp()) / "beaky"
        (self.space / ".contour").mkdir(parents=True)
        (self.space / ".contour" / "project").write_text("toolkit: stub\n")
        (self.space / "exports").mkdir()
        self.export = self.space / "exports" / "beaky.glb"
        shutil.copy(SMOKE, self.export)
        topics.answered(self.space, ["creature", "bird"], ["creature", "bird"])

    def contour(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "contour"), "release-glb", *args],
                              cwd=str(self.space), capture_output=True, text=True,
                              timeout=60)

    def released(self, n=1):
        return self.space / "release" / f"v{n}" / "beaky.glb"

    def test_a_release_carries_its_topics_read_back_after_the_round_trip(self):
        done = self.contour("v1")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        doc, _ = glb.load(self.released())
        self.assertEqual(doc["extras"]["topics"], ["creature", "bird"])
        self.assertEqual(glb.measure(self.released()), glb.measure(self.export))

    def test_a_working_export_of_the_same_model_has_no_topics_in_it(self):
        before = self.export.read_bytes()
        self.contour("v1")
        self.assertEqual(self.export.read_bytes(), before)
        doc, _ = glb.load(self.export)
        self.assertNotIn("topics", doc.get("extras", {}))

    def test_approving_a_topic_afterwards_changes_nothing_in_the_release(self):
        self.contour("v1")
        shipped = self.released().read_bytes()
        topics.answered(self.space, ["forest"], ["forest"])
        again = self.contour("v1")
        self.assertEqual(again.returncode, 1)
        self.assertIn("v1 is released", again.stdout)
        self.assertEqual(self.released().read_bytes(), shipped)

    def test_changing_a_topic_turns_no_check_red_and_asks_for_no_release(self):
        spec = self.space / "spec.yaml"
        spec.write_text("model: beaky\nrevision: 1\n")
        git = ["git", "-C", str(self.space), "-c", "user.name=t", "-c", "user.email=t@t"]
        for args in (["init", "-q"], ["add", "spec.yaml", "topics.json"],
                     ["commit", "-qm", "beaky"]):
            subprocess.run(git + args, check=True, capture_output=True)
        for args in (("add", "forest"), ("strike", "bird")):
            done = subprocess.run([sys.executable, str(ROOT / "contour"), "topics", *args],
                                  cwd=str(self.space), capture_output=True, text=True,
                                  timeout=60)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(spec.read_text(), "model: beaky\nrevision: 1\n")
        self.assertIsNone(revision.unbumped(self.space))
        self.assertFalse((self.space / "release").exists())

    def test_only_a_release_tag_is_released_and_only_an_export_carried(self):
        for tag in ("1", "v0", "v1-beta", "release"):
            done = self.contour(tag)
            self.assertEqual(done.returncode, 1, tag)
            self.assertIn("not a release tag", done.stdout)
        self.export.unlink()
        done = self.contour("v1")
        self.assertEqual(done.returncode, 1)
        self.assertIn("contour export", done.stdout)
        self.assertFalse((self.space / "release").exists())


if __name__ == "__main__":
    unittest.main()
