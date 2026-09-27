"""`contour-console`: the executable above the launcher, and its lifetime.

ADR 0019, decisions 1, 4, 11, 13, 17, 33. The console is the one layer allowed
dependencies, and the first thing it has to do well is not need them where it
does not: every test here runs it as a subprocess the way a person would type it,
`$CONTOUR_CONSOLE_PYTHON` stands in for the environment, and the run is driven by
a scripted stand-in rather than by the Claude Agent SDK. So the gate, the wait,
the hold and the lifetime are all provable on a clone with nothing installed,
which is the property `contour selftest` exists to defend.
"""
import ast
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import anchor, marks as marks_store, panel

from test_launcher import stages, stub_blender

CONSOLE = ROOT / "contour-console"
STAND_IN = Path(__file__).resolve().parent / "agent_stand_in.py"


class EnvironmentTest(unittest.TestCase):
    """The console needs an interpreter the launcher does not, which makes a
    missing environment the one error a first-time reader is guaranteed to hit.
    """

    def console(self, *args, cwd=None, **env):
        return subprocess.run([str(CONSOLE), *args], cwd=str(cwd or ROOT),
                              capture_output=True, text=True, timeout=60,
                              env=dict(os.environ, **env))

    def test_no_console_environment_says_so_and_how_to_make_one(self):
        """Never a traceback about an import: the reader has not installed
        anything wrong, they have not installed anything at all, and the
        message that helps is the command that fixes it."""
        r = self.console(CONTOUR_CONSOLE_PYTHON="/nowhere/python")
        said = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no console environment", said)
        self.assertIn("python3 -m venv", said)
        self.assertNotIn("Traceback", said)

    def test_help_works_with_no_environment_at_all(self):
        """The one thing that must answer on a bare clone besides the missing
        environment: what this is and what it takes. Asked before an interpreter
        is looked for, because needing an environment to be told you need one is
        the joke the two names exist to avoid."""
        r = self.console("--help", CONTOUR_CONSOLE_PYTHON="/nowhere/python")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--no-browser", r.stdout)

    def test_run_outside_a_model_space_says_so(self):
        """The launcher's rule, and for the launcher's reason: a console that
        fell back to the toolkit's own directory would open a page about
        something the user was not standing in (ADR 0015)."""
        elsewhere = Path(tempfile.mkdtemp())
        r = self.console(cwd=elsewhere, CONTOUR_CONSOLE_PYTHON=sys.executable)
        said = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not in a model space", said)
        self.assertNotIn("Traceback", said)


class ConsoleCase(unittest.TestCase):
    """Launching the console the way a person launches it.

    Shared because every console test needs the same three things and none of
    them is what is being proved: a throwaway space, a live process, and a way
    to stop it. `$CONTOUR_CONSOLE_PYTHON` stands in for the environment.
    """

    def space(self):
        space = Path(tempfile.mkdtemp())
        (space / ".contour").mkdir()
        (space / ".contour" / "project").write_text("# Contour model space\n")
        (space / "sheet.png").write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")
        return space

    def launch(self, space=None, *args, **env):
        """A live console, and the URL it says it is on.

        `--no-browser` because a test that opened a browser would be a test
        nobody could run twice in a row; it is a real flag for real headless
        cases, not a hook.
        """
        proc = subprocess.Popen(
            [str(CONSOLE), "--no-browser", *args], cwd=str(space or self.space()),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            env=dict(os.environ, CONTOUR_CONSOLE_PYTHON=sys.executable, **env))
        self.addCleanup(self.finish, proc)
        said = proc.stdout.readline()
        found = re.search(r"http://\S+", said)
        self.assertIsNotNone(found, f"no URL in what it said: {said!r}")
        return proc, found.group(0)

    def finish(self, proc):
        if proc.poll() is None:
            proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        if not proc.stdout.closed:
            proc.stdout.close()

    def ask(self, url, path, body=None):
        """One request, exactly as the page makes it: the token in a header,
        which is what makes it a request another site cannot forge, and JSON on
        a POST, which is the content type the server insists on. Here for the
        page's reason too — one place, so there is one place to get it wrong."""
        origin, token = url.split("/?")[0], url.split("t=")[1]
        req = urllib.request.Request(
            origin + path, headers={"X-Contour-Token": token},
            **({} if body is None else
               {"data": json.dumps(body).encode(), "method": "POST"}))
        if body is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as r:
            blob = r.read()
            return r.status, (json.loads(blob) if blob else None)

    def beat(self, url):
        """One heartbeat, exactly as the page sends it."""
        return self.ask(url, "/beat", {})[0]

    def keep_beating(self, url, proc, every=0.25):
        """A tab that is open and doing nothing: the Friday tab."""
        def loop():
            while proc.poll() is None:
                try:
                    self.beat(url)
                except (urllib.error.URLError, OSError):
                    return                    # the console ended; that is the test
                time.sleep(every)
        threading.Thread(target=loop, daemon=True).start()


