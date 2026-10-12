"""The first green build proposes (ADR 0030, decision 4; issue 117).

Once in a model's life, unprompted: `contour check` says so on the first green
build, the first moment the agent knows what the model is, and never again.
Run through the launcher with Blender stubbed, as the panel tests run it.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_launcher import stub_blender    # noqa: E402

LINE = "first green: propose topics to find this model by"


class FirstGreenTest(unittest.TestCase):

    def setUp(self):
        self.space = Path(tempfile.mkdtemp())
        (self.space / ".contour").mkdir()
        (self.space / ".contour" / "project").write_text("toolkit: stub\n")

    def check(self, ok=True):
        """`contour check` here; what the agent reads is its report."""
        r = subprocess.run(
            [sys.executable, str(ROOT / "contour"), "check"], cwd=str(self.space),
            env=dict(os.environ, BLENDER=str(stub_blender(self.space, ok=ok))),
            capture_output=True, text=True, timeout=60)
        return r.stdout

    def test_a_new_spaces_first_green_build_says_to_propose(self):
        self.assertEqual(self.check().count(LINE), 1)

    def test_a_later_green_build_says_nothing(self):
        self.check()
        self.assertNotIn(LINE, self.check())

    def test_red_then_green_after_the_first_green_says_nothing(self):
        self.check()
        self.check(ok=False)
        self.assertNotIn(LINE, self.check())

    def test_a_space_already_green_before_topics_is_not_prompted(self):
        """Every space today: green on a toolkit that kept no stamp. Issue 118
        labels those; their next green is stamped and says nothing."""
        self.check()
        (self.space / ".contour" / "first-green").unlink()
        self.assertNotIn(LINE, self.check())
        self.check(ok=False)
        self.assertNotIn(LINE, self.check())

    def test_a_red_first_build_says_nothing_and_the_first_green_does(self):
        self.assertNotIn(LINE, self.check(ok=False))
        self.assertEqual(self.check().count(LINE), 1)


class SkillTest(unittest.TestCase):
    """What the agent does on reading the line: the build-model skill's."""

    def test_the_skill_says_what_the_line_asks_under_a_console_and_a_terminal(self):
        skill = (ROOT / "templates" / "space" / ".claude" / "skills" / "build-model"
                 / "SKILL.md").read_text(encoding="utf-8")
        said = skill.split("## Topics")[1].split("\n## ")[0]
        self.assertIn("first green", said)
        self.assertIn("topics_propose", said)
        self.assertIn("contour topics add", said)
        self.assertIn("only when asked", said)


if __name__ == "__main__":
    unittest.main()
