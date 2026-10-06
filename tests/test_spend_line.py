"""Spend is a quiet line (ADR 0025, decision 9; issue 73).

*12 turns*, and, when gates cost turns, *3 stops cost 4 extra turns*, linking
to the list of what runs without asking — ADR 0019 decision 37's *informed
act* made one click long. The tokens sit behind a click, in the units
`tools/tokens.py` reports in. Still nothing before a turn is spent, and still
no limit (`test_console.SpendTest` holds both).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from test_console import ConsoleCase    # noqa: E402


class FigureTest(ConsoleCase):

    def spent(self, *script):
        """The last running total a run put on the transcript."""
        _, url = self.driven(*script, space=self.space())
        self.ask(url, "/run", {"prompt": "make it taller"})
        for _ in [s for s in script if "call" in s]:
            waiting, _ = self.gate(url)
            self.ask(url, "/verdict", {"id": waiting["id"], "allow": True})
        said = self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        return [e for e in said if e["kind"] == "spend"][-1]

    def test_a_stop_says_how_many_turns_came_after_it(self):
        """The turns after a stop are the ones it cost — the accounting's own
        reading of a gate (`lib/spend.runs`, *what the turns after one cost*),
        so the page and `tools/tokens.py` count one way."""
        usage = {"usage": {"input_tokens": 100, "output_tokens": 10}}
        figure = self.spent(usage, {"call": {"command": "git commit -m taller"}},
                            usage, usage)
        self.assertEqual((figure["turns"], figure["stops"], figure["after_stops"]),
                         (3, 1, 2))

    def test_a_run_no_gate_stopped_cost_no_turns_to_one(self):
        usage = {"usage": {"input_tokens": 100, "output_tokens": 10}}
        figure = self.spent(usage, usage)
        self.assertEqual((figure["stops"], figure["after_stops"]), (0, 0))


class PageTest(unittest.TestCase):
    """The page's source, as `test_always.PageTest` reads it."""

    def setUp(self):
        from lib.canvas import PAGE
        self.page = PAGE.read_text(encoding="utf-8")
        self.script = self.page.split("function spendLine(", 1)[1].split("\n}\n", 1)[0]

    def test_the_line_is_turns_and_stops_only_when_they_cost_turns(self):
        self.assertIn("event.after_stops", self.script)
        self.assertIn("' extra turn'", self.script)
        self.assertIn("' stop'", self.script)

    def test_the_stops_link_to_what_runs_without_asking(self):
        self.assertIn("'#unwatched'", self.script)

    def test_the_tokens_are_one_click_away_in_the_accountings_words(self):
        """`tools/tokens.py` calls them *cached*, *fresh*, *out* and
        *weighted*, and prints them through `human`, which `round` mirrors."""
        self.assertIn("<details", self.page.split('id="spend"', 1)[1].split("</div>", 1)[0])
        for word in ("' cached'", "' fresh'", "' out'", "' weighted'"):
            self.assertIn(word, self.script)


if __name__ == "__main__":
    unittest.main()
