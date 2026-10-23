"""A run waits on its by-eye spans (ADR 0035, decisions 1, 2, 4, 5 and 6;
issue 157).

Under an attended console, `contour worksheet` called while by-eye agent
spans are unanswered parks the run, as a form does, until each is answered or
skipped. A snapped span never parks it, a span is asked about once per run,
and a run nobody is watching never parks.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import one_run    # noqa: E402,F401  one suite run per machine (issue 94)
from test_run_record import RecordCase    # noqa: E402

from console import approvals, vetoes    # noqa: E402
from console.run import Run    # noqa: E402
from lib.canvas import PAGE    # noqa: E402
from test_console import ConsoleCase    # noqa: E402
from lib import marks, worksheet    # noqa: E402
from test_found import function    # noqa: E402

WAIT_S = 15
WORKSHEET = {"command": "contour worksheet"}


class ParkCase(RecordCase):

    def drawn(self, text, placed="by eye"):
        """An agent span on file, and its id."""
        mark = {"ref": "front.png", "pixel": [10, 10], "to": [100, 10], "text": text,
                "placed": placed}
        if placed == "snapped":
            mark["question"] = {"row": 10}
        span, _ = marks.spanned(self.space / marks.NAME, mark, "90 px", [55, 10])
        return span["id"]

    def worksheets(self, n=1, requester=None):
        """A run whose agent calls the worksheet `n` times, and what each
        call's gate gave it."""
        given = []

        def drive(prompt, options, gate, say):
            for _ in range(n):
                given.append(gate("Bash", WORKSHEET))
        run = Run(self.space, drive=drive)
        self.addCleanup(lambda: run.live and run.end())
        run.start("measure it", ceiling=10**6, requester=requester)
        return run, given

    def parked(self, run):
        deadline = time.monotonic() + WAIT_S
        while run.pending is None:
            self.assertLess(time.monotonic(), deadline, "the run never parked")
            time.sleep(0.01)
        return run.pending

    def through(self, given, n=1):
        deadline = time.monotonic() + WAIT_S
        while len(given) < n:
            self.assertLess(time.monotonic(), deadline, "the worksheet never ran")
            time.sleep(0.01)
        return given[n - 1]


