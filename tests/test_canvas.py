"""The canvas loop: a click lands a mark, and the server stops when told.

These talk to the running server over HTTP, the way the page does. Nothing
here reaches inside the handler: a mark is real when it is on disk, and the
canvas is done when the port is free.
"""
import contextlib
import inspect
import io
import json
import re
import sys
import tempfile
import threading
import time
import types
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import marks as marks_store
from lib.canvas import Canvas, serve
from client import get, open_url, post


class CanvasTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.sheet = self.tmp / "sheet.png"
        self.sheet.write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")
        self.marks = self.tmp / "marks.json"
        self.canvas = Canvas(sheet=self.sheet, marks=self.marks)
        self.addCleanup(self.canvas.stop)
        self.canvas.start()

    def test_a_posted_mark_lands_in_marks_json(self):
        status, _ = post(self.canvas, "/marks",
                         {"view": "front", "pixel": [412, 208],
                          "text": "beak sits too low"})
        self.assertEqual(status, 200)
        stored = json.loads(self.marks.read_text())
        self.assertEqual(len(stored), 1)
        mark = stored[0]
        self.assertEqual(mark["view"], "front")
        self.assertEqual(mark["pixel"], [412, 208])
        self.assertEqual(mark["text"], "beak sits too low")
        self.assertEqual(mark["author"], "user")
        self.assertEqual(mark["status"], "open")
        self.assertTrue(mark["id"])

    def test_the_page_and_the_sheet_are_served(self):
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
            self.assertEqual(r.status, 200)
            self.assertIn("text/html", r.headers["Content-Type"])
        self.assertIn("<canvas", page)
        with open_url(self.canvas, "/sheet.png", timeout=5) as r:
            self.assertEqual(r.read(), self.sheet.read_bytes())
            self.assertEqual(r.headers["Content-Type"], "image/png")

    def test_the_page_fetches_nothing_from_the_internet(self):
        """ADR 0018's tripwire: needing a bundler means the scope went wrong."""
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        for smell in ("http://", "https://", "//cdn", "<script src", "<link"):
            self.assertNotIn(smell, page.replace("http://127.0.0.1", ""))

    def test_closing_a_mark_takes_it_out_of_the_open_count(self):
        """Only the user closes a mark, and this is the action they take."""
        _, mark = post(self.canvas, "/marks",
                       {"view": "front", "pixel": [1, 2], "text": "beak short"})
        status, closed = post(self.canvas, "/close", {"id": mark["id"]})
        self.assertEqual(status, 200)
        self.assertEqual(closed["status"], "closed")
        on_disk = json.loads(self.marks.read_text())
        self.assertEqual([m["status"] for m in on_disk], ["closed"])
        self.assertIsNone(marks_store.status_line(self.marks))

    def test_marks_from_an_earlier_session_are_served_and_closable(self):
        """A mark outlives its session, so the page must be able to see one
        it did not place — otherwise closing reaches almost nothing."""
        marks_store.append(self.marks, {"view": "top", "pixel": [9, 9],
                                        "text": "legs too close"})
        status, served = get(self.canvas, "/marks")
        self.assertEqual(status, 200)
        self.assertEqual([m["text"] for m in served], ["legs too close"])
        post(self.canvas, "/close", {"id": served[0]["id"]})
        self.assertIsNone(marks_store.status_line(self.marks))

    def test_the_page_loads_the_marks_on_file_and_offers_to_close_one(self):
        """No JS runs here, so this proves only the page's half of the
        contract: it asks for the marks on file, and it has a close action
        that needs no typing. What a closed one looks like is a HITL check."""
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn("'/marks'", page)
        self.assertIn("'/close'", page)
        self.assertIn(".closed", page)

    def test_done_stops_the_server_and_reports_what_was_captured(self):
        post(self.canvas, "/marks",
             {"view": "top", "pixel": [10, 20], "text": "legs too close"})
        post(self.canvas, "/done", {})
        report = self.canvas.wait()
        self.assertTrue(report["ok"])
        self.assertIn("1 mark", " ".join(report["lines"]))
        with self.assertRaises(urllib.error.URLError):
            open_url(self.canvas, "/", timeout=2)

    def test_the_page_beats_so_a_closed_tab_can_be_told_from_a_quiet_one(self):
        """Read from the source, as the no-internet tripwire above is: there is
        no browser here to run it, and a page that did not beat would leave the
        console's whole lifetime rule waiting for a signal nobody sends."""
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn("/beat", page)
        self.assertIn("setInterval", page)

    def test_a_beat_leaves_the_canvas_serving(self):
        """The page beats so a closed tab can be told from a quiet one, and a
        beat is the tab still open: it ends nothing (issue 110)."""
        status, _ = post(self.canvas, "/beat", {})
        self.assertEqual(status, 200)
        self.assertFalse(self.canvas.done)
        with open_url(self.canvas, "/", timeout=5) as r:
            self.assertEqual(r.status, 200)

    def test_the_page_labels_the_picture_with_the_build_it_is_of(self):
        """The sheet changes only when a build finishes, so a page showing one
        without saying which build it is of is authoritative about whichever
        picture happens to be on screen (ADR 0019, decision 13). The label sits
        with the picture and not in the marks column: it is a fact about what is
        being looked at, and it is read while looking at it."""
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        stage = page.split('id="stage"', 1)[1].split("</div>\n<aside", 1)[0]
        self.assertIn('id="build"', stage, "no label beside the picture")
        self.assertIn("'/sheet.json'", page, "the page never asks what it is of")

    def test_a_new_build_is_a_new_picture_and_never_a_cached_one(self):
        """A finished build updates the panel, and the panel is polled — so the
        picture's address is keyed on the build it is of rather than on the clock.
        A new build is then an address the browser has never seen and cannot
        satisfy from cache, and an unchanged one is the address it already holds,
        so a panel that is current costs no request at all."""
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn("'/sheet.png?b=' + ", page)
        self.assertNotIn("Date.now()", page.split("function show", 1)[1],
                         "the clock says nothing about which build this is")
        with open_url(self.canvas, "/sheet.png?b=4f3a9c21b0de", timeout=5) as r:
            self.assertEqual(r.read(), self.sheet.read_bytes())

    def test_the_launcher_says_it_can_mark_and_nothing_more(self):
        """One page, two hosts, and the page asks rather than assumes (ADR 0019).

        The launcher's answer is the whole of what a zero-dependency clone can
        do, and that is marking: ADR 0018 made the sheet the surface both
        parties point at, so a toolkit that could not mark without the console
        would have moved an existing capability behind an install.
        """
        status, said = get(self.canvas, "/can")
        self.assertEqual(status, 200)
        self.assertEqual(said, {"can": ["marks"]})

    def test_the_pages_console_surface_is_declared_not_assumed(self):
        """Read from the source, as the no-internet tripwire above is: there is
        no browser in this suite. What it pins is the page's side of the
        bargain — a console-only affordance says which capability it needs, and
        the launcher's ending says which capability it stands in for, so neither
        host is hard-coded into markup the other one is also served.
        """
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn('data-needs="drive"', page)
        self.assertIn('data-unless="drive"', page)

    def panel(self, name):
        """One section of the served page, by id. Read from the source, as every
        page test here is: there is no browser in this suite."""
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn(f'id="{name}"', page, f"no {name} on the page")
        return page.split(f'id="{name}"', 1)[1].split("</section>", 1)[0]

    def test_a_run_starts_from_prose_and_says_what_leaves_the_machine(self):
        """Prose, because the space's skills self-trigger on their descriptions:
        making the user pick one first moves a decision from the agent, which
        reads it from context, to the user, who has not described the task yet —
        and it has no answer for a run that is neither skill (ADR 0019).

        And the sentence: model content reaching the API is the named purpose of
        starting a run, said where a run is started. Rule 8 is a *git* boundary,
        so this is not a warning about a mistake — it is what the command is for,
        stated where somebody decides to do it."""
        run = self.panel("run")
        self.assertIn("<textarea", run)
        self.assertNotIn("<select", run, "a run does not start by picking a skill")
        self.assertRegex(run, r"(?i)anthropic")
        self.assertRegex(run, r"(?i)\bapi\b")
        with open_url(self.canvas, "/", timeout=5) as r:
            self.assertIn("'/run'", r.read().decode())

    def test_the_launcher_serves_no_run(self):
        """A capability is not only a thing the page hides. `contour canvas`
        declares `marks` and gains none of the console's endpoints, so the run is
        absent from the server as well as from the surface — otherwise the page's
        own restraint would be the whole of the boundary, and the page is the part
        a user can retype (ADR 0019)."""
        for path, body in (("/run", {"prompt": "build me a beak"}),
                           ("/verdict", {"id": "x", "allow": True}),
                           ("/end", {})):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                post(self.canvas, path, body)
            self.assertEqual(caught.exception.code, 404, path)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            get(self.canvas, "/events?since=0")
        self.assertEqual(caught.exception.code, 404)

    def test_nothing_touches_a_capabilitys_insides_as_the_page_loads(self):
        """The same failure as reaching for a removed affordance, one level in.

        Slice 07 learned this about `#done`: an element a host removes cannot be
        reached without a guard, or the page works for one host and throws for
        the other. Everything inside a declaring element is removed with it, so
        the run panel's own ids are in exactly that position — and `/can` is a
        request, so at load time they are all still there and all about to go.
        The rule that holds is that they are touched from a function and never as
        the page loads, because the only thing that calls those functions is the
        capability rule itself.
        """
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        script = page.split("<script>", 1)[1]
        inside = set(re.findall(r'id="([^"]+)"', self.panel("run"))) - {"run"}
        self.assertTrue(inside, "the run panel declares no affordances to check")
        depth = 0
        for line in script.split("\n"):
            if depth == 0:
                for got in inside:
                    self.assertNotIn(f"getElementById('{got}')", line,
                                     f"#{got} is inside a capability the host may "
                                     f"remove, and this runs before `/can` answers")
            depth += line.count("{") - line.count("}")

    def test_transcript_and_sheet_share_the_page_when_the_host_drives(self):
        """An equal split, and only under the console (ADR 0019, decision 13).

        The transcript is where decisions are visible and where a gate fires; the
        sheet is where a build is verified and where marks live. Neither is a
        sidebar to the other. Under the launcher there is no transcript, so the
        marks column stays the column it has always been — which is why the split
        is declared against the same capability the run panel is.
        """
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        style = page.split("<style>", 1)[1].split("</style>", 1)[0]
        self.assertRegex(style, r"body\.driving aside \{[^}]*width: 50%")
        self.assertRegex(style, r"aside \{[^}]*width: 300px",
                         "the launcher's column is still a column")
        script = page.split("<script>", 1)[1]
        depth, added = 0, False
        for line in script.split("\n"):
            if "classList.add('driving')" in line:
                self.assertGreater(depth, 0, "the launcher's page splits too")
                added = True
            depth += line.count("{") - line.count("}")
        self.assertTrue(added, "nothing ever asks for the split")

    def test_end_run_is_as_prominent_as_continue(self):
        """Not a link at the bottom. A run that ends at a gate and starts again
        never reaches compaction at all, and the spec is read from disk rather
        than recalled for the same reason — so ending a run is the sanctioned
        move and the page must not make it the reluctant one (ADR 0019).

        Read as layout, not as a feeling: the two sit in one container that
        divides the width between them, and nothing in the stylesheet shrinks or
        dims the ending."""
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        run = self.panel("run")
        pair = run.split('class="pair"', 1)[1].split("</div>", 1)[0]
        self.assertIn("Start run", pair)
        self.assertIn("End run", pair)
        style = page.split("<style>", 1)[1].split("</style>", 1)[0]
        self.assertRegex(style, r"\.pair button \{[^}]*flex: 1")
        # Nothing dims or shrinks it. `#end` may be coloured — every other
        # *stop and look* on this page is — but not made quieter than its pair.
        for rule in re.findall(r"#end \{([^}]*)\}", style):
            self.assertNotIn("opacity", rule)
            self.assertNotIn("font-size", rule)

    def test_the_gate_offers_no_way_to_edit_the_call(self):
        """A gate has two answers and a sentence. Editing the call would make the
        user the author of a change attributed to the agent — in the commit and in
        every later reading of why two builds differ — and this repo tracks
        authorship everywhere else: a mark carries an author, `addressed` is not a
        close. The gate is not the one place it gets laundered (ADR 0019, 13).

        A template rather than markup built in script, so that what the dialog
        contains is readable here and not inferred from the code that assembles
        it."""
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn('<template id="gate">', page)
        gate = page.split('<template id="gate">', 1)[1].split("</template>", 1)[0]
        self.assertIn('class="call"', gate, "the gate does not show the call")
        # One field, and it is the reason: the call is shown, never offered.
        self.assertEqual(gate.count("<input"), 1, gate)
        self.assertEqual(gate.count("<textarea"), 0, gate)
        self.assertIn("because", gate)
        # And what the page sends back carries no call either, so the absence is
        # not merely a dialog that happens to lack a field.
        script = page.split("<script>", 1)[1]
        body = re.search(r"ask\('/verdict', \{([^}]*)\}", script)
        self.assertIsNotNone(script and body, "the page never answers a gate")
        # `always` is an answer and not a piece of the call: a build gate's third
        # one, allow-and-write-the-ask-list (ADR 0025, decision 6).
        self.assertEqual(set(re.findall(r"(\w+):", body.group(1))),
                         {"id", "allow", "reason", "always"})

    def test_one_rule_applies_every_declaration(self):
        """The page asks its host once and enforces the answer in one place.

        Counted, not merely present: a second site that consults the answer is
        the beginning of a page that is really two pages, which is the mistake
        ADR 0019 named when it rejected sharing components between surfaces. A
        new affordance should need a declaration and no new code at all.
        """
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn("/can", page)
        # The script alone: the stylesheet names the same attributes to keep them
        # off screen until the answer lands, which is the same rule and not a
        # second one. What must stay singular is the code that acts on `can`.
        script = page.split("<script>", 1)[1]
        self.assertEqual(script.count("[data-needs]"), 1)
        self.assertEqual(script.count("[data-unless]"), 1)
        self.assertIn(".remove()", script)

    def test_nothing_reaches_for_an_affordance_its_host_removed(self):
        """Every declared element may be absent, so nothing may assume it.

        An unguarded `getElementById('done').addEventListener` throws under the
        console, which the launcher's own tests would never notice: the page
        works here and is broken there, from markup both are served. Each id
        that carries a declaration is checked, so a new affordance cannot be
        wired up the unsafe way either.
        """
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        declared = re.findall(r'id="([^"]+)"[^>]*data-(?:needs|unless)=', page)
        self.assertTrue(declared, "no declared affordance found to check")
        for got in declared:
            self.assertNotIn(f"getElementById('{got}').", page,
                             f"#{got} can be removed by its host, so reaching "
                             f"through it without a guard breaks the page")

    def test_an_unknown_capability_changes_nothing(self):
        """A host naming something this page has never heard of is not an error.

        The page's rule removes what the host lacks, so a name it does not know
        matches no element and does nothing — which is what makes a newer console
        safe in front of an older page. Nothing is reported, either: `/can` is
        written by us, and an unrecognised name there is our bug, not something
        to put in front of the user. `lib/policy.py` says its strangers out loud
        for the opposite reason — the user wrote that file.
        """
        odd = Canvas(sheet=self.sheet, marks=self.marks,
                     can=("marks", "teleport"))
        self.addCleanup(odd.stop)
        odd.start()
        status, said = get(odd, "/can")
        self.assertEqual(status, 200)
        self.assertEqual(said, {"can": ["marks", "teleport"]})
        # and the surface the name has nothing to do with is untouched
        status, _ = post(odd, "/marks", {"view": "front", "pixel": [10, 10],
                                         "text": "still works"})
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(self.marks.read_text())), 1)
        with open_url(odd, "/", timeout=5) as r:
            self.assertEqual(r.status, 200)

    def test_there_is_one_page_and_the_console_did_not_add_a_second(self):
        """ADR 0019 rejected two surfaces sharing components as *a bundler with
        a delay*. The page degrading to its host is what replaced that, so a
        second page appearing beside this one means the replacement was
        abandoned — and the sheet stops being the one surface both parties point
        at, which is ADR 0018's whole argument. If the page does outgrow one
        file, the console's extra views are served beside it, not bundled in.

        The lobby is the one other page, and it is not a second surface for a
        space: it sits above the spaces and shows no sheet (ADR 0021). Named
        here so any other page still fails this.
        """
        from lib import canvas as canvas_lib
        pages = sorted(Path(canvas_lib.__file__).parent.glob("*.html"))
        self.assertEqual([p.name for p in pages], ["canvas.html", "lobby.html"])

    def test_no_affordance_is_shown_before_the_host_has_answered(self):
        """`/can` is a request, so there is a moment before the answer arrives.

        Painted in that moment, the launcher's page shows the console's panel and
        the console's page shows the canvas's ending — each host briefly offering
        the other's surface, which is exactly what this slice exists to prevent.
        So whatever depends on the answer stays hidden until there is one.
        """
        with open_url(self.canvas, "/", timeout=5) as r:
            page = r.read().decode()
        self.assertIn("body:not(.asked) [data-needs]", page)
        self.assertIn("body:not(.asked) [data-unless]", page)
        self.assertIn("classList.add('asked')", page)


