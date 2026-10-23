"""An approved guess keeps its name (ADR 0034, decision 4; issue 148).

A size Claude guessed and the user approved is wrong, if it is wrong, by the
same factor everywhere, and every check stays green (ADR 0016). So the anchor
span, the next place the size is used, asks with where it came from: *is this
the 300 mm width you approved from Claude's guess?* A size the user typed asks
as before.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import form, marks, span  # noqa: E402
from lib.canvas import PAGE  # noqa: E402
from test_camera import SIZE, STEEP, edge, picture  # noqa: E402
from test_found import function  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEEN = picture(STEEP)
GUESSED = "is this the 300 mm width you approved from Claude's guess?"
TOLD = "is this the width you told me, 300 mm?"


def answers(source):
    return [{"question": "What is it?", "answer": "a box", "source": "guess"},
            {"question": "How big is it in real life?", "answer": "300 mm wide",
             "source": source, "is_size": True}]


class AnchorAskedTest(unittest.TestCase):

    def setUp(self):
        self.space = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.space, True)
        (self.space / ".contour").mkdir()
        self.spec = self.space / "spec.yaml"
        self.spec.write_text("model: m\nrevision: 1\ndimensions:\n"
                             "  width: { value: 300, tol: 3 }\n")
        self.marks = self.space / "marks.json"

    def asked(self):
        """What the anchor span asks, claimed as `contour measure --claims`
        claims it."""
        claims = span.claimed(self.spec, "width")
        span.by_eye(self.marks, "box.png", edge(SEEN, (0, 0, 1), (1, 0, 1)), None,
                    "the box, end to end", claims=claims, size=SIZE)
        return marks.load(self.marks)[-1]["text"]

    def test_a_size_approved_from_claudes_guess_is_asked_as_one(self):
        form.keep(self.space, "r1", answers("guess"))
        said = self.asked()
        self.assertIn(GUESSED, said)
        self.assertNotIn("you told me", said)

    def test_a_size_the_user_typed_or_the_chat_said_asks_as_before(self):
        for source in ("yours", "chat"):
            with self.subTest(source=source):
                shutil.rmtree(self.space / ".contour")
                (self.space / ".contour").mkdir()
                self.marks.unlink(missing_ok=True)
                form.keep(self.space, "r1", answers(source))
                self.assertIn(TOLD, self.asked())

    def test_with_no_form_approved_it_asks_as_before(self):
        """A space made before the form, or whose size came on the launch
        line."""
        self.assertIn(TOLD, self.asked())

    def test_the_latest_size_approved_is_the_one_asked_about(self):
        """A guess the user later typed over is theirs."""
        form.keep(self.space, "r1", answers("guess"))
        form.keep(self.space, "r2", answers("yours")[1:])
        self.assertIn(TOLD, self.asked())


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class CardTest(unittest.TestCase):
    """The canvas card asks the anchor span's question in its own words, run
    under node as the browser gets it."""

    def phrased(self, claims):
        mark = {"text": "the box, end to end", "claims": claims}
        js = (function(PAGE.read_text(encoding="utf-8"), "phrased")
              + f"\nconsole.log(phrased({json.dumps(mark)}));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout.strip()

    def test_the_card_names_an_approved_guess(self):
        self.assertEqual(self.phrased({"dimension": "width", "mm": 300, "source": "guess"}),
                         "Is this the box, end to end \u2014 the 300 mm width you "
                         "approved from Claude's guess?")
        self.assertEqual(self.phrased({"dimension": "width", "mm": 300}),
                         "Is this the box, end to end \u2014 the width you told me, 300 mm?")


GUESSED_ANCHOR = ("A guessed anchor is the user's only once approved, and is named "
                  "*Claude's guess, approved* wherever it is used.")
"""Rule 1's fourth source, as ADR 0034 decision 4 has it: one sentence, the
same words in the toolkit, the space template and the new-space skill."""


def flat(path):
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


class RuleOneTest(unittest.TestCase):
    """Text, tested as text, as `test_rule_one_spans` tests the span clause."""

    SAYS = (ROOT / "CLAUDE.md", ROOT / "templates" / "space" / "CLAUDE.md",
            ROOT / ".claude" / "skills" / "new-space" / "SKILL.md")

    def test_rule_one_and_the_skill_say_the_same_thing(self):
        for path in self.SAYS:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIn(GUESSED_ANCHOR, flat(path))

    def test_none_of_them_says_the_anchor_is_never_guessed(self):
        for path in self.SAYS:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("Never guess it", flat(path))
                self.assertNotIn("an anchor they give you,", flat(path))

    def test_a_spec_writes_sources_list_the_fourth(self):
        skill = flat(self.SAYS[2])
        sources = skill.split("**Every number in the draft names its source**", 1)[1]
        self.assertIn("there are four", sources[:40])
        self.assertIn("*Claude's guess, approved*", sources.split("A number from", 1)[0])


if __name__ == "__main__":
    unittest.main()