class ServesTest(ConsoleCase):
    """The slice's demo: run it in a space and the sheet is in a browser.

    What is proved here includes the handover from the stdlib shim to the half
    that may have dependencies, which is why it is a subprocess and not a call.
    """

    def test_the_console_says_it_can_drive_as_well_as_mark(self):
        """Same page, bigger host. The console's answer to `/can` is the
        launcher's plus what only the console has, because the page degrades to
        its host rather than each host carrying a page of its own (ADR 0019).
        """
        _, url = self.launch()
        origin, token = url.split("/?")[0], url.split("t=")[1]
        with urllib.request.urlopen(f"{origin}/can?t={token}", timeout=10) as r:
            said = json.loads(r.read())
        self.assertIn("marks", said["can"])
        self.assertIn("drive", said["can"])

    def test_every_capability_the_page_asks_for_is_one_a_host_grants(self):
        """Page and hosts, checked against each other rather than separately.

        An affordance keyed on a name no server ever answers is invisible
        forever, and the page cannot notice: its rule removes what the host
        lacks, so a typo reads exactly like a capability the host does not have.
        The console's set comes over HTTP and not from an import, because from
        slice 08 `console/` may hold a dependency and this suite has to keep
        working on a bare clone.
        """
        from lib.canvas import MARKS_ONLY
        _, url = self.launch()
        origin, token = url.split("/?")[0], url.split("t=")[1]
        with urllib.request.urlopen(f"{origin}/can?t={token}", timeout=10) as r:
            granted = set(json.loads(r.read())["can"]) | set(MARKS_ONLY)
        with urllib.request.urlopen(url, timeout=10) as r:
            page = r.read().decode()
        asked = set(re.findall(r'data-(?:needs|unless)="([^"]+)"', page))
        self.assertTrue(asked, "the page declares no capability at all")
        self.assertEqual(asked - granted, set(),
                         "the page keys an affordance on a name no host answers")

    def test_the_console_serves_the_page_it_shares_with_the_canvas(self):
        """`lib/canvas.html`, not a copy: two copies of the page would drift,
        and the one that drifts is the one nobody is looking at."""
        _, url = self.launch()
        with urllib.request.urlopen(url, timeout=10) as r:
            self.assertEqual(r.read(), (ROOT / "lib" / "canvas.html").read_bytes())

    def test_the_page_is_served_the_spaces_own_sheet(self):
        """What is on the page is this space's render, not the toolkit's idea of
        one: the console was handed a space and everything it serves comes from
        there."""
        space = self.space()
        space.joinpath("sheet.png").write_bytes(b"\x89PNG\r\n\x1a\nthis space")
        _, url = self.launch(space)
        origin, token = url.split("/?")[0], url.split("t=")[1]
        with urllib.request.urlopen(f"{origin}/sheet.png?t={token}",
                                    timeout=10) as r:
            self.assertEqual(r.read(), b"\x89PNG\r\n\x1a\nthis space")
            self.assertEqual(r.headers["Content-Type"], "image/png")

    def test_the_console_exits_when_the_page_stops_beating(self):
        """Closing the last tab exits the process. A closed tab and a quiet one
        differ only in how long you wait, so the page beats and the console ends
        when the beats stop — there is no onbeforeunload that can be trusted to
        arrive."""
        proc, url = self.launch(CONTOUR_CONSOLE_GRACE="1")
        self.assertEqual(self.beat(url), 200)
        self.assertEqual(proc.wait(timeout=30), 0)

    def test_a_space_that_has_never_built_opens_on_an_empty_panel(self):
        """The console starts where a space starts: nothing built, nothing drawn.

        `contour canvas` refuses this, and is right to — it exists to mark a
        sheet. The console exists to *make* one, so refusing here would mean the
        one surface that can produce a first build cannot be opened until
        something else has. The panel is empty and says which build it is of,
        which is none (ADR 0019, decision 13).
        """
        bare = self.space()
        (bare / "sheet.png").unlink()
        proc, url = self.launch(bare)
        self.assertEqual(self.ask(url, "/sheet.json")[1]["build"], None)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.ask(url, "/sheet.png")
        self.assertEqual(caught.exception.code, 404)
        caught.exception.close()
        self.assertIsNone(proc.poll(), "the console is still standing")

    def test_an_idle_console_exits_even_while_the_tab_is_still_beating(self):
        """A beat proves a tab is open, not that anybody is there, so a beat must
        not reset the idle clock — or the tab left open on Friday keeps the run
        alive until Monday. The grace is set long here so that what ends this run
        can only be the idle timeout."""
        proc, url = self.launch(CONTOUR_CONSOLE_IDLE="2",
                                CONTOUR_CONSOLE_GRACE="60")
        self.keep_beating(url, proc)
        self.assertEqual(proc.wait(timeout=40), 0)
        self.assertIn("idle", proc.stdout.read())

    def test_a_request_without_the_session_token_is_refused(self):
        """Slice 01's authentication, inherited rather than rebuilt: the console
        carries an *allow*, so a request the user never made must not reach a
        handler. This passed the moment the console used the canvas's server,
        which is the argument for using it."""
        _, url = self.launch()
        origin = url.split("/?")[0]
        for req in (urllib.request.Request(origin + "/marks"),
                    urllib.request.Request(origin + "/marks", data=b"{}",
                                           method="POST",
                                           headers={"Content-Type":
                                                    "application/json"})):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(req, timeout=10)
            self.assertEqual(caught.exception.code, 403, req.get_method())

    def test_ctrl_c_leaves_no_server_listening_and_no_lock_held(self):
        """The console is an instrument somebody is holding, so it is going to be
        interrupted. Two things must not survive: a port still answering, which
        would make the next run look like a port conflict, and a hold on the
        space, which would wedge it behind a file the user would have to know
        about."""
        space = self.space()
        proc, url = self.launch(space)
        with urllib.request.urlopen(url, timeout=10) as r:
            r.read()                          # it was serving before the signal
        proc.send_signal(signal.SIGINT)
        code = proc.wait(timeout=30)
        said = proc.stdout.read()
        with self.assertRaises((urllib.error.URLError, OSError)):
            urllib.request.urlopen(url, timeout=5).read()
        self.assertFalse((space / ".contour" / "run.lock").exists())
        # An interrupt the console handled, not one that killed it where it
        # stood: the port closes either way, and only one of those releases
        # what a later slice will be holding when the signal arrives.
        self.assertIn("interrupted", said)
        self.assertNotIn("Traceback", said)
        self.assertEqual(code, 130)


    def test_the_panel_says_which_build_the_sheet_is_of(self):
        """The console labels the sheet from the same two files the launcher
        wrote: `views.json` says which build the cameras drew, and the verdict
        beside the build log says what the last check came to. A build that
        raised leaves the previous `.blend` in place, so without the verdict the
        panel would call a picture of a build that never finished current."""
        space = self.space()
        out = space / "out"
        out.mkdir()
        blend = out / f"{space.name}.blend"
        blend.write_bytes(b"a blend")
        anchor.record(out / "views.json", [1024, 1024],
                      [{"label": "front", "tile": [0, 0, 512, 512]}], blend)
        panel.record(space / ".contour" / panel.NAME, {"ok": False, "lines": []})
        _, said = self.ask(self.launch(space)[1], "/sheet.json")
        self.assertEqual(said["build"], anchor.fingerprint(blend))
        self.assertFalse(said["current"])
        self.assertIn("last build failed", said["why"])