class TabTest(unittest.TestCase):
    """A canvas ends when its tab goes, as well as on Done (issue 110).

    A chat that opened one for the user left it holding the space after its tab
    closed, because nobody told them there was a Done to press. Nothing is lost
    by ending it: each mark was written as it arrived."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.sheet = self.tmp / "sheet.png"
        self.sheet.write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")
        self.marks = self.tmp / "marks.json"

    def canvas(self, grace=60, hidden_grace=60, reload_grace=0.5):
        canvas = Canvas(sheet=self.sheet, marks=self.marks, grace=grace,
                        hidden_grace=hidden_grace, reload_grace=reload_grace)
        self.addCleanup(canvas.stop)
        canvas.start()
        return canvas

    def ended(self, canvas, within=5):
        deadline = time.monotonic() + within
        while not canvas.done:
            self.assertLess(time.monotonic(), deadline, "the canvas never ended")
            time.sleep(0.05)

    def test_a_tab_that_says_it_is_going_ends_it_and_keeps_its_marks(self):
        canvas = self.canvas()
        post(canvas, "/beat", {"hidden": False})
        post(canvas, "/marks", {"view": "top", "pixel": [10, 20], "text": "legs"})
        post(canvas, "/going", {})
        self.ended(canvas)
        report = canvas.wait()
        self.assertTrue(report["ok"])
        self.assertIn("the tab closed, 1 mark kept", " ".join(report["lines"]))
        self.assertEqual(len(marks_store.load(self.marks)), 1)

    def test_a_reload_is_not_a_closed_tab(self):
        """A reload says going and then beats again: the canvas waits a moment
        for that beat rather than ending under the page that sent it."""
        canvas = self.canvas(reload_grace=1.0)
        post(canvas, "/beat", {"hidden": False})
        post(canvas, "/going", {})
        post(canvas, "/beat", {"hidden": False})
        time.sleep(1.5)
        self.assertFalse(canvas.done)

    def test_a_tab_on_screen_gone_silent_ends_it(self):
        """A browser that quit sends no word of it."""
        canvas = self.canvas(grace=0.3)
        post(canvas, "/beat", {"hidden": False})
        self.ended(canvas)
        self.assertIn("the tab closed", " ".join(canvas.wait()["lines"]))

    def test_done_still_reports_as_done(self):
        canvas = self.canvas()
        post(canvas, "/beat", {"hidden": False})
        post(canvas, "/done", {})
        self.assertIn("no marks captured", " ".join(canvas.wait()["lines"]))

    def test_contour_canvas_ends_with_its_tab(self):
        """The command itself, as a chat's `open` or a terminal starts it."""
        out, said = io.StringIO(), []
        with contextlib.redirect_stdout(out):
            thread = threading.Thread(target=lambda: said.append(serve(
                self.sheet, self.marks, open_browser=False,
                grace=60, hidden_grace=60, reload_grace=0.2)))
            thread.start()
            deadline = time.monotonic() + 5
            while "canvas at " not in out.getvalue():
                self.assertLess(time.monotonic(), deadline, "the canvas never said where")
                time.sleep(0.02)
        address = urllib.parse.urlparse(out.getvalue().split()[2])
        page = types.SimpleNamespace(
            origin=f"{address.scheme}://{address.netloc}",
            token=urllib.parse.parse_qs(address.query)["t"][0])
        post(page, "/beat", {"hidden": False})
        post(page, "/going", {})
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive(), "contour canvas outlived its tab")
        self.assertIn("the tab closed", " ".join(said[0]["lines"]))

    def test_it_closes_on_a_closed_tab_by_default(self):
        defaults = inspect.signature(serve).parameters
        for name in ("grace", "hidden_grace", "reload_grace"):
            self.assertIsNotNone(defaults[name].default, name)


if __name__ == "__main__":
    unittest.main()