class ParksTest(ParkCase):

    def test_a_by_eye_span_unanswered_parks_the_worksheet_until_answered(self):
        width = self.drawn("width")
        run, given = self.worksheets()
        self.parked(run)
        time.sleep(0.3)
        self.assertEqual(given, [], "the worksheet ran before the span was answered")
        marks.adopt(self.space / marks.NAME, width)
        self.assertEqual(self.through(given), (True, None))

    def test_the_worksheet_parks_however_it_is_spelled(self):
        # The first three as a live run wrote it, or near it: `;` and `|`
        # against the word before them (a live console, 2026-10-24).
        for command in ('contour worksheet; echo "---"; cat spec.yaml',
                        "contour worksheet&& cat spec.yaml", "contour worksheet|head",
                        "cd /s && ./contour worksheet", "contour run contour worksheet"):
            with self.subTest(command=command):
                given = []

                def drive(prompt, options, gate, say, command=command):
                    given.append(gate("Bash", {"command": command}))
                self.drawn("width")
                run = Run(self.space, drive=drive)
                self.addCleanup(lambda r=run: r.live and r.end())
                run.start("measure it", ceiling=10**6)
                self.parked(run)
                run.end()

    def test_the_transcript_keeps_what_was_answered_once_the_park_ends(self):
        """As a form keeps its answers (issue 158): by what each measures, and
        a skip as a skip. The page closes the card on it."""
        held = self.space / marks.NAME
        width, grille, knob = self.drawn("width"), self.drawn("grille"), self.drawn("knob")
        run, given = self.worksheets()
        at = self.parked(run)["id"]
        marks.adopt(held, width)
        marks.reject(held, grille, "that is the speaker")
        run.skip(knob)
        self.through(given)
        [said] = [e for e in run.events if e["kind"] == "spans-answered"]
        self.assertEqual(said["id"], at)
        self.assertEqual(said["text"], "You answered Claude's spans: width adopted, "
                                       "grille rejected, knob skipped for now")

    def test_a_snapped_span_unanswered_never_parks_it(self):
        """Its number may be proposed as the agent's reading: making the run
        wait for it is the second gate ADR 0022 rejected (ADR 0035, decision 2)."""
        self.drawn("width", placed="snapped")
        run, given = self.worksheets()
        self.assertEqual(self.through(given), (True, None))
        self.assertEqual(run.gates, 0)

    def test_skipped_it_ends_the_park_and_stays_unanswered(self):
        width = self.drawn("width")
        run, given = self.worksheets()
        self.parked(run)
        self.assertEqual(run.skip(width), {"skipped": width})
        self.assertEqual(self.through(given), (True, None))
        self.assertEqual([m["id"] for m in marks.by_eye(marks.load(self.space / marks.NAME))],
                         [width], "skipping answers nothing")

    def test_the_park_waits_for_every_span_it_asked_about(self):
        width, grille = self.drawn("width"), self.drawn("grille")
        run, given = self.worksheets()
        self.parked(run)
        marks.adopt(self.space / marks.NAME, width)
        time.sleep(0.3)
        self.assertEqual(given, [], "one of two answered is not the park's end")
        run.skip(grille)
        self.assertEqual(self.through(given), (True, None))

    def test_a_later_worksheet_parks_only_on_spans_drawn_since(self):
        """A span is asked about once per run (ADR 0035, decision 5): skipped, it does
        not stop the next worksheet; a span drawn since does."""
        width = self.drawn("width")
        given = []

        def drive(prompt, options, gate, say):
            given.append(gate("Bash", WORKSHEET))
            given.append(gate("Bash", WORKSHEET))
            self.drawn("grille")
            given.append(gate("Bash", WORKSHEET))
        run = Run(self.space, drive=drive)
        self.addCleanup(lambda: run.live and run.end())
        run.start("measure it", ceiling=10**6)
        self.parked(run)
        run.skip(width)
        self.through(given, 2)
        self.assertEqual(self.parked(run)["spans"], ["m3"])
        self.assertEqual(len(given), 2)

    def test_a_new_run_asks_about_a_skipped_span_again(self):
        width = self.drawn("width")
        run, given = self.worksheets()
        self.parked(run)
        run.skip(width)
        self.through(given)
        run.end()
        again, given = self.worksheets()
        self.assertEqual(self.parked(again)["spans"], [width])

    def test_a_skip_for_a_span_the_park_did_not_ask_about_is_refused(self):
        self.drawn("width")
        run, _ = self.worksheets()
        self.parked(run)
        self.assertIn("refused", run.skip("m9"))
        self.assertIsNotNone(run.pending)

    def test_an_unattended_run_never_parks(self):
        """Nobody is there to answer, and the span already waits in
        `marks.json` (ADR 0035, decision 6)."""
        self.drawn("width")
        run, given = self.worksheets(requester="the nightly agent")
        self.assertEqual(self.through(given), (True, None))
        self.assertEqual(run.gates, 0)

    def test_ending_the_run_ends_the_park_as_it_ends_any_gate(self):
        """From the page or from outside: nothing is set aside, since a span
        already waits in `marks.json` without being set aside."""
        for aside in (False, True):
            with self.subTest(aside=aside):
                self.drawn("width")
                run, given = self.worksheets()
                self.parked(run)
                run.end(aside=aside)
                deadline = time.monotonic() + WAIT_S
                while run.live:
                    self.assertLess(time.monotonic(), deadline, "the park outlived its run")
                    time.sleep(0.01)
                self.assertEqual(given, [])
                self.assertIsNone(run.pending)
                self.assertEqual(approvals.load(self.space), [])

    def test_a_verdict_on_the_park_answers_nothing(self):
        """It is answered span by span, never allowed or denied whole."""
        self.drawn("width")
        run, _ = self.worksheets()
        at = self.parked(run)["id"]
        self.assertIsNone(run.answer(at, False, "no"))
        self.assertIsNotNone(run.pending)
        self.assertEqual(vetoes.load(self.space), [])

    def test_while_parked_the_line_says_it_waits_on_its_spans(self):
        """In the words the canvas's card says them (issue 157)."""
        self.drawn("width")
        run, _ = self.worksheets()
        self.parked(run)
        self.assertEqual(run.status(), {
            "state": "waiting",
            "said": "Waiting for you: Claude has questions about your pictures"})
        self.assertEqual(self.until("waiting for you")["act"],
                         "Claude has questions about your pictures")


