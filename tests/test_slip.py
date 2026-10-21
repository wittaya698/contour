"""A slip can be undone (issue 136; ADR 0022, decision 5).

An answer to an agent span is final, and a wrong button or a bad drag then
stood. One undo now covers a slip: the last answer only, while the span is
still exactly as that answer left it and no run has started since. Undone, the
marks are as they were before the answer, with no trace of it. These talk to
the running canvas over HTTP, as the page does.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import span
from lib.canvas import PAGE, Canvas
from client import post
from test_found import function
from test_console import ConsoleCase
from test_span_answers import QUESTION


class SlipCase(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.marks = self.tmp / "marks.json"
        self.runs = self.tmp / "last-run.json"
        self.canvas = Canvas(sheet=self.tmp / "sheet.png", marks=self.marks, runs=self.runs)
        self.addCleanup(self.canvas.stop)
        self.canvas.start()

    def drawn(self, text="the body, side to side"):
        """An agent span with its reading, as `contour measure` draws one."""
        said = span.pinned(self.marks, "front.jpg", QUESTION,
                           ([99.5, 549.5], [299.5, 549.5]), 2.0, text)
        return said["lines"][0].split()[2]


class UndoneTest(SlipCase):

    def test_an_adoption_undone_leaves_the_marks_as_they_were(self):
        mark_id = self.drawn()
        before = self.marks.read_bytes()
        post(self.canvas, "/adopt", {"id": mark_id})
        status, said = post(self.canvas, "/unanswer", {"id": mark_id})
        self.assertEqual(status, 200)
        self.assertNotIn("refused", said)
        self.assertEqual(self.marks.read_bytes(), before)

    def test_a_correction_undone_leaves_the_marks_as_they_were(self):
        """Claude's ends back, its reading open again, and the reading the
        correction made gone, with its id free again."""
        mark_id = self.drawn()
        before = self.marks.read_bytes()
        post(self.canvas, "/correct", {"id": mark_id, "pixel": [99.5, 549.5],
                                       "to": [349.5, 549.5]})
        self.assertNotEqual(self.marks.read_bytes(), before)
        status, said = post(self.canvas, "/unanswer", {"id": mark_id})
        self.assertNotIn("refused", said)
        self.assertEqual(self.marks.read_bytes(), before)

    def test_a_rejection_undone_leaves_the_marks_as_they_were(self):
        """Open again, its why and *not to be used* gone, its reading too."""
        mark_id = self.drawn()
        before = self.marks.read_bytes()
        post(self.canvas, "/reject", {"id": mark_id, "why": "the lid"})
        status, said = post(self.canvas, "/unanswer", {"id": mark_id})
        self.assertNotIn("refused", said)
        self.assertEqual(self.marks.read_bytes(), before)


class RefusedTest(SlipCase):

    def test_only_the_last_answer_can_be_undone(self):
        first, second = self.drawn("the body"), self.drawn("the lid")
        post(self.canvas, "/adopt", {"id": first})
        post(self.canvas, "/adopt", {"id": second})
        before = self.marks.read_bytes()
        status, said = post(self.canvas, "/unanswer", {"id": first})
        self.assertIn("only the last answer, once", said["refused"])
        self.assertEqual(self.marks.read_bytes(), before)

    def test_an_answer_undone_is_not_undone_twice(self):
        mark_id = self.drawn()
        post(self.canvas, "/adopt", {"id": mark_id})
        post(self.canvas, "/unanswer", {"id": mark_id})
        status, said = post(self.canvas, "/unanswer", {"id": mark_id})
        self.assertIn("only the last answer, once", said["refused"])

    def test_a_span_changed_since_the_answer_keeps_it(self):
        """Closed from the list after it was adopted: the answer has been
        built on, and taking it back would quietly undo the close too."""
        mark_id = self.drawn()
        post(self.canvas, "/adopt", {"id": mark_id})
        post(self.canvas, "/close", {"id": mark_id})
        before = self.marks.read_bytes()
        status, said = post(self.canvas, "/unanswer", {"id": mark_id})
        self.assertIn("changed since you answered", said["refused"])
        self.assertEqual(self.marks.read_bytes(), before)


    def test_a_run_started_since_the_answer_keeps_it(self):
        """A tab left open behind a run cannot reopen a question the run
        already used. Whichever console started it: the space's run record
        says which run is the latest."""
        for had in ({"run": "b0540403df56f473", "state": "finished"}, None):
            with self.subTest(before=had):
                if had:
                    self.runs.write_text(json.dumps(had))
                mark_id = self.drawn()
                post(self.canvas, "/adopt", {"id": mark_id})
                self.runs.write_text(json.dumps({"run": "9f2c11d07a3e5b68", "state": "running"}))
                before = self.marks.read_bytes()
                status, said = post(self.canvas, "/unanswer", {"id": mark_id})
                self.assertIn("a run has started since", said["refused"])
                self.assertEqual(self.marks.read_bytes(), before)
                self.runs.unlink()

    def test_a_run_going_when_it_was_answered_does_not_keep_it(self):
        """Answered while a run worked: the same run, so nothing started since."""
        self.runs.write_text(json.dumps({"run": "9f2c11d07a3e5b68", "state": "running"}))
        mark_id = self.drawn()
        before = self.marks.read_bytes()
        post(self.canvas, "/adopt", {"id": mark_id})
        self.runs.write_text(json.dumps({"run": "9f2c11d07a3e5b68", "state": "waiting"}))
        status, said = post(self.canvas, "/unanswer", {"id": mark_id})
        self.assertNotIn("refused", said)
        self.assertEqual(self.marks.read_bytes(), before)


class UnderTheConsoleTest(ConsoleCase):
    """The console's own runs are the runs that close the window."""

    def test_a_run_started_on_the_console_keeps_the_answer(self):
        space = self.space()
        found = space / "marks.json"
        drawn = span.pinned(found, "front.jpg", QUESTION,
                            ([99.5, 549.5], [299.5, 549.5]), 2.0, "the body")
        mark_id = drawn["lines"][0].split()[2]
        _, url = self.driven({"say": "done"}, space=space)
        self.ask(url, "/adopt", {"id": mark_id})
        self.ask(url, "/run", {"prompt": "measure the lid"})
        _, said = self.ask(url, "/unanswer", {"id": mark_id})
        self.assertIn("a run has started since", said["refused"])
        self.assertEqual(span.marked(found, mark_id)["answer"], "adopted")