class RunTest(ConsoleCase):
    """The heart of ADR 0019: prose in, a driven agent, every call gated.

    The agent is scripted rather than real (`tests/agent_stand_in.py`), because
    what is being proved is the console's — the transcript, the gate, the wait,
    the lock. That the Claude Agent SDK drives the same seam is confirmed by
    hand, since the suite has to pass on a clone with nothing installed.
    """

    def driven(self, *script, **env):
        """A console whose agent does exactly these things, in this order.

        `$CONTOUR_HOME` points at an empty directory unless a test says
        otherwise, so the policy in force is the one the design starts from —
        an ask-list nobody has written, which gates everything — and never the
        ask-list of whoever is running the suite.
        """
        env.setdefault("CONTOUR_HOME", tempfile.mkdtemp())
        return self.launch(env.pop("space", None),
                           CONTOUR_CONSOLE_AGENT=f"{STAND_IN}:drive",
                           CONTOUR_AGENT_SCRIPT=json.dumps(list(script)), **env)

    def gate(self, url):
        """The one gate now waiting, once it is."""
        said = self.transcript(url, lambda ev: any(e["kind"] == "gate" for e in ev))
        return [e for e in said if e["kind"] == "gate"][0], said

    def transcript(self, url, until, timeout=15):
        """Everything the page would have on screen, once `until` is true of it.

        Polled, as the page polls: the transcript is a cursor over a list, so a
        reloaded tab and a slow test read it the same way.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            _, said = self.ask(url, "/events?since=0")
            if until(said["events"]):
                return said["events"]
            time.sleep(0.1)
        self.fail(f"transcript never satisfied {until}: {said['events']!r}")

    def test_a_prose_prompt_starts_a_run_and_the_agent_answers_it(self):
        """The slice's demo. Prose, not a skill chosen from a list: the space's
        skills self-trigger on their descriptions, so picking one first moves a
        decision from the agent, which reads it from context, to the user, who
        has not described the task yet (ADR 0019)."""
        _, url = self.driven({"say": "measuring the beak against refs/side.png"})
        status, _ = self.ask(url, "/run", {"prompt": "why is the neck 269"})
        self.assertEqual(status, 200)
        said = self.transcript(url, lambda ev: any(e["kind"] == "text" for e in ev))
        kinds = [(e["kind"], e.get("text")) for e in said]
        self.assertEqual(kinds[0], ("prompt", "why is the neck 269"))
        self.assertIn(("text", "measuring the beak against refs/side.png"), kinds)

    def test_a_classified_call_raises_a_gate_naming_what_the_call_means(self):
        """A gate says *a build*, not *a Bash command matching this glob*. One
        intent has four spellings and a permission list needing one rule per
        spelling will still have a hole, so the launcher is asked what a call
        means (ADR 0019, decision 20)."""
        _, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}})
        self.ask(url, "/run", {"prompt": "check the build"})
        gate, said = self.gate(url)
        self.assertEqual(gate["category"], "build")
        self.assertEqual(gate["call"]["command"], "./contour check")
        # A gate, so nothing has happened yet: the call has no outcome on the
        # transcript, which is the difference between gating and logging.
        self.assertEqual([e for e in said if e["kind"] == "result"], [])

    def test_what_the_ask_list_allows_runs_without_being_asked_about(self):
        """The ask-list is the whole of what is not gated, and it is an
        allow-list with no presets: the default gates everything, and this is the
        user widening it for this space by name. A category the file does not
        mention is asked about, which is how a category the toolkit gains later
        arrives as a gate that is noticed and then decided (ADR 0019)."""
        space, home = self.space(), Path(tempfile.mkdtemp())
        (home / "ask-list.yaml").write_text(
            f"spaces:\n  {space}:\n    allow:\n      - build\n")
        _, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                             space=space, CONTOUR_HOME=str(home))
        self.ask(url, "/run", {"prompt": "check the build"})
        said = self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        self.assertEqual([e for e in said if e["kind"] == "gate"], [])
        self.assertTrue([e for e in said if e["kind"] == "result"][0]["allowed"])

    def test_allow_lets_the_call_happen_and_the_run_carries_on(self):
        """The gate is a pause, not a branch in the run: answered, the agent gets
        its call and goes on to the next thing it was doing."""
        _, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                             {"say": "the check is green"})
        self.ask(url, "/run", {"prompt": "check the build"})
        gate, _ = self.gate(url)
        self.assertEqual(self.ask(url, "/verdict",
                                  {"id": gate["id"], "allow": True})[0], 200)
        said = self.transcript(
            url, lambda ev: any(e.get("text") == "the check is green" for e in ev))
        self.assertTrue([e for e in said if e["kind"] == "result"][0]["allowed"])

    def test_deny_hands_the_agent_the_sentence_as_the_calls_result(self):
        """The cheapest correction channel in the system: a sentence, at the
        moment it applies, instead of a paragraph after the fact. The reason is
        not a log line — it comes back as what the call returned, which is the
        only place the agent will read it (ADR 0019, decision 13)."""
        _, url = self.driven({"call": {"tool": "Bash", "command": "git commit -m wip"}})
        self.ask(url, "/run", {"prompt": "tidy up"})
        gate, _ = self.gate(url)
        self.assertEqual(gate["category"], "commit")
        self.ask(url, "/verdict", {"id": gate["id"], "allow": False,
                                   "reason": "not until the neck measures 280"})
        said = self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        got = [e for e in said if e["kind"] == "result"][0]
        self.assertFalse(got["allowed"])
        self.assertEqual(got["text"], "not until the neck measures 280")
        # and the decision is on the transcript too, because it is as much part
        # of the run as the call was — slice 11 turns this into a veto.
        spoken = [e for e in said if e["kind"] == "verdict"][0]
        self.assertEqual(spoken["text"], "not until the neck measures 280")

    def test_an_unanswered_gate_waits_and_holds_off_the_idle_timeout(self):
        """Silence is not a verdict, in either direction. The console never
        answers a gate on the user's behalf, and slice 06's idle timeout must not
        answer one by ending the run — otherwise the lifetime rule quietly
        becomes the timeout policy ADR 0019 rejects. The practical case is worse
        than the principled one: a refused agent works around the refusal, so an
        unattended run would spend its time productively doing the wrong thing.
        """
        proc, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                                CONTOUR_CONSOLE_IDLE="2", CONTOUR_CONSOLE_GRACE="60")
        self.keep_beating(url, proc)
        self.ask(url, "/run", {"prompt": "check the build"})
        gate, _ = self.gate(url)
        time.sleep(6)                         # three idle timeouts' worth
        self.assertIsNone(proc.poll(), "the console ended at an unanswered gate")
        _, said = self.ask(url, "/events?since=0")
        self.assertEqual([e for e in said["events"] if e["kind"] == "result"], [],
                         "the call happened without anybody answering for it")
        # Answered, the clock starts again: the suppression is the gate's, and it
        # lasts exactly as long as the gate does.
        self.ask(url, "/verdict", {"id": gate["id"], "allow": False,
                                   "reason": "measure it first"})
        self.assertEqual(proc.wait(timeout=40), 0)
        self.assertIn("idle", proc.stdout.read())

    def marked(self, space):
        """A space the user has marked and has not resolved: a build on disk, a
        sheet drawn from that build, and a pin still carrying the pixel it was
        born with (ADR 0018)."""
        out = space / "out"
        out.mkdir(exist_ok=True)
        blend = out / f"{space.name}.blend"
        blend.write_bytes(b"a blend")
        anchor.record(out / "views.json", [1024, 1024],
                      [{"label": "front", "tile": [0, 0, 512, 512]}], blend)
        marks_store.append(space / marks_store.NAME,
                           {"view": "front", "pixel": [10, 10],
                            "text": "the neck is short"})
        return space

    def test_an_approved_build_casts_the_rays_before_the_agent_is_let_through(self):
        """ADR 0019, decision 14, and the whole of this slice. The sheet is
        always on screen, so it can always be clicked, and a rebuild would
        otherwise invalidate a mark mid-typing. The console owns the build, so it
        knows the instant before geometry changes — a strictly better place to
        cast rays than session close ever was (decision 8).

        Ordering is the claim: the agent is holding a verdict it cannot act on
        until the gate returns, so a resolve that has happened by the time the
        call has a result is a resolve that happened before the build.
        """
        space = self.marked(self.space())
        _, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                             space=space, BLENDER=str(stub_blender(space)))
        self.ask(url, "/run", {"prompt": "the neck is short — fix it"})
        gate, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": gate["id"], "allow": True})
        self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        self.assertEqual(stages(space), ["resolve"])

    def test_a_build_the_ask_list_allows_still_resolves_first(self):
        """The cost of decision 14 is a click per build, and the sanctioned
        relief is this — a deliberate per-space ask-list entry. What it buys is
        not being asked; it is not permission for a rebuild to invalidate a mark
        mid-typing. So resolution hangs off the *allow*, not off the dialog, and a
        user who widened the list keeps their pins.
        """
        space, home = self.marked(self.space()), Path(tempfile.mkdtemp())
        (home / "ask-list.yaml").write_text(
            f"spaces:\n  {space}:\n    allow:\n      - build\n")
        _, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                             space=space, CONTOUR_HOME=str(home),
                             BLENDER=str(stub_blender(space)))
        self.ask(url, "/run", {"prompt": "check the build"})
        said = self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        self.assertEqual([e for e in said if e["kind"] == "gate"], [],
                         "the ask-list did not let the build through")
        self.assertEqual(stages(space), ["resolve"])

    def test_a_build_with_nothing_to_anchor_pays_for_no_blender(self):
        """The gate is the most-pressured one in the system, and most builds have
        no new pin waiting: a Blender startup on every approval would be a second
        a click long, paid for nothing. The same question `contour canvas` asks
        before it resolves at close, asked by importing `lib/` — which is the half
        of decision 28 this file may do in its own process.
        """
        space = self.space()
        _, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                             space=space, BLENDER=str(stub_blender(space)))
        self.ask(url, "/run", {"prompt": "check the build"})
        gate, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": gate["id"], "allow": True})
        self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        self.assertEqual(stages(space), [])

    def test_a_denied_build_casts_no_rays(self):
        """Resolution is not a side effect of asking — it is what happens
        immediately before geometry changes. A denial means nothing is about to
        change, and the pixel is still the best thing the mark has: rays cast now
        would spend a Blender startup to reach exactly the same answer they will
        reach at the build the user eventually allows.
        """
        space = self.marked(self.space())
        _, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                             space=space, BLENDER=str(stub_blender(space)))
        self.ask(url, "/run", {"prompt": "check the build"})
        gate, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": gate["id"], "allow": False,
                                   "reason": "measure the neck first"})
        self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        self.assertEqual(stages(space), [])
        # And the pin is untouched: it still carries the pixel it was born with.
        self.assertTrue(anchor.unresolved(marks_store.load(space / marks_store.NAME)))

    def test_approving_something_that_is_not_a_build_casts_no_rays(self):
        """Resolution is tied to the *build* category and not to approval itself.
        A spec write is approved at a gate too, and it changes no geometry — so
        rays cast on it would anchor the pins the user is still placing against a
        sheet that is about to stay exactly as it is, and drop the pixels that
        let them be cast again later.
        """
        space = self.marked(self.space())
        _, url = self.driven({"call": {"tool": "Bash",
                                       "command": "python3 -c \"open('spec.yaml','w')\""}},
                             space=space, BLENDER=str(stub_blender(space)))
        self.ask(url, "/run", {"prompt": "the neck should be 280"})
        gate, _ = self.gate(url)
        self.assertEqual(gate["category"], "spec-write")
        self.ask(url, "/verdict", {"id": gate["id"], "allow": True})
        self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        self.assertEqual(stages(space), [])

    def test_the_transcript_says_what_resolution_came_to_and_when(self):
        """A mark the user placed changes shape at this moment — its pixel is
        spent and an anchor takes its place — and the transcript is where the run
        is visible. Said in the run's own words, before the call it went ahead of,
        so the order on screen is the order it happened in: this is why a later
        pin sits where it does, and there is nowhere else that records it.
        """
        space = self.marked(self.space())
        _, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                             space=space, BLENDER=str(stub_blender(space)))
        self.ask(url, "/run", {"prompt": "the neck is short — fix it"})
        gate, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": gate["id"], "allow": True})
        said = self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        kinds = [e["kind"] for e in said]
        self.assertIn("resolved", kinds, "the rays were cast and nobody was told")
        self.assertIn("resolve", [e for e in said if e["kind"] == "resolved"][0]["text"])
        self.assertLess(kinds.index("resolved"), kinds.index("result"))

    def test_resolution_that_fails_says_so_and_does_not_cancel_the_build(self):
        """Bookkeeping about a pin does not get to veto a call the user
        personally approved. The mark is not lost when this happens — it still
        carries its pixel, and the panel already labels a sheet the build has
        moved past — so the cost of going ahead is one pin resolved later, while
        the cost of refusing is a build the user asked for and did not get.

        Loudly, though: the lines are the launcher's own, on the transcript,
        because rays that were meant to be cast and were not is exactly the sort
        of quiet that makes a pin land somewhere wrong two builds later.
        """
        space = self.marked(self.space())
        _, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                             space=space, BLENDER="/nowhere/blender")
        self.ask(url, "/run", {"prompt": "the neck is short — fix it"})
        gate, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": gate["id"], "allow": True})
        said = self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        self.assertTrue([e for e in said if e["kind"] == "result"][0]["allowed"],
                        "a failed resolve took the build down with it")
        told = " ".join(e["text"] for e in said if e["kind"] == "resolved")
        self.assertTrue(told.strip(), "resolution failed and said nothing")
        self.assertTrue(anchor.unresolved(marks_store.load(space / marks_store.NAME)),
                        "the pin lost its pixel without gaining an anchor")

    def test_a_run_holds_the_space_and_a_terminal_check_is_refused(self):
        """Slice 02's lock, taken by a run and not by a build: what actually
        races over a space is the `build.py` editing *between* builds, so a
        build-scoped lock would look like a fix and not be one. The lock is the
        launcher's — the console takes the same one through the same module,
        because a lock the console owned would put privilege in the one layer
        allowed to carry dependencies and would leave terminal-versus-terminal,
        which races today, unprotected (ADR 0019, decision 17).
        """
        from lib import lock
        space = self.space()
        # Parked at a gate, which is a run that is unambiguously still live: the
        # hold lasts as long as the run, so a script that had already finished
        # would be asking about a hold that was rightly gone.
        _, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                             space=space)
        self.ask(url, "/run", {"prompt": "measure the beak"})
        self.gate(url)
        record = lock.holder(space)
        self.assertIsNotNone(record, "the run did not hold the space")
        # The refusal a person actually meets, from the launcher they typed.
        # `$BLENDER` points nowhere so that a check which was *not* refused
        # cannot go on to spend a minute in Blender before failing.
        r = subprocess.run([str(ROOT / "contour"), "check"], cwd=str(space),
                           capture_output=True, text=True, timeout=60,
                           env=dict(os.environ, BLENDER="/nowhere/blender"))
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("is held by", r.stderr)
        # The run's own builds are not refused by the run's own hold: the lock is
        # between sessions, and a session that could not build would make it
        # useless for the thing it protects.
        self.assertEqual(lock.take(space, "check", run=record["run"])["run"],
                         record["run"])

    def test_a_finished_run_says_so_and_gives_the_space_back(self):
        """The hold lasts exactly as long as the run. A run that ended while
        still holding would wedge the space behind a file the user would have to
        know about, which is the failure slice 02's `free` exists to prevent."""
        from lib import lock
        space = self.space()
        _, url = self.driven({"say": "measured: 269 against a stated 280"},
                             space=space)
        self.ask(url, "/run", {"prompt": "measure the neck"})
        self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        self.assertIsNone(lock.holder(space))

    def test_ctrl_c_during_a_live_run_gives_the_space_back(self):
        """The console is an instrument somebody is holding, so it is going to be
        interrupted — and the likeliest moment is while a run is parked at a gate,
        which is precisely when it holds the space. A hold that survived the
        process would wedge the space behind a file the user would have to know
        about."""
        from lib import lock
        space = self.space()
        proc, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                                space=space)
        self.ask(url, "/run", {"prompt": "check the build"})
        self.gate(url)
        self.assertIsNotNone(lock.holder(space), "the run did not hold the space")
        proc.send_signal(signal.SIGINT)
        self.assertEqual(proc.wait(timeout=30), 130)
        self.assertIsNone(lock.holder(space))
        self.assertNotIn("Traceback", proc.stdout.read())

    def test_a_run_that_reaches_a_context_limit_carries_on(self):
        """A limit is news, not an ending. It is the same argument as the
        timeout: a limit the user did not choose interrupting work they were
        watching. So it appears on the transcript — they should know the harness
        compacted — and the run goes on to the next thing, and the only thing
        that ends a run is the run ending."""
        space = self.space()
        proc, url = self.driven({"limit": "compacted at 200k tokens"},
                                {"say": "carrying on with the beak"}, space=space)
        self.ask(url, "/run", {"prompt": "measure every part"})
        said = self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        self.assertEqual([e["kind"] for e in said],
                         ["prompt", "limit", "text", "ended"])
        self.assertIsNone(proc.poll(), "the console ended at a context limit")

    def test_end_run_ends_the_run_and_leaves_the_console_standing(self):
        """Ending a run is not closing the console. A run that ends at a gate and
        starts again never reaches compaction at all, so ending one has to be
        cheap and repeatable — which is why **End run** gets as much prominence
        on the page as continue (ADR 0019)."""
        from lib import lock
        space = self.space()
        proc, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                                space=space)
        self.ask(url, "/run", {"prompt": "check the build"})
        self.gate(url)
        self.assertEqual(self.ask(url, "/end", {})[0], 200)
        self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        self.assertIsNone(lock.holder(space), "the ended run still holds the space")
        self.assertIsNone(proc.poll(), "ending the run closed the console")
        self.assertEqual(self.ask(url, "/run", {"prompt": "again, smaller"})[0], 200)

    def test_a_second_run_is_refused_while_one_is_live(self):
        """One run at a time, and it says so rather than starting a second. Two
        runs over one console would be two agents in one space with one gate
        between them — and the space's own lock, which is what stops that
        between sessions, would let them both through because they belong to the
        same run id."""
        _, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}})
        self.ask(url, "/run", {"prompt": "the one that is happening"})
        self.gate(url)
        _, said = self.ask(url, "/run", {"prompt": "the one that is not"})
        self.assertFalse(said["started"])
        self.assertIn("run", said["why"])
        _, whole = self.ask(url, "/events?since=0")
        self.assertEqual([e["kind"] for e in whole["events"]], ["prompt", "gate"])

    def test_a_verdict_cannot_rewrite_the_call_it_answers(self):
        """The same rule as the dialog's missing field, enforced where it cannot
        be got around: the server reads an id, a verdict and a sentence off the
        body, so a caller that sends a call sends it into nothing. Otherwise the
        page's restraint would be the whole of the guarantee, and the page is the
        part a user can retype."""
        _, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}})
        self.ask(url, "/run", {"prompt": "check the build"})
        gate, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": gate["id"], "allow": True, "tool": "Bash",
                                   "call": {"command": "git push --force"}})
        said = self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        self.assertEqual([e for e in said if e["kind"] == "result"][0]["ran"],
                         {"command": "./contour check"})