class AnswersTest(ParkCase):
    """The worksheet's output names each answer (ADR 0035, decision 4), and which spans
    are still unanswered, watched or not (ADR 0035, decision 6)."""

    def said(self, skipped=()):
        return worksheet.answers(marks.load(self.space / marks.NAME), skipped)

    def test_each_answer_is_named_with_what_it_means_for_a_proposal(self):
        held = self.space / marks.NAME
        width, grille, knob, strip = (self.drawn(t) for t in
                                      ("width", "grille", "knob", "button strip"))
        marks.adopt(held, width)
        marks.correct(held, grille, [10, 20], [120, 20], "110 px")
        marks.reject(held, knob, "that is the case edge")
        self.assertEqual(self.said(skipped=[strip]), [
            f"  {width} width: adopted by the user; its number may be proposed, "
            f"naming {width}",
            f"  {grille} grille: moved by the user, now 110 px; its number may be "
            f"proposed, naming {grille}",
            f"  {knob} knob: rejected by the user (that is the case edge); its "
            f"number may not be used",
            f"  {strip} button strip: skipped for now, still unanswered; its number "
            f"may not be proposed"])

    def test_a_by_eye_span_unanswered_is_named_as_one(self):
        width = self.drawn("width")
        self.assertEqual(self.said(), [
            f"  {width} width: by eye and unanswered; its number may not be "
            f"proposed until the user answers it"])

    def test_a_snapped_span_unanswered_is_not_listed(self):
        """Its number is already the agent's own reading to propose."""
        self.drawn("width", placed="snapped")
        self.assertEqual(self.said(), [])

    def test_the_runs_skips_are_read_by_the_run_that_holds_the_space(self):
        width = self.drawn("width")
        run, given = self.worksheets()
        self.parked(run)
        here = run.record["run"]
        run.skip(width)
        self.through(given)
        self.assertEqual(worksheet.skipped(self.space / ".contour", here), [width])
        self.assertEqual(worksheet.skipped(self.space / ".contour", "another run"), [])

    def test_the_worksheet_command_says_them_for_the_run_it_belongs_to(self):
        """Read off `marks.json` before Blender starts, so the answers are said
        whatever the drawing does; here it cannot draw at all."""
        width, grille = self.drawn("width"), self.drawn("grille")
        worksheet.skip(self.space / ".contour", "r1", [grille])
        said = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent.parent / "contour"),
             "worksheet"], cwd=str(self.space), capture_output=True, text=True,
            timeout=60, env=dict(os.environ, BLENDER="/nonexistent", CONTOUR_RUN="r1"))
        self.assertIn(f"  {width} width: by eye and unanswered", said.stdout)
        self.assertIn(f"  {grille} grille: skipped for now", said.stdout)


