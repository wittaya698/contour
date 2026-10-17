"""The agent's words keep their formatting (issue 128).

The agent writes Markdown; the transcript drew the symbols that wrote it. The
console parses each `text` event into a tree of blocks and spans beside the
raw words, and the page draws the tree with `textContent` alone. Parsed here
and not on the page because there is no browser in this suite.
"""
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import prose                   # noqa: E402
from test_console import ConsoleCase    # noqa: E402


class SaidTest(ConsoleCase):

    def test_a_text_event_keeps_its_words_and_carries_a_tree(self):
        _, url = self.driven({"say": "the neck is **280**"})
        self.ask(url, "/run", {"prompt": "go on"})
        said = self.transcript(url, lambda ev: any(e["kind"] == "text" for e in ev))
        text, = [e for e in said if e["kind"] == "text"]
        self.assertEqual(text["text"], "the neck is **280**")
        self.assertEqual(text["blocks"], [{"kind": "paragraph", "spans": [
            {"text": "the neck is "}, {"text": "280", "bold": True}]}])


def paragraph(*spans):
    return {"kind": "paragraph", "spans": [
        s if isinstance(s, dict) else {"text": s} for s in spans]}


class ProseTest(unittest.TestCase):

    def test_a_blank_line_starts_a_paragraph_and_a_single_break_is_kept(self):
        self.assertEqual(prose.blocks("Two questions:\nwhat, and how big?\n\nThen a spec."), [
            paragraph("Two questions:\nwhat, and how big?"), paragraph("Then a spec.")])

    def test_a_fenced_spec_keeps_every_line_and_its_indentation(self):
        """The spec draft the new-space flow ends on, at the moment rule 1 asks
        the person to confirm it: one line of it run into the next is a spec
        nobody can read."""
        spec = ("revision: 1\nname: nexus-probe\n\ndimensions:\n"
                "  height: {value: 1200, tol: 20}\n  # a comment, not a heading\n"
                "parts:\n  - bell\n  - cone   # two spaces kept\n")
        said = prose.blocks(f"Here is the draft:\n\n```yaml\n{spec}```\n\nConfirm?")
        self.assertEqual(said, [paragraph("Here is the draft:"),
                                {"kind": "code", "lang": "yaml", "text": spec.rstrip("\n")},
                                paragraph("Confirm?")])

    def test_an_unclosed_marker_is_shown_as_written(self):
        """Not swallowed: an unclosed fence taking everything after it, or an
        unclosed `**` making the rest of the message bold, hides what the
        agent wrote behind what it forgot."""
        self.assertEqual(prose.blocks("the **neck is 280"), [paragraph("the **neck is 280")])
        self.assertEqual(prose.blocks("```yaml\nname: probe\n\nConfirm?"), [
            paragraph("```yaml\nname: probe"), paragraph("Confirm?")])

    def test_emphasis_and_code_are_styles_and_their_markers_go(self):
        self.assertEqual(prose.blocks("*nexus-probe* is _small_, see `build.py`"), [paragraph(
            {"text": "nexus-probe", "italic": True}, " is ", {"text": "small", "italic": True},
            ", see ", {"text": "build.py", "code": True})])
        self.assertEqual(prose.blocks("**a *b* c**"), [paragraph(
            {"text": "a ", "bold": True}, {"text": "b", "bold": True, "italic": True},
            {"text": " c", "bold": True})])

    def test_markers_that_are_not_emphasis_stay(self):
        """A name with underscores, a sum, and stars inside code are what they
        say, not styles."""
        for written in ("set spec_write_case and bone_roll_z", "2 * 3 * 4", "a ** b"):
            self.assertEqual(prose.blocks(written), [paragraph(written)], written)
        self.assertEqual(prose.blocks("`**not bold**`"), [paragraph(
            {"text": "**not bold**", "code": True})])

    def test_the_interview_is_one_list_with_its_options_under_each_question(self):
        """The new-space interview from the session that found this: five
        numbered questions, blank lines between them, options indented under
        each. It read as one paragraph."""
        said = prose.blocks(
            "A few questions about *nexus-probe*:\n"
            "1. **What is it?** A probe, a drone, or a satellite?\n"
            "   - bell-shaped body\n"
            "   - cone with fins\n"
            "\n"
            "2. **How big?**\n"
            "   - hand-sized\n"
            "   - person-sized\n"
            "\n"
            "3. **Rigged?** Yes or no.\n"
            "\n"
            "Answer what you can.")
        self.assertEqual(said, [
            paragraph("A few questions about ", {"text": "nexus-probe", "italic": True}, ":"),
            {"kind": "list", "items": [
                {"marker": "1.", "spans": [{"text": "What is it?", "bold": True},
                                           {"text": " A probe, a drone, or a satellite?"}],
                 "items": [{"marker": "-", "spans": [{"text": "bell-shaped body"}]},
                           {"marker": "-", "spans": [{"text": "cone with fins"}]}]},
                {"marker": "2.", "spans": [{"text": "How big?", "bold": True}],
                 "items": [{"marker": "-", "spans": [{"text": "hand-sized"}]},
                           {"marker": "-", "spans": [{"text": "person-sized"}]}]},
                {"marker": "3.", "spans": [{"text": "Rigged?", "bold": True},
                                           {"text": " Yes or no."}]}]},
            paragraph("Answer what you can.")])

    def test_a_list_keeps_its_own_numbers_and_a_wrapped_line(self):
        """Its numbers as the agent wrote them, not renumbered; a line
        indented under an item is more of it; and deeper than one level
        nests no deeper."""
        said = prose.blocks("3) third\n  wraps here\n7. seventh\n  * under\n      * deeper")
        self.assertEqual(said, [{"kind": "list", "items": [
            {"marker": "3)", "spans": [{"text": "third\nwraps here"}]},
            {"marker": "7.", "spans": [{"text": "seventh"}], "items": [
                {"marker": "*", "spans": [{"text": "under"}]},
                {"marker": "*", "spans": [{"text": "deeper"}]}]}]}])

    def test_a_heading_is_a_line_on_its_own_and_a_table_is_kept_as_written(self):
        table = "| span | reads |\n|---|--:|\n| m1 | 280 |"
        self.assertEqual(prose.blocks(f"## The neck\nIt measures:\n{table}\nso it holds."), [
            {"kind": "heading", "spans": [{"text": "The neck"}]},
            paragraph("It measures:"),
            {"kind": "code", "lang": "", "text": table},
            paragraph("so it holds.")])
        self.assertEqual(prose.blocks("#3 is next, and | is a pipe"),
                         [paragraph("#3 is next, and | is a pipe")])

    def test_a_link_is_its_text_and_where_it_points_and_never_a_link(self):
        """The agent chooses the URL, so the page shows it rather than
        letting a click go there."""
        self.assertEqual(prose.blocks("see [x](javascript:alert(1)) and [the ADR](docs/adr/0025.md)"),
                         [paragraph("see x (javascript:alert(1)) and the ADR (docs/adr/0025.md)")])

    def test_markup_in_the_words_is_text(self):
        written = "<script>alert(1)</script> <img src=x onerror=alert(1)>"
        self.assertEqual(prose.blocks(written), [paragraph(written)])

    def test_no_word_is_ever_lost(self):
        """Whatever the agent writes, every letter and digit of it is in the
        tree, in order, and nothing is added: only markers go. Random text
        from the characters this reads, plus words, many times over."""
        pieces = ["**", "*", "_", "__", "`", "```", "~~~", "#", "## ", "- ", "* ", "1. ",
                  "2) ", "|", "|---|", "[", "]", "(", ")", "\n", "\n\n", "  ", "    ",
                  "neck", "a1", "x_y", "280", "yaml", " "]
        rng = random.Random(128)
        for _ in range(3000):
            written = "".join(rng.choice(pieces) for _ in range(rng.randint(0, 40)))
            self.assertEqual(alnum(drawn(prose.blocks(written))), alnum(written), repr(written))


def drawn(tree):
    """Every string the page would put on screen from `tree`, in order."""
    if isinstance(tree, list):
        return "".join(drawn(t) for t in tree)
    return "".join(v if k in ("text", "marker", "lang") else drawn(v)
                   for k, v in tree.items() if isinstance(v, (str, list)) and k != "kind")


def alnum(text):
    return "".join(c for c in text if c.isalnum())


class PageTest(unittest.TestCase):

    def test_the_page_draws_the_tree_and_never_markup(self):
        """Read from the source, as every page test is: there is no browser in
        this suite. The page draws the tree, sets no markup from anything (so
        an agent's `<script>` stays the text the tree says it is), and makes
        no link, so a URL the agent chose is shown and never followed."""
        page = (ROOT / "lib" / "canvas.html").read_text()
        self.assertTrue("words(event.blocks" in page, "the page does not draw the tree")
        for markup in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
            self.assertFalse(markup in page, f"the page sets markup with {markup}")
        drawing = page.split("function words(", 1)[1].split("\nfunction ", 1)[0]
        self.assertFalse("'a'" in drawing, "the agent's words make a link")


if __name__ == "__main__":
    unittest.main()
