"""Claude's span questions, one at a time (ADR 0022's answers, worded by ADR
0025 decision 1; issue 75).

While agent spans are unanswered, the canvas says *Claude has 4 questions
about your pictures* and steps through them: the reference zoomed on the
span, its number, and *Is this the seat?*. The three answers are adopt,
correct and reject underneath, through the functions the marks list calls;
*skip for now* moves on and sends nothing. The list stays the overview and
still answers. Read off the page's source, as `test_always.PageTest` does,
because there is no browser here.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class PageTest(unittest.TestCase):

    def setUp(self):
        from lib.canvas import PAGE
        self.page = PAGE.read_text(encoding="utf-8")
        found = re.search(r'<section id="questions"([^>]*)>(.*?)</section>', self.page, re.S)
        self.assertIsNotNone(found, "the page has no questions card")
        self.attrs, self.card = found.groups()

    def script(self, name):
        self.assertEqual(self.page.count(f"function {name}("), 1,
                         "declared once: a page script's later function of the same name wins")
        return self.page.split(f"function {name}(", 1)[1].split("\n}\n", 1)[0]

    def test_the_card_is_under_every_host_and_hidden_until_there_is_a_question(self):
        """Both hosts serve the answers (`lib/canvas.py`), so both ask."""
        self.assertNotIn("data-needs", self.attrs)
        self.assertIn("hidden", self.attrs)
        for part in ('class="count"', "<canvas", 'class="number"', 'class="asks"',
                     'class="eyed"'):
            self.assertIn(part, self.card)

    def test_it_counts_the_unanswered_and_asks_the_first_not_skipped(self):
        """The count is every unanswered agent span, skipped or not: skipping
        puts a question off, it does not answer it. Asked in the agent's own
        words for what the span measures."""
        chosen = self.script("asking")      # and run under node in test_asked
        self.assertIn("spanState(m) === 'unanswered'", chosen)
        self.assertIn("skipped.has(", chosen)
        asking = self.script("questions")
        self.assertIn("asking(marks, skipped)", asking)
        self.assertIn("'Claude has '", asking)
        self.assertIn("' about your pictures'", asking)
        self.assertIn("'Is this ' + mark.text + '?'", asking)
        self.assertIn("questions()", self.script("draw"), "redrawn with the list")

    def test_its_number_is_the_reading_the_span_is_linked_to(self):
        """`marks.spanned` links a span to the agent mark carrying its number
        (`reading`); the card shows that number and not the arithmetic after
        it, which the list still has."""
        asking = self.script("questions")
        self.assertIn("m.id === mark.reading", asking)
        self.assertIn("'.number'", asking)

    def test_a_by_eye_span_says_so(self):
        """ADR 0022, decision 3: no snap placed these ends, so the user is
        asked to look harder at them than at a snapped pair."""
        self.assertIn("Claude placed these ends by eye — check them closely.", self.card)
        self.assertIn("mark.placed !== 'by eye'", self.script("questions"))

    def test_each_answer_is_the_one_the_list_records(self):
        """Yes is adopt, *Let me move it* is correct, *Wrong thing…* is
        reject with a reason: the list's own functions, so the two cannot
        record an answer differently."""
        wired = self.script("askedAnswers")
        for button, act in ((".yes", "adoptSpan(asked)"), (".move", "correctSpan(asked)"),
                             (".wrong", "rejectSpan(asked)")):
            self.assertIn(f"'{button}', () => {act}", wired)

    def test_skip_moves_on_and_sends_nothing(self):
        wired = self.script("askedAnswers")
        skip = wired.split("'.skip'", 1)[1].split("\n", 1)[0]
        self.assertIn("skipped.add(asked.id)", skip)
        self.assertIn("questions()", skip)
        self.assertNotIn("ask(", skip)
        self.assertNotIn("answered(", skip)

    def test_the_reference_is_zoomed_on_the_span(self):
        """The user's own picture, fetched as the strip fetches it, cropped
        around the two ends with room either side, and the span drawn on it."""
        self.assertIn("zoom(mark)", self.script("questions"))
        zoom = self.script("zoom")
        self.assertIn("'/ref?name='", zoom)
        self.assertIn("mark.pixel", zoom)
        self.assertIn("mark.to", zoom)
        self.assertIn("drawImage(", zoom)
        self.assertIn("stroke()", zoom)


if __name__ == "__main__":
    unittest.main()
