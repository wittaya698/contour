"""A reason is typed without stopping the page (issue 143).

*Wrong thing…* asked for its reason with the browser's `prompt()`, which
stops the page's script while it is open, the heartbeat with it: ten seconds
of typing and the console took the silent tab for a closed one and ended.
The reason is now typed in the page, on the card, and nothing in the page
blocks. The page's functions run here under node, with the server stood in:
there is no browser in this suite.
"""
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.canvas import PAGE             # noqa: E402
from test_found import function         # noqa: E402

MARKS = [{"id": "m1", "author": "agent", "ref": "a.png", "pixel": [0, 0], "to": [9, 9]},
         {"id": "m2", "author": "agent", "ref": "a.png", "pixel": [5, 5], "to": [20, 9]}]

# The page around the functions under test, stood in: `sent` is every request
# made, and each answers `replies[path]` in turn.
SERVER = f"""
let marks = {json.dumps(MARKS)}, moving = null, rejecting = null, reads = 0, drawn = 0;
const skipped = new Set(), sent = [], replies = {{}};
const hint = {{ textContent: '' }};
function draw() {{ drawn++; }}
function spanState(m) {{ return m.answer ? m.answer : 'unanswered'; }}
function ask(path, body) {{
  sent.push([path, body]);
  const said = (replies[path] || []).shift();
  return said === null ? Promise.reject(new Error('gone'))
                       : Promise.resolve({{ ok: true, json: () => Promise.resolve(said) }});
}}
"""


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class ReasonTest(unittest.TestCase):

    def run_page(self, names, body):
        page = PAGE.read_text(encoding="utf-8")
        js = (SERVER + "".join(("async " if f"async function {n}(" in page else "")
                               + function(page, n) for n in names)
              + f"(async () => {{ {body} }})().then(r => console.log(JSON.stringify(r)));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_wrong_thing_asks_for_the_reason_on_the_card(self):
        """From the card or from the list: the span is the card's question,
        with its reason field open, and nothing is sent yet."""
        said = self.run_page(["rejectSpan", "foundation", "named", "asking"], """
            rejectSpan(marks[1]);
            return { asks: asking(marks, skipped, rejecting).mark.id, sent };""")
        self.assertEqual(said, {"asks": "m2", "sent": []})

    def test_a_reason_is_sent_as_before_and_a_blank_one_is_not(self):
        said = self.run_page(["giveWhy", "answered", "reread"], """
            rejecting = marks[1];
            replies['/reject'] = [{ id: 'm2', answer: 'rejected' }];
            replies['/marks'] = [marks];
            await giveWhy('   ');
            await giveWhy('  the cap, not the rim ');
            return sent.filter(([path]) => path === '/reject');""")
        self.assertEqual(said, [["/reject", {"id": "m2", "why": "the cap, not the rim"}]])

    def test_a_reason_recorded_closes_the_field_and_one_lost_keeps_it(self):
        """Lost — the console gone, or the request refused before it was
        read — the field stays open with the reason in it, to send again."""
        said = self.run_page(["giveWhy", "answered", "reread"], """
            const after = [];
            rejecting = marks[1];
            replies['/reject'] = [null, { id: 'm2', answer: 'rejected' }];
            replies['/marks'] = [marks];
            await giveWhy('the cap');
            after.push(rejecting && rejecting.id);
            await giveWhy('the cap');
            after.push(rejecting && rejecting.id);
            return after;""")
        self.assertEqual(said, ["m2", None])


class PageTest(unittest.TestCase):

    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")

    def card(self):
        return self.page.split('<section id="questions"', 1)[1].split("</section>", 1)[0]

    def test_the_reason_is_a_field_on_the_card(self):
        """A form, so Enter sends it; Reject waits for something typed."""
        form = self.card().split('<form class="why" hidden>', 1)[1].split("</form>", 1)[0]
        self.assertIn('<input class="reason"', form)
        self.assertIn('<button type="submit" class="reject" disabled>Reject</button>', form)
        self.assertIn('<button type="button" class="unwhy">Cancel</button>', form)

    def test_the_card_asks_the_span_being_rejected_with_its_field_open(self):
        for name in ("draw", "questions"):
            # A run's park, if any, follows it (issue 158).
            self.assertRegex(function(self.page, name),
                             r"asking\(marks, skipped, \(moving && moving\.mark\) \|\| rejecting[,)]",
                             name)
        asking = function(self.page, "questions")
        self.assertIn("card.querySelector('.why').hidden = !rejecting;", asking)
        self.assertIn("card.querySelector('.answers').hidden = !!(moving || rejecting);", asking)

    def test_sent_with_enter_or_reject_and_put_away_with_cancel_or_escape(self):
        wired = function(self.page, "askedAnswers")
        self.assertIn("why.addEventListener('submit'", wired)
        self.assertIn("giveWhy(reason.value)", wired)
        self.assertIn("e.key === 'Escape'", wired)
        self.assertIn("reject.disabled = !reason.value.trim()", wired)
        self.assertIn("on('.unwhy', unreject)", wired)
        self.assertIn("rejecting = null;", function(self.page, "unreject"))

    def test_nothing_in_the_page_stops_it(self):
        """A dialog stops the script, and the heartbeat with it."""
        self.assertEqual(re.findall(r"\b(?:prompt|confirm|alert)\(", self.page), [])


if __name__ == "__main__":
    unittest.main()