# The server, stood in, as `test_next` stands it in: `replies` is what each
# request to a path answers, in turn, with null for one that fails.
SERVER = """
let marks = [], drawn = 0, moving = null, reads = 0, slip = null;
const hint = { textContent: '' };
function draw() { drawn++; }
const replies = {};
function ask(path, body) {
  const said = (replies[path] || []).shift();
  return said === null ? Promise.reject(new Error('gone'))
                       : Promise.resolve({ ok: true, json: () => Promise.resolve(said) });
}
"""


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class OfferTest(unittest.TestCase):
    """The page's half: it holds the window, and the server checks it."""

    def run_page(self, names, body):
        page = PAGE.read_text(encoding="utf-8")
        js = (SERVER + "".join(("async " if f"async function {n}(" in page else "")
                               + function(page, n) for n in names)
              + f"(async () => {{ {body} }})().then(r => console.log(JSON.stringify(r)));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_the_last_answer_is_the_one_offered(self):
        span = {"id": "m3", "author": "agent", "pixel": [0, 0], "to": [9, 9]}
        said = self.run_page(["answered", "reread"], f"""
            const got = [];
            for (const [path, did] of [['/adopt', 'adopted'], ['/correct', 'corrected'],
                                       ['/reject', 'rejected']]) {{
              replies[path] = [{{ id: 'm3', answer: did }}];
              replies['/marks'] = [[{json.dumps(span)}]];
              await answered(path, {{ id: 'm3' }});
              got.push(slip);
            }}
            return got;""")
        self.assertEqual(said, [{"id": "m3", "did": "Adopted"}, {"id": "m3", "did": "Corrected"},
                                {"id": "m3", "did": "Rejected"}])

    def test_an_answer_refused_or_lost_leaves_the_offer_as_it_was(self):
        """The server's last answer did not change, so neither does the page's."""
        said = self.run_page(["answered", "reread"], """
            slip = { id: 'm1', did: 'Adopted' };
            replies['/adopt'] = [{ refused: 'm3 is not an agent span waiting on an answer' }, null];
            await answered('/adopt', { id: 'm3' });
            await answered('/adopt', { id: 'm3' });
            return slip;""")
        self.assertEqual(said, {"id": "m1", "did": "Adopted"})

    def test_the_offer_names_the_span_by_its_badge(self):
        """By its place in the list, as the card names a question (issue 131),
        and nothing once the span is not on file."""
        said = self.run_page(["named", "slipped"], """
            const marks = [{ id: 'm1' }, { id: 'm2' }, { id: 'm7' }];
            return [slipped({ id: 'm7', did: 'Corrected' }, marks), slipped({ id: 'm9', did: 'Adopted' }, marks),
                    slipped(null, marks)];""")
        self.assertEqual(said, ["Corrected span 3", None, None])

    def test_an_undo_taken_back_asks_the_span_again(self):
        """The span is Claude's question again, read back from the file."""
        again = [{"id": "m3", "author": "agent", "pixel": [0, 0], "to": [9, 9]}]
        said = self.run_page(["undo", "reread"], f"""
            slip = {{ id: 'm3', did: 'Adopted' }};
            replies['/unanswer'] = [{json.dumps(again[0])}];
            replies['/marks'] = [{json.dumps(again)}];
            await undo();
            return {{ slip, marks }};""")
        self.assertEqual(said, {"slip": None, "marks": again})

    def test_an_undo_refused_says_why_and_is_not_offered_again(self):
        said = self.run_page(["undo", "reread"], """
            slip = { id: 'm3', did: 'Adopted' };
            replies['/unanswer'] = [{ refused: "m3's answer stands: a run has started since, and may have used it" }];
            replies['/marks'] = [[]];
            await undo();
            return { slip, hint: hint.textContent, drawn };""")
        self.assertEqual(said["slip"], None)
        self.assertIn("a run has started since", said["hint"])
        self.assertGreater(said["drawn"], 0, "redrawn, so the offer goes")

    def test_an_undo_that_does_not_arrive_is_said_and_still_offered(self):
        said = self.run_page(["undo", "reread"], """
            slip = { id: 'm3', did: 'Adopted' };
            replies['/unanswer'] = [null];
            await undo();
            return { slip, hint: hint.textContent };""")
        self.assertEqual(said["slip"], {"id": "m3", "did": "Adopted"})
        self.assertIn("did not reach the console", said["hint"])


class PageTest(unittest.TestCase):
    """The wiring, read off the page's source as `test_questions` reads it."""

    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")
        self.card = self.page.split('<section id="questions"', 1)[1].split("</section>", 1)[0]

    def test_the_card_offers_the_last_answer_back(self):
        self.assertIn('<p class="slip" hidden>', self.card)
        self.assertIn('class="undo', self.card)
        asking = function(self.page, "questions")
        self.assertIn("slipped(slip, marks)", asking)
        self.assertLess(asking.index("slipped(slip, marks)"), asking.index("if (!mark) return;"),
                        "offered before the card asks, whether or not it has more to ask")

    def test_with_no_card_showing_the_list_offers_it_beside_the_span(self):
        drawing = function(self.page, "draw")
        self.assertIn("!now && slip && mark.id === slip.id", drawing)
        self.assertIn("undo()", drawing.split("!now && slip && mark.id === slip.id", 1)[1])

    def test_skipping_takes_the_offer_away(self):
        skip = function(self.page, "askedAnswers").split("'.skip'", 1)[1].split("\n", 1)[0]
        self.assertIn("slip = null", skip)

    def test_a_run_starting_takes_the_offer_away(self):
        """Whoever started it: a run's first line is its prompt, which the
        transcript says on every tab of this console."""
        polled = self.page.split("ask('/events?since=' + cursor)", 1)[1].split("}, 600);", 1)[0]
        self.assertIn("if (event.kind === 'prompt' && slip) { slip = null; draw(); }", polled)

    def test_both_undo_buttons_are_the_one_undo(self):
        self.assertIn("on('.undo', () => undo())", function(self.page, "askedAnswers"))


if __name__ == "__main__":
    unittest.main()
