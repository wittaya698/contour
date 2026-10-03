"""Rule 1's span clause, and what the skills say about numbers from a
reference (ADR 0022, decisions 6, 7 and 9; issue 46).

Text, tested as text: the clause is a rule, and a rule copied into a space is
only the same rule if it is the same words.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CLAUSE = ("A measurement read off a reference is a **span** — the user's, or an "
          "agent span — and the proposal names it. A number from a reference with "
          "no span behind it is not an argument, and a by-eye agent span argues "
          "nothing until the user has answered it.")
"""The wording the user approved on 2026-09-30, as ADR 0022 records it."""

RULES = (ROOT / "CLAUDE.md", ROOT / "templates" / "space" / "CLAUDE.md")
SKILLS = (ROOT / ".claude" / "skills" / "new-space" / "SKILL.md",
          ROOT / "templates" / "space" / ".claude" / "skills" / "build-model" / "SKILL.md")


def flat(path):
    """The file with its line breaks and indents folded to single spaces, so
    the clause matches however it is wrapped."""
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


class ClauseTest(unittest.TestCase):

    def test_rule_one_carries_the_approved_clause_in_the_toolkit_and_the_template(self):
        for path in RULES:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIn(CLAUSE, flat(path))

    def test_the_adr_records_the_same_words(self):
        adr = ROOT / "docs" / "adr" / "0022-the-agent-reads-the-references-in-spans.md"
        self.assertIn(CLAUSE, flat(adr).replace("> ", ""))


class SkillsTest(unittest.TestCase):
    """Drafting a spec and arguing a revision both say how a number from a
    reference is proposed."""

    def test_both_skills_state_the_three_sources(self):
        for path in SKILLS:
            with self.subTest(path=path.relative_to(ROOT)):
                text = flat(path)
                for source in ("a span, by id", "the user, who gave it",
                               "*not measurable*"):
                    self.assertIn(source, text)

    def test_both_skills_state_the_two_span_rules(self):
        for path in SKILLS:
            with self.subTest(path=path.relative_to(ROOT)):
                text = flat(path)
                self.assertIn("unanswered **snapped** span", text)
                self.assertIn("the agent's own reading", text)
                self.assertIn("unanswered **by-eye** span", text)
                self.assertIn("is not proposed", text)
                self.assertIn("contour measure --standing", text)

    def test_both_skills_name_the_worksheet_checkpoint(self):
        for path in SKILLS:
            with self.subTest(path=path.relative_to(ROOT)):
                text = flat(path)
                self.assertIn("contour worksheet", text)
                self.assertIn("once", text)
                self.assertIn("before you propose", text)

    def test_the_new_space_skill_names_contour_measure(self):
        text = flat(SKILLS[0])
        self.assertIn("contour measure refs/", text)
        self.assertIn("--by-eye", text)


class StaleDepthTest(unittest.TestCase):
    """ADR 0017 measured `beaky`'s reference depth at 597, inside 600 ±20, and
    found the conclusion drawn from *about 620* inverted."""

    def test_no_rule_or_skill_states_the_620_depth(self):
        for path in RULES + SKILLS:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("620", path.read_text(encoding="utf-8"))

    def test_no_skill_says_beaky_s_contract_was_wrong_about_depth(self):
        for path in RULES + SKILLS:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("the contract was not", flat(path))


if __name__ == "__main__":
    unittest.main()
