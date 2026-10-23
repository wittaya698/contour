"""Old readings are read again (ADR 0032, decision 7; issue 142).

A reading made by the foreground box carries the scale it was read at, and
says so in its text: *640 mm ±3 mm  (213 px at 3.000 mm/px)*. When its
reference's foundations are answered it is read again through the camera.
Nothing is deleted: the old reading is closed as superseded, as a
correction's is, and the new one says which it replaced. The spec never moves
on its own; a number that moved is the agent's to propose.

The reference is a box projected through a known camera (`test_camera`).
"""
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import marks, span  # noqa: E402
from lib.canvas import PAGE  # noqa: E402
from client import post  # noqa: E402
from test_anchor_span import SEEN  # noqa: E402
from test_camera import BOX, edge  # noqa: E402
from test_foundations import ReadAgainCase  # noqa: E402
from test_found import function  # noqa: E402

READS = re.compile(r"(\d+) mm ±(\d+) mm")
OLD_SCALE = 0.5
"""mm per pixel, as the foreground box once gave it: wrong on purpose, so the
old number and the new one differ."""


class OldCase(ReadAgainCase):

    def old_span(self, *corners, text="the box's depth"):
        """A span drawn before the camera, at a flat scale."""
        span.by_eye(self.marks, "box.png", edge(SEEN, *corners), OLD_SCALE, text)
        return [m for m in marks.load(self.marks) if m.get("to")][-1]["id"]


class ReadAgainTest(OldCase):

    def test_answering_the_last_foundation_reads_an_old_reading_again(self):
        self.directions()
        anchor = self.anchor(answer=False)
        drawn = self.old_span((1, 0, 1), (1, 1, 1))
        old = span.marked(self.marks, drawn)["reading"]
        post(self.canvas, "/adopt", {"id": anchor})
        now = span.marked(self.marks, drawn)
        said = span.marked(self.marks, now["reading"])
        got = READS.search(said["text"])
        self.assertIsNotNone(got, said["text"])
        self.assertLessEqual(abs(int(got[1]) - BOX[1]), int(got[2]) + 1)
        self.assertEqual(said["was"], old)
        kept = span.marked(self.marks, old)
        self.assertEqual((kept["status"], kept["superseded"]), ("closed", True))
        self.assertNotIn("scale", now)

    def test_until_the_foundations_are_answered_the_old_reading_stands(self):
        """Pixels would replace a number with none: it waits, labelled."""
        self.directions(answer=False)
        anchor = self.anchor(answer=False)
        drawn = self.old_span((1, 0, 1), (1, 1, 1))
        before = span.marked(self.marks, drawn)
        post(self.canvas, "/adopt", {"id": anchor})
        self.assertEqual(span.marked(self.marks, drawn), before)
        self.assertTrue(marks.is_open(span.marked(self.marks, before["reading"])))

    def test_undoing_the_answer_puts_the_old_reading_back(self):
        self.directions()
        anchor = self.anchor(answer=False)
        self.old_span((1, 0, 1), (1, 1, 1))
        before = self.marks.read_bytes()
        post(self.canvas, "/adopt", {"id": anchor})
        post(self.canvas, "/unanswer", {"id": anchor})
        self.assertEqual(self.marks.read_bytes(), before)


class ProposedTest(OldCase):
    """The spec never moves on its own: the agent is handed the span, the old
    number and the new, which is a proposal's argument (rule 1, ADR 0016)."""

    def read_again(self):
        self.directions()
        anchor = self.anchor(answer=False)
        drawn = self.old_span((1, 0, 1), (1, 1, 1))
        old = span.marked(self.marks, drawn)["reading"]
        post(self.canvas, "/adopt", {"id": anchor})
        return drawn, old

    def test_standing_says_the_new_number_and_the_old_it_replaced(self):
        drawn, old = self.read_again()
        said = "\n".join(span.standing(self.marks, drawn)["lines"])
        new = READS.search(said)
        self.assertLessEqual(abs(int(new[1]) - BOX[1]), int(new[2]) + 1, said)
        self.assertIn(f"was 123 mm \u00b11 mm, made by the foreground box ({old})", said)

    def test_the_spec_beside_the_marks_is_not_written(self):
        spec = self.tmp / "spec.yaml"
        spec.write_text("model: m\nrevision: 1\ndimensions:\n  depth: { value: 123, tol: 3 }\n")
        before = spec.read_bytes()
        self.read_again()
        self.assertEqual(spec.read_bytes(), before)


OLD = "span m5: 123 mm \u00b11 mm  (246 px at 0.500 mm/px)  by eye: the bar covers it"


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class LabelTest(unittest.TestCase):
    """An old reading says so on the card and in the list."""

    def run_page(self, names, expression, **given):
        page = PAGE.read_text(encoding="utf-8")
        js = ("".join(function(page, n) for n in names)
              + "".join(f"const {k} = {json.dumps(v)};\n" for k, v in given.items())
              + f"console.log(JSON.stringify({expression}));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_the_card_says_an_old_number_was_made_the_old_way(self):
        said = self.run_page(["oldWay", "plainly", "numbered"], "numbered(text)", text=OLD)
        self.assertEqual(said["number"], "123 mm \u00b11 mm")
        self.assertIn("made the old way, by the foreground box", said["why"])

    def test_only_a_reading_at_a_flat_scale_is_the_old_way(self):
        said = self.run_page(["oldWay"], "texts.map(oldWay)", texts=[
            OLD, "span m5: 200 mm \u00b16 mm  (through the camera, along y, against m4)",
            "span m5: 115 px \u00b12 px  (waits on m4, the anchor span, being answered)"])
        self.assertEqual(said, [True, False, False])


class ListTest(unittest.TestCase):

    def test_the_list_labels_an_old_reading_and_one_read_again(self):
        """The list is the DOM, built by `draw`: its script is read, as
        `test_questions` reads the card's."""
        drawn = function(PAGE.read_text(encoding="utf-8"), "draw")
        self.assertIn("oldWay(mark.text)", drawn)
        self.assertIn("made the old way, by the foreground box", drawn)
        self.assertIn("mark.superseded", drawn)


class SkillTest(unittest.TestCase):

    def test_the_skill_says_a_number_that_moved_is_proposed(self):
        skill = (Path(__file__).resolve().parent.parent / "templates" / "space" / ".claude"
                 / "skills" / "build-model" / "SKILL.md").read_text(encoding="utf-8")
        skill = " ".join(skill.split())
        self.assertIn("made the old way", skill)
        self.assertIn("contour measure --standing", skill)
        self.assertIn("moved by more than its ±", skill)


if __name__ == "__main__":
    unittest.main()
