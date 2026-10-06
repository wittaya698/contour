"""Claude speaks in plain words (ADR 0025, decisions 2 and 3; issue 78).

The agent speaks to the user by the tiers `docs/CONTEXT.md` gives under *On the
page*, in a console run and in a terminal session alike. It reaches the agent
where everything does: the space's own `CLAUDE.md` and skills. Text, tested as
text, as `test_rule_one_spans` tests rule 1's clause.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from console.server import NEW_SPACE    # noqa: E402

SPACE = ROOT / "templates" / "space"
RULES = SPACE / "CLAUDE.md"
SKILLS = (ROOT / ".claude" / "skills" / "new-space" / "SKILL.md",
          SPACE / ".claude" / "skills" / "build-model" / "SKILL.md",
          SPACE / ".claude" / "skills" / "release-model" / "SKILL.md")


def flat(text):
    return re.sub(r"\s+", " ", text)


def section(text, heading):
    """The body under `## heading`, up to the next `## `."""
    return text.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


class VoiceTest(unittest.TestCase):

    def test_the_space_rules_say_how_to_speak_to_the_user(self):
        voice = flat(section(RULES.read_text(encoding="utf-8"), "Speaking to the user"))
        self.assertIn("*Save this version?*", voice)
        for shown in ("reference", "sheet", "mark", "span", "spec"):
            self.assertIn(shown, voice)
        self.assertIn("commit messages", voice)

    def test_every_term_it_renames_is_one_the_glossary_has_sorted(self):
        """One vocabulary, not a second kept in step by hand: a term the agent
        says in other words is one *On the page* has put in a tier."""
        context = (ROOT / "docs" / "CONTEXT.md").read_text(encoding="utf-8")
        sorted_ = flat(section(context, "On the page")).replace("**", "").lower()
        voice = section(RULES.read_text(encoding="utf-8"), "Speaking to the user")
        renamed = re.findall(r"^\s*- \*\*([\w -]+)\*\*(?: / \*\*([\w -]+)\*\*)? →", voice, re.M)
        self.assertGreater(len(renamed), 5)
        for term in (t for pair in renamed for t in pair if t):
            with self.subTest(term=term):
                self.assertIn(term.lower(), sorted_)

    def test_every_skill_that_asks_the_user_asks_in_those_words(self):
        for path in SKILLS:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIn("Speaking to the user", path.read_text(encoding="utf-8"))

    def test_asking_to_commit_is_asking_to_save_this_version(self):
        for path in SKILLS[1:]:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIn("*Save this version?*", flat(path.read_text(encoding="utf-8")))


class InterviewTest(unittest.TestCase):
    """A new model opens on the agent's interview, in plain words."""

    def test_the_first_prompt_asks_in_plain_words(self):
        for asked in ("How big is it in real life?", "Where will it be seen?"):
            self.assertIn(asked, NEW_SPACE)

    def test_the_first_prompt_never_says_anchor(self):
        self.assertNotIn("anchor", NEW_SPACE.lower())

    def test_the_first_prompt_no_longer_asks_to_save_the_references(self):
        """They are in `refs/` before the console opens (issue 65)."""
        self.assertNotIn("Save the user's reference", NEW_SPACE)
        self.assertIn("already in refs/", NEW_SPACE)

    def test_tolerances_and_the_budget_are_the_agents_own_proposals(self):
        said = flat(NEW_SPACE)
        self.assertIn("tolerances and the triangle budget yourself", said)
        self.assertIn("say they are yours", said)

    def test_the_skill_interviews_the_same_way(self):
        intent = section(SKILLS[0].read_text(encoding="utf-8"), "1. Get the intent first, in plain words")
        for asked in ("How big is it in real life?", "Where will it be seen?"):
            self.assertIn(asked, intent)
        self.assertIn("Never ask the user for a tolerance or a triangle budget", flat(intent))


if __name__ == "__main__":
    unittest.main()
