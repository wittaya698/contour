"""An answer shows what comes next without a reload (issue 135).

Reproduced with the stand-in console and the page driven headless: every
answer the page gives itself — Yes, Let me move it and Save, Wrong thing with
a reason or cancelled, skip, and the list's adopt, correct and reject — moved
the card on. What did not was a span written by anyone else. The page read
`/marks` on load and after its own answers and never again, so the spans a
run's `contour measure` placed, or an answer given in another tab, reached the
card only on a reload: the file held 4 questions and the card said 3 for as
long as it was watched. The page now reads the marks on a clock too.

The page's functions run here under node, with the server stood in: there is
no browser in this suite.
"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.canvas import PAGE             # noqa: E402
from test_found import function         # noqa: E402

# The server, stood in: `replies` is what each request to a path answers, in
# turn, with null for a request that fails, and `{later: name, said}` for one
# that answers only when the test calls `later[name]()`.
SERVER = """
let marks = [], drawn = 0, moving = null, reads = 0;
const hint = { textContent: '' };
function draw() { drawn++; }
const replies = {}, later = {};
function ask(path, body) {
  const said = (replies[path] || []).shift();
  if (said === null) return Promise.reject(new Error('gone'));
  const reply = s => ({ ok: true, json: () => Promise.resolve(s) });
  if (said && said.later) return new Promise(go => { later[said.later] = () => go(reply(said.said)); });
  return Promise.resolve(reply(said));
}
"""


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class NextTest(unittest.TestCase):

    def run_page(self, names, body):
        page = PAGE.read_text(encoding="utf-8")
        js = (SERVER + "".join("async " + function(page, n) for n in names)
              + f"(async () => {{ {body} }})().then(r => console.log(JSON.stringify(r)));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_a_span_written_elsewhere_reaches_the_page(self):
        """A run's agent placed one while the page was open."""
        placed = [{"id": "m1", "author": "agent", "text": "the seat"}]
        said = self.run_page(["reread"], f"""
            replies['/marks'] = [{json.dumps(placed)}];
            await reread();
            return {{ marks, drawn }};""")
        self.assertEqual(said, {"marks": placed, "drawn": 1})

    def test_a_read_that_finds_nothing_new_redraws_nothing(self):
        """Read on a clock, a redraw every time would rebuild the list under
        the mouse every few seconds, a checkbox about to be ticked with it."""
        placed = [{"id": "m1", "author": "agent", "text": "the seat"}]
        said = self.run_page(["reread"], f"""
            replies['/marks'] = [{json.dumps(placed)}, {json.dumps(placed)}];
            await reread();
            await reread();
            return drawn;""")
        self.assertEqual(said, 1)

    def test_a_read_that_comes_back_after_a_newer_one_is_older_news(self):
        """The clock's read went out, the person answered, the answer's read
        came back with the span adopted, and then the clock's came back with
        it still a question: the card must not ask it again."""
        asked = [{"id": "m1", "author": "agent", "text": "the seat"}]
        adopted = [{"id": "m1", "author": "user", "answer": "adopted", "text": "the seat"}]
        said = self.run_page(["reread"], f"""
            replies['/marks'] = [{{ later: 'clock', said: {json.dumps(asked)} }},
                                 {json.dumps(adopted)}];
            const clock = reread();
            await reread();
            later.clock();
            await clock;
            return marks;""")
        self.assertEqual(said, adopted)

    def test_an_answer_that_does_not_arrive_is_said_and_can_be_given_again(self):
        """The console gone, or the request refused before it was read: the
        answer is not recorded, the page says so, and a span being moved
        keeps the ends the person dragged it to, with Save still there."""
        span = {"id": "m1", "author": "agent", "pixel": [0, 0], "to": [9, 9]}
        said = self.run_page(["answered", "reread"], f"""
            marks = [{json.dumps(span)}];
            moving = {{ mark: marks[0], ends: [[0, 0], [12, 9]] }};
            replies['/correct'] = [null];
            replies['/marks'] = [marks];
            await answered('/correct', {{ id: 'm1', pixel: [0, 0], to: [12, 9] }});
            return {{ hint: hint.textContent, ends: moving && moving.ends }};""")
        self.assertIn("not recorded", said["hint"])
        self.assertEqual(said["ends"], [[0, 0], [12, 9]])

    def test_marks_that_cannot_be_read_back_are_said_and_the_page_keeps_what_it_shows(self):
        """The answer was recorded and the read after it failed: the page
        cannot show what comes next, so it says why, and the clock's next
        read catches it up."""
        span = {"id": "m1", "author": "agent", "pixel": [0, 0], "to": [9, 9]}
        said = self.run_page(["answered", "reread"], f"""
            marks = [{json.dumps(span)}];
            replies['/adopt'] = [{{ id: 'm1', answer: 'adopted' }}];
            replies['/marks'] = [null];
            await answered('/adopt', {{ id: 'm1' }});
            return {{ hint: hint.textContent, marks }};""")
        self.assertIn("could not be read", said["hint"])
        self.assertEqual(said["marks"], [span])

    def test_a_saved_move_stops_asking_for_a_save(self):
        """Reproduced: after Save the card moved on and the line under the
        picture still said to drag an end and Save."""
        span = {"id": "m1", "author": "agent", "pixel": [0, 0], "to": [9, 9]}
        corrected = {**span, "author": "user", "answer": "corrected", "to": [12, 9]}
        said = self.run_page(["answered", "reread"], f"""
            marks = [{json.dumps(span)}];
            moving = {{ mark: marks[0], ends: [[0, 0], [12, 9]] }};
            hint.textContent = 'Drag the end that is wrong, here or on the card, then Save.';
            replies['/correct'] = [{json.dumps(corrected)}];
            replies['/marks'] = [[{json.dumps(corrected)}]];
            await answered('/correct', {{ id: 'm1', pixel: [0, 0], to: [12, 9] }});
            return {{ hint: hint.textContent, moving }};""")
        self.assertIsNone(said["moving"])
        self.assertNotIn("Save", said["hint"])


class PageTest(unittest.TestCase):
    """The wiring, read off the page's source as `test_questions` reads it."""

    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")

    def test_the_marks_are_read_on_load_on_a_clock_and_after_an_answer(self):
        """One read, so the three cannot disagree about what is news."""
        self.assertTrue("\nreread();\n" in self.page, "read on load")
        self.assertTrue("setInterval(reread, " in self.page, "read on a clock")
        self.assertIn("await reread()", function(self.page, "answered"))
        self.assertEqual(self.page.count("ask('/marks').then"), 1, "reread's, and no other")


if __name__ == "__main__":
    unittest.main()