class InheritsTest(unittest.TestCase):
    """What the agent is told, and what it is left to discover (ADR 0019, 21).

    Imported rather than launched: `console/run.py` is the console's stdlib half
    on purpose, and a test that could only run with `claude-agent-sdk` installed
    would stop proving this on the clone `contour selftest` defends.
    """

    def test_the_agent_is_pointed_at_the_space_and_told_nothing_else(self):
        """No system prompt. The SDK is pointed at the space and discovers what
        Claude Code discovers — its `CLAUDE.md`, its `.claude/settings.json`, its
        skills. A hand-rolled prompt here would yield an agent following
        whichever of the eight rules its author remembered, in a second place
        that drifts."""
        from console import run as run_lib
        opts = run_lib.options("/tmp/somewhere", {"run": "4b1284a24b754800"})
        self.assertEqual(opts["cwd"], "/tmp/somewhere")
        self.assertNotIn("system_prompt", opts)
        # The toolkit is on the agent's PATH, which is what makes the space's own
        # `contour hook spec` resolve — so the guard that denies a ref write is
        # the installed one, firing before any gate could offer to allow it.
        self.assertIn(str(ROOT), opts["env"]["PATH"].split(os.pathsep))
        # And the agent's own builds join this run's hold instead of meeting it.
        self.assertEqual(opts["env"]["CONTOUR_RUN"], "4b1284a24b754800")

    def test_the_agent_is_told_to_read_the_spaces_own_configuration(self):
        """Discovery is a decision, and the default is to discover nothing: an
        agent given no setting sources reads no `CLAUDE.md`, no
        `.claude/settings.json` — so no `contour hook spec` — and none of the
        space's skills. The console would then have replaced the space's
        discipline with silence, which is the same failure as restating it badly
        and harder to notice. Named here rather than in the driver, because it is
        the console's decision and has to be checkable without the SDK."""
        from console import run as run_lib
        opts = run_lib.options("/tmp/somewhere", {"run": "abc"})
        self.assertEqual(sorted(opts["setting_sources"]),
                         ["local", "project", "user"])

    def spoken(self, path):
        """Every name and string this file's *code* uses, prose left out.

        Docstrings and comments are how the console explains a decision, and
        explaining one is the opposite of restating it. What would restate the
        discipline is a literal the code passes or a keyword it sets, so that is
        what this reads.
        """
        tree = ast.parse(path.read_text())
        prose = set()
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                    and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                prose.add(id(body[0].value))
        said = {n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and id(n) not in prose}
        said |= {n.arg for n in ast.walk(tree) if isinstance(n, ast.keyword) and n.arg}
        return said | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}

    def test_the_console_restates_none_of_the_spaces_discipline(self):
        """The negative half of the same decision, checked against the code: the
        console neither writes the agent a prompt nor reads the space's rules
        itself. Either would be a second copy of the discipline, and the copy
        that drifts is the one nobody is reading."""
        for f in sorted((ROOT / "console").glob("*.py")):
            for said in self.spoken(f):
                self.assertNotIn("CLAUDE", said, f)
                self.assertNotIn("system_prompt", said, f)
