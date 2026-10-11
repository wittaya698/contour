"""The vetoes panel says *You said no to* (ADR 0025, decision 7; issue 74).

What `/vetoes` hands the page is held in `test_console.VetoTest`: each veto
with the act it refused and the part it was pinned to, and no count. These
read the page's source, as `test_always.PageTest` does, for how it says them.
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
        self.section = re.search(r'<section id="vetoes"[^>]*>(.*?)</section>',
                                 self.page, re.S).group(1)
        self.script = self.page.split("function vetoed(", 1)[1].split("\n}\n", 1)[0]

    def test_the_heading_is_you_said_no_to(self):
        self.assertIn("<h1>You said no to</h1>", self.section)

    def test_each_line_is_the_act_and_the_reason(self):
        self.assertIn("veto.act", self.script)
        self.assertIn("veto.reason", self.script)
        self.assertNotIn("veto.category", self.script)

    def test_pinning_is_pin_this_to_a_part_and_says_the_part(self):
        self.assertIn("'Pin this to a part'", self.script)
        self.assertIn("'pinned to ' + veto.pinned", self.script)
        self.assertIn("'/promote'", self.script, "the same mark promotion made")
        self.assertNotIn("promote to a mark", self.page)

    def test_pinning_is_offered_only_where_the_veto_says_it_can_be(self):
        """A build refused is not about a part, nor a veto with no reason
        (issue 112): the console says which with `pinnable`, and the page asks
        nothing of its own."""
        self.assertIn("if (!veto.pinnable) return li;", self.script)
        self.assertLess(self.script.index("if (!veto.pinnable) return li;"),
                        self.script.index("'Pin this to a part'"))

    def test_no_count_of_uncommitted_vetoes_is_shown(self):
        self.assertNotIn("uncommitted", self.page.split("<script>", 1)[1])
        self.assertNotIn('id="exposure"', self.page)


if __name__ == "__main__":
    unittest.main()