class PageTest(ConsoleCase):
    """Through the real console: the page's *skip for now* is the run's."""

    def test_the_pages_skip_ends_the_park_and_the_transcript_says_it_waited(self):
        space = self.space()
        mark = {"ref": "front.png", "pixel": [10, 10], "to": [100, 10], "text": "width",
                "placed": "by eye"}
        width = marks.spanned(space / marks.NAME, mark, "90 px", [55, 10])[0]["id"]
        _, url = self.driven({"call": {"tool": "Bash", "command": "contour worksheet"}},
                             {"say": "drawn"}, space=space)
        self.ask(url, "/run", {"prompt": "measure it"})
        said = self.transcript(url, lambda ev: any(e["kind"] == "spans" for e in ev))
        [park] = [e for e in said if e["kind"] == "spans"]
        self.assertEqual(park["spans"], [width])
        self.assertIn("Claude has questions about your pictures", park["text"])
        self.assertEqual(self.ask(url, "/skip", {"id": width}), (200, {"skipped": width}))
        self.transcript(url, lambda ev: any(e.get("text") == "drawn" for e in ev))

    def test_the_park_brings_the_panels_own_card_into_the_transcript(self):
        """The same card, not a second one: moved, so an answer in either
        place is the answer in both (issue 158)."""
        page = PAGE.read_text(encoding="utf-8")
        turn = page.split("function turn(", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("event.kind === 'spans') return park(event)", turn)
        self.assertIn("event.kind === 'spans-answered') return unpark(event)", turn)
        self.assertIn("event.kind === 'ended'", turn, "a run ended while parked gives it back")
        parked = page.split("function park(", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("document.getElementById('questions')", parked)
        self.assertIn("li.append(", parked)
        self.assertEqual(page.count('id="questions"'), 1, "one card")
        back = page.split("function unpark(", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("replaceWith(card)", back)

    def test_the_card_asks_what_the_run_waits_on_with_its_count(self):
        page = PAGE.read_text(encoding="utf-8")
        asks = page.split("function questions(", 1)[1].split("\n}\n", 1)[0]
        # A span gone to from a spec gate follows the park (issue 159).
        self.assertRegex(asks, r"asking\(marks, skipped, \(moving && moving\.mark\) "
                               r"\|\| rejecting, parkedOn[,)]")
        self.assertIn("' \\u00b7 ' + of", asks)

    def test_the_skip_button_tells_the_console_under_one(self):
        page = PAGE.read_text(encoding="utf-8")
        skip = page.split("on('.skip',", 1)[1].split("});", 1)[0]
        self.assertIn("ask('/skip', { id:", skip)
        self.assertIn("seeding", skip, "only a console has a run to skip in")


# A document as the browser keeps one: an element is found by its id only
# while it is on the page. A moved card in a line not yet appended is not.
DOCUMENT = """
const onPage = new Set(['panel', 'turns']);
function el(name) {
  return { name, parent: null, children: [], get parentNode() { return this.parent; },
           append(...kids) { for (const k of kids) if (typeof k === 'object') {
             k.parent = this; this.children.push(k); } },
           before(k) { k.parent = this.parent; },
           replaceWith(k) { k.parent = this.parent; this.parent = null; } };
}
const turns = el('turns'), panel = el('panel');
const card = el('card');
card.parent = panel;
function attached(e) { for (; e; e = e.parent) if (onPage.has(e.name)) return true; return false; }
const document = { createElement: el, createComment: () => el('comment'),
                   getElementById: id => id === 'questions' && attached(card) ? card : null };
let parkedOn = null, asked = [];
function questions() {
  if (!document.getElementById('questions')) throw new TypeError('the card is not on the page');
  asked.push(parkedOn);
}
"""


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class ParkedCardTest(unittest.TestCase):
    """The park asks its card once the card is on the page (a live console,
    2026-10-24: asked while its line was still being made, the card was found
    nowhere, the line was never added, and the card was lost with it)."""

    def test_the_card_is_asked_once_its_line_is_in_the_transcript(self):
        page = PAGE.read_text(encoding="utf-8")
        home = re.search(r"^const home = .*$", page, re.M).group(0)
        js = (DOCUMENT + home + "\n" + function(page, "park") + function(page, "unpark") + """
            (async () => {
              const line = park({ spans: ['m1', 'm3'], text: 'waits' });
              turns.append(line);
              await null;
              const there = attached(card) && card.parent === line;
              unpark({ text: 'answered' });
              return { asked, there, back: card.parent === panel };
            })().then(r => console.log(JSON.stringify(r)),
                      e => { console.log(JSON.stringify({ threw: String(e) })); });""")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout),
                         {"asked": [["m1", "m3"], None], "there": True, "back": True})


if __name__ == "__main__":
    unittest.main()
