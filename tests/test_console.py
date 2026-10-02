"""`contour-console`: the executable above the launcher, and its lifetime.

ADR 0019, decisions 1, 2, 34, 13, 17, 23. The console is the one layer allowed
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

from console import spend
from lib import marks as marks_store, panel, views

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

    def servers(self):
        """Every `console.server` alive on this machine, by pid.

        Asked of the machine and not of the shim, because the failure this looks
        for is a server that outlived the process that launched it: a child the
        parent still knows about is not the thing that wedges a space.
        """
        found = subprocess.run(["pgrep", "-f", "console.server"],
                               capture_output=True, text=True)
        return {int(pid) for pid in found.stdout.split()}

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

    def test_a_tab_that_said_it_is_hidden_outlives_the_grace(self):
        """A browser slows or stops the timers of a tab nobody is looking at:
        you enter a space, then go back to the lobby. That silence is not a
        closed tab's (issue 39)."""
        proc, url = self.launch(CONTOUR_CONSOLE_GRACE="0.5")
        self.ask(url, "/beat", {"hidden": True})
        time.sleep(2)
        self.assertIsNone(proc.poll(), "the console ended under a hidden tab")

    def test_a_hidden_tab_that_never_comes_back_still_ends(self):
        """A browser that quit with the tab behind another sends no word of it,
        so the long grace bounds a console that outlived its tab."""
        proc, url = self.launch(CONTOUR_CONSOLE_GRACE="0.2",
                                CONTOUR_CONSOLE_HIDDEN_GRACE="1.5")
        self.ask(url, "/beat", {"hidden": True})
        time.sleep(0.8)
        self.assertIsNone(proc.poll(), "ended on the short grace")
        self.assertEqual(proc.wait(timeout=30), 0)
        self.assertIn("the page closed", proc.stdout.read())

    def test_a_tab_that_says_it_is_going_ends_it_promptly(self):
        """Closing the tab still ends the console within seconds: the page says
        so as it goes, and no grace is waited out."""
        proc, url = self.launch(CONTOUR_CONSOLE_GRACE="60")
        self.ask(url, "/beat", {"hidden": True})
        self.ask(url, "/going", {})
        self.assertEqual(proc.wait(timeout=5), 0)
        self.assertIn("the page closed", proc.stdout.read())

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

    def test_ctrl_c_while_the_browser_is_still_opening_is_handled_too(self):
        """A browser can take seconds to come up, and a Ctrl-C in those
        seconds is the same Ctrl-C: the lobby had it escape as a traceback, and
        so did this (issue 36). `$BROWSER` stands in for one that has not
        answered yet."""
        space = self.space()
        opening = space / "browser-opening"
        slow = Path(tempfile.mkdtemp()) / "browser"
        slow.write_text(f"#!/bin/sh\ntouch {opening}\nsleep 30\n")
        slow.chmod(0o755)
        proc = subprocess.Popen(
            [str(CONSOLE)], cwd=str(space), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True,
            env=dict(os.environ, CONTOUR_CONSOLE_PYTHON=sys.executable,
                     BROWSER=str(slow)))
        self.addCleanup(self.finish, proc)
        deadline = time.monotonic() + 30
        while not opening.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertTrue(opening.exists(), "the browser was never asked to open")
        proc.send_signal(signal.SIGINT)
        code = proc.wait(timeout=30)
        said = proc.stdout.read()
        self.assertNotIn("Traceback", said)
        self.assertIn("interrupted", said)
        self.assertEqual(code, 130)
        self.assertFalse((space / ".contour" / "run.lock").exists())


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
        views.record(out / "views.json", [1024, 1024],
                      [{"label": "front", "tile": [0, 0, 512, 512]}], blend)
        panel.record(space / ".contour" / panel.NAME, {"ok": False, "lines": []})
        _, said = self.ask(self.launch(space)[1], "/sheet.json")
        self.assertEqual(said["build"], views.fingerprint(blend))
        self.assertFalse(said["current"])
        self.assertIn("last build failed", said["why"])


class SignalTest(ConsoleCase):
    """What happens to the server when the shim is told to go.

    `contour-console` is a shim in front of `python -m console.server`, and the
    signal a console meets is not always the one a person typed: a terminated
    console, a closed terminal, a test harness tidying up. Every one of them has
    the same two things to give back — the port, and the space's hold — and
    exactly one way to give them back, which is to be asked (issue 27).
    """

    def test_a_terminated_console_leaves_no_server_behind(self):
        """SIGTERM is what anything that is not a person sends, and it is what
        this suite's own cleanup sends. A shim that dies where it stands leaves
        the server reparented to init with its port still bound and no page, no
        parent and no terminal — which is not an ending, it is a stray."""
        space = self.space()
        before = self.servers()
        proc, url = self.launch(space)
        started = self.servers() - before
        self.assertEqual(len(started), 1, f"one server, not {started}")
        self.addCleanup(self.reap, started)
        proc.terminate()
        proc.wait(timeout=30)
        self.assertEqual(self.servers() & started, set(),
                         "the server outlived the console that launched it")
        with self.assertRaises((urllib.error.URLError, OSError)):
            urllib.request.urlopen(url, timeout=5).read()

    def test_a_terminated_console_gives_the_space_back(self):
        """The hold is the half that outlives a killed console worst. A port
        still answering makes the next console look like a port conflict; a hold
        still held wedges the space behind a `run.lock` naming a pid with no
        terminal, no page and no parent, and `lock.alive` asks the kernel, which
        says yes. So the user's next `contour check` in their own space is
        refused by a console nobody can go and look at."""
        from lib import lock
        space = self.space()
        before = self.servers()
        proc, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                                space=space)
        self.addCleanup(self.reap, self.servers() - before)
        self.ask(url, "/run", {"prompt": "check the build"})
        self.gate(url)
        self.assertIsNotNone(lock.holder(space), "the run did not hold the space")
        proc.terminate()
        proc.wait(timeout=30)
        self.assertIsNone(lock.holder(space), "the run kept the space it was holding")
        # The refusal a person would meet, from the launcher they would type.
        # `$BLENDER` points nowhere so a check that was *not* refused fails for
        # its own reason instead of spending a minute in Blender first.
        r = subprocess.run([str(ROOT / "contour"), "check"], cwd=str(space),
                           capture_output=True, text=True, timeout=60,
                           env=dict(os.environ, BLENDER="/nowhere/blender"))
        self.assertNotIn("is held by", r.stderr)

    def test_a_closed_terminal_ends_the_console_and_says_which_signal_did(self):
        """SIGHUP is what a closed terminal sends, and the console has no way to
        ask about it afterwards — so it says which signal stopped it on the way
        out, and exits as that signal. Which one arrived is the only thing that
        differs between the three paths, and it is the thing a person reading a
        log wants: a console that was hung up on is a different story from one
        somebody typed Ctrl-C at."""
        space = self.space()
        before = self.servers()
        proc, url = self.launch(space)
        self.addCleanup(self.reap, self.servers() - before)
        proc.send_signal(signal.SIGHUP)
        code = proc.wait(timeout=30)
        said = proc.stdout.read()
        self.assertEqual(code, 128 + int(signal.SIGHUP))
        self.assertIn("SIGHUP", said)
        self.assertNotIn("Traceback", said)
        self.assertEqual(self.servers() - before, set(),
                         "the server outlived the terminal it was hung up on")

    def test_a_console_killed_outright_still_lets_go_of_the_space(self):
        """SIGKILL is the one thing forwarding cannot reach: nothing runs after
        it, so the shim cannot pass it on and the server is never asked. It is
        also what a person reaches for when a console will not go — and what
        Activity Monitor sends. So the server watches the one fact that says it
        happened: the parent it was launched by is gone, and a console with no
        shim has no terminal to print to and no page to serve."""
        from lib import lock
        space = self.space()
        before = self.servers()
        proc, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                                space=space)
        started = self.servers() - before
        self.addCleanup(self.reap, started)
        self.ask(url, "/run", {"prompt": "check the build"})
        self.gate(url)
        self.assertIsNotNone(lock.holder(space), "the run did not hold the space")
        proc.kill()
        proc.wait(timeout=30)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and self.servers() & started:
            time.sleep(0.25)
        self.assertEqual(self.servers() & started, set(),
                         "the server outlived the console nobody could stop")
        self.assertIsNone(lock.holder(space), "the run kept the space it was holding")

    def test_the_cleanup_this_suite_runs_puts_back_what_it_launched(self):
        """The bill this issue came from. Every console test ends through
        `finish`, which terminates — the right thing for a harness to do — and
        one `unittest discover` left about fifty-seven servers behind, each with
        a port. A session that ran the suite a dozen times could not fork at all,
        and the suite failed with errors that accused the change in flight. So
        the harness is held to the same standard as the console: what it starts,
        it puts back."""
        before = self.servers()
        proc, _ = self.launch()
        self.assertEqual(len(self.servers() - before), 1, "no server started")
        self.finish(proc)
        self.assertEqual(self.servers() - before, set(),
                         "the suite's own cleanup leaves servers behind")

    def reap(self, pids):
        """Kill what the test proved should not be there, so one red does not
        cost the next run its ability to fork."""
        for pid in pids & self.servers():
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass


class RunTest(ConsoleCase):
    """The heart of ADR 0019: prose in, a driven agent, every call gated.

    The agent is scripted rather than real (`tests/agent_stand_in.py`), because
    what is being proved is the console's — the transcript, the gate, the wait,
    the lock. That the Claude Agent SDK drives the same seam is confirmed by
    hand, since the suite has to pass on a clone with nothing installed.
    """

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
        means (ADR 0019, decision 22)."""
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

    def test_a_hidden_tab_at_a_gate_never_ends_the_console(self):
        """Gone to the lobby, or to another app, while a gate waits: the
        console waits too, past every grace, because ending the run would
        decide the gate by silence (issue 39). Closing the tab still ends it."""
        proc, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                                CONTOUR_CONSOLE_GRACE="0.3",
                                CONTOUR_CONSOLE_HIDDEN_GRACE="1")
        self.ask(url, "/beat", {"hidden": True})
        self.ask(url, "/run", {"prompt": "check the build"})
        self.gate(url)
        time.sleep(4)                         # four hidden graces' worth
        self.assertIsNone(proc.poll(), "the console ended at a gate under a hidden tab")
        _, said = self.ask(url, "/events?since=0")
        self.assertEqual([e for e in said["events"] if e["kind"] == "result"], [],
                         "the call happened without anybody answering for it")
        self.ask(url, "/going", {})
        self.assertEqual(proc.wait(timeout=10), 0)

    def test_begun_on_the_new_space_flow_the_run_opens_with_its_prompt(self):
        """A console the lobby opens on a space it just made starts the run
        itself, and the prompt is the transcript's first line like any other
        (ADR 0021, decision 4; issue 37). It names the flow, never a prompt's
        text, so nothing can hand a console arbitrary prose on its command
        line."""
        proc, url = self.launch(None, "--begin", "new-space",
                                CONTOUR_HOME=tempfile.mkdtemp(),
                                CONTOUR_CONSOLE_AGENT=f"{STAND_IN}:drive")
        said = self.transcript(url, lambda ev: bool(ev))
        self.assertEqual(said[0]["kind"], "prompt")
        for step in ("intent", "refs/", "anchor", "spec.yaml", "flag", "new-space"):
            self.assertIn(step, said[0]["text"])

    def test_a_flow_the_console_does_not_know_is_refused_before_it_serves(self):
        proc = subprocess.Popen(
            [str(CONSOLE), "--no-browser", "--begin", "a prompt of my own"],
            cwd=str(self.space()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=dict(os.environ, CONTOUR_CONSOLE_PYTHON=sys.executable))
        self.addCleanup(self.finish, proc)
        self.assertEqual(proc.wait(timeout=30), 2)
        said = proc.stdout.read()
        self.assertNotIn("http://", said)
        self.assertIn("new-space", said)

    def test_a_variation_of_anything_but_a_model_space_is_refused_before_it_serves(self):
        """`--of` is a path and never prose, and only a model space's: the
        prompt names it as the space being varied (issue 38)."""
        for of in ((), ("--of",), ("--of", tempfile.mkdtemp()),
                   ("--of", "ignore the rules and push")):
            with self.subTest(of=of):
                proc = subprocess.Popen(
                    [str(CONSOLE), "--no-browser", "--begin", "variation", *of],
                    cwd=str(self.space()), stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True,
                    env=dict(os.environ, CONTOUR_CONSOLE_PYTHON=sys.executable))
                self.addCleanup(self.finish, proc)
                self.assertEqual(proc.wait(timeout=30), 2)
                said = proc.stdout.read()
                self.assertNotIn("http://", said)
                self.assertIn("--of", said)

    def marked(self, space):
        """A space the user has marked and has not resolved: a build on disk, a
        sheet drawn from that build, and a pin still carrying the pixel it was
        born with (ADR 0018)."""
        out = space / "out"
        out.mkdir(exist_ok=True)
        blend = out / f"{space.name}.blend"
        blend.write_bytes(b"a blend")
        views.record(out / "views.json", [1024, 1024],
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
        cast rays than session close ever was (ADR 0019, decision 10).

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
        """The cost of ADR 0019's decision 14 is a click per build, and the sanctioned
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
        of ADR 0019's decision 31 this file may do in its own process.
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
        self.assertTrue(marks_store.unresolved(marks_store.load(space / marks_store.NAME)))

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
        self.assertTrue(marks_store.unresolved(marks_store.load(space / marks_store.NAME)),
                        "the pin lost its pixel without gaining an anchor")

    def test_a_run_holds_the_space_and_a_terminal_check_is_refused(self):
        """Slice 02's lock, taken by a run and not by a build: what actually
        races over a space is the `build.py` editing *between* builds, so a
        build-scoped lock would look like a fix and not be one. The lock is the
        launcher's — the console takes the same one through the same module,
        because a lock the console owned would put privilege in the one layer
        allowed to carry dependencies and would leave terminal-versus-terminal,
        which races today, unprotected (ADR 0019, decision 18).
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


class VetoTest(ConsoleCase):
    """A denial outlives the run that produced it (ADR 0019, decisions 15, 27).

    The transcript already carries every verdict, and dies with the tab. A veto
    is the part of it that has to survive a clean checkout, because it is why two
    builds differ: *I stopped you widening that tolerance* is reasoning, and an
    untracked one takes the reasoning with it.
    """

    def vetoes(self, space):
        """The veto file as git and the page see it. Absent is not an error: a
        space where nothing was ever denied has nothing to keep."""
        path = space / "vetoes.json"
        return json.loads(path.read_text()) if path.exists() else []

    def built(self, space):
        """A space with a build on disk, so a veto has something to be against.
        A veto names the build it happened at, which is what lets a later reader
        line it up with the geometry the user was looking at."""
        out = space / "out"
        out.mkdir(exist_ok=True)
        blend = out / f"{space.name}.blend"
        blend.write_bytes(b"a blend")
        return blend

    def test_denying_at_a_gate_records_the_call_the_reason_and_the_build(self):
        """The four things a veto is: what was asked, why not, who said so, and
        which build they said it against. The reason is the user's own sentence
        and the author is the user, because only the user vetoes — exactly as
        only the user closes a mark (ADR 0018)."""
        space = self.space()
        blend = self.built(space)
        _, url = self.driven({"call": {"tool": "Bash", "command": "git commit -m wip"}},
                             space=space)
        self.ask(url, "/run", {"prompt": "tidy up"})
        gate, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": gate["id"], "allow": False,
                                   "reason": "not until the neck measures 280"})
        self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        got, = self.vetoes(space)
        self.assertEqual(got["reason"], "not until the neck measures 280")
        self.assertEqual(got["author"], "user")
        self.assertEqual(got["category"], "commit")
        self.assertEqual(got["tool"], "Bash")
        self.assertEqual(got["call"]["command"], "git commit -m wip")
        self.assertEqual(got["build"], views.fingerprint(blend))
        self.assertTrue(got["id"], "a veto with no id cannot be promoted later")

    def test_an_allowed_call_leaves_no_veto_behind(self):
        """A veto is a denial and nothing else. Recording approvals here would
        make the file a log of the run — which ADR 0019's decision 15 refused, because a log
        is read by nobody and a veto is read by whoever asks why two builds
        differ. The transcript already has the allow, and is where it belongs."""
        space = self.space()
        self.built(space)
        _, url = self.driven({"call": {"tool": "Bash", "command": "git commit -m wip"}},
                             space=space)
        self.ask(url, "/run", {"prompt": "tidy up"})
        gate, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": gate["id"], "allow": True})
        self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        self.assertEqual(self.vetoes(space), [])

    def test_ending_the_run_at_a_waiting_gate_writes_no_veto(self):
        """Ending a run denies whatever was waiting, and that is not a veto.

        A veto is authority exercised against one call, with a sentence its
        author wrote. Ending the run is a decision about the run: the call is
        refused as a consequence, by nobody who considered it. Recording it would
        put sentences in a tracked file that no user ever said — and the file is
        read by whoever asks why two builds differ.
        """
        space = self.space()
        self.built(space)
        _, url = self.driven({"call": {"tool": "Bash", "command": "git commit -m wip"}},
                             space=space)
        self.ask(url, "/run", {"prompt": "tidy up"})
        self.gate(url)
        self.ask(url, "/end", {})
        # The call really was refused — this is the absence of a record, not the
        # absence of the denial.
        said = self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        self.assertTrue([e for e in said if e["kind"] == "ended"])
        self.assertEqual(self.vetoes(space), [])

    def git(self, space, *args):
        """Git in this space, told who it is: a throwaway repository has no
        identity of its own and the suite must not borrow the user's."""
        done = subprocess.run(("git", "-c", "user.email=t@example.com",
                               "-c", "user.name=test", *args), cwd=str(space),
                              capture_output=True, text=True)
        return done.returncode, done.stdout

    def repo(self, space):
        """The space as it really is: its own git repository (ADR 0015), with the
        template's ignore rules in it, because what a space ignores is part of
        what tracking a file there means."""
        self.git(space, "init", "-q")
        space.joinpath(".gitignore").write_text(
            (ROOT / "templates" / "space" / "gitignore").read_text())
        self.git(space, "add", "-A")
        self.git(space, "commit", "-qm", "the space")
        return space

    def test_the_veto_file_is_tracked_and_a_second_veto_diffs_as_an_addition(self):
        """Tracked, and legible in a diff — the two halves of *it reaches git
        with the change it prevented*.

        A space gitignores `.contour/` whole but for its marker, so a veto kept
        there would vanish on a clean checkout and be the log ADR 0019's decision 15
        refused. And the diff matters because this file is read in one: a store
        that renumbered or reordered what was already on file would bury the
        sentence that was added in a rewrite of the ones that were not.
        """
        space = self.repo(self.space())
        self.built(space)
        _, url = self.driven({"call": {"tool": "Bash", "command": "git commit -m one"}},
                             {"call": {"tool": "Bash", "command": "git commit -m two"}},
                             space=space)
        self.ask(url, "/run", {"prompt": "tidy up"})
        first, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": first["id"], "allow": False,
                                   "reason": "measure the neck first"})
        self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        ignored, _ = self.git(space, "check-ignore", "-q", "vetoes.json")
        self.assertNotEqual(ignored, 0, "the space ignores its own vetoes")
        self.git(space, "add", "-A")
        self.git(space, "commit", "-qm", "the first veto")
        second = self.transcript(
            url, lambda ev: len([e for e in ev if e["kind"] == "gate"]) == 2)
        at = [e for e in second if e["kind"] == "gate"][1]
        self.ask(url, "/verdict", {"id": at["id"], "allow": False,
                                   "reason": "and the beak before that"})
        self.transcript(url, lambda ev: len([e for e in ev if e["kind"] == "result"]) == 2)
        _, diff = self.git(space, "diff", "--", "vetoes.json")
        added = [l for l in diff.splitlines() if l.startswith("+") and l[1:2] != "+"]
        gone = [l for l in diff.splitlines() if l.startswith("-") and l[1:2] != "-"]
        self.assertTrue(any("and the beak before that" in l for l in added), diff)
        self.assertEqual([l for l in gone if "measure the neck first" in l], [],
                         f"the veto already on file was rewritten:\n{diff}")

    def vetoed(self, space, call=None, reason="not until the neck measures 280"):
        """One veto on file, made the only way one can be: a gated call, denied
        from the page with a sentence. Returns the console's URL, because most
        of what is worth asking about a veto is asked while the console stands.
        """
        _, url = self.driven({"call": call or {"tool": "Bash",
                                               "command": "git commit -m wip"}},
                             space=space)
        self.ask(url, "/run", {"prompt": "tidy up"})
        gate, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": gate["id"], "allow": False,
                                   "reason": reason})
        self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        return url

    def test_a_veto_naming_a_part_is_promoted_to_a_sheet_mark(self):
        """Promotion is what turns a fact about a moment into an open question
        about the model (ADR 0019, decision 15).

        The mark it becomes names a part and no point on it — the shape an
        agent's `contour mark --part` already makes, which the render badges per
        view against the identity mask. So a promoted veto gains a position
        without any new placement machinery, and gains it on every view that can
        see the part. Authored by the user, because they wrote the sentence: a
        veto is theirs, and so is the question it turns into.
        """
        space = self.space()
        self.built(space)
        (space / "out" / "parts.json").write_text(json.dumps({"1": "cap"}))
        url = self.vetoed(space)
        _, got = self.ask(url, "/promote", {"id": "v1", "part": "cap"})
        self.assertEqual(got["part"], "cap")
        self.assertNotIn("anchor", got)
        self.assertEqual(got["text"], "not until the neck measures 280")
        self.assertEqual(got["author"], "user")
        self.assertEqual(got["status"], "open")
        self.assertEqual(got["from"], "v1")
        self.assertEqual([m["id"] for m in
                          marks_store.load(space / marks_store.NAME)], [got["id"]])
        # The veto stays. It was true when it happened and promotion does not
        # resolve it — what promotion adds is which mark it became.
        kept, = self.vetoes(space)
        self.assertEqual(kept["promoted"], got["id"])
        self.assertEqual(kept["reason"], "not until the neck measures 280")

    def refused(self, url, body):
        """A promotion the console will not make. 404 and not a 200 carrying a
        complaint, because the page's own rule is that a route answers with the
        thing or not at all."""
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.ask(url, "/promote", body)
        self.assertEqual(caught.exception.code, 404, body)
        caught.exception.close()

    def test_nothing_is_promoted_that_the_veto_or_the_build_cannot_carry(self):
        """Three ways a promotion is not one, and the same reason under each: the
        mark it would make would be a claim nobody can stand behind.

        A veto that is not on file has no sentence to carry. A part this build
        does not have would produce a mark the render can never badge, which is
        `contour mark`'s rule already and not a new one. And a second promotion
        would ask the same question twice on the same picture, from one moment
        that happened once.
        """
        space = self.space()
        self.built(space)
        (space / "out" / "parts.json").write_text(json.dumps({"1": "cap"}))
        url = self.vetoed(space)
        self.refused(url, {"id": "v9", "part": "cap"})
        self.refused(url, {"id": "v1", "part": "beak"})
        self.ask(url, "/promote", {"id": "v1", "part": "cap"})
        self.refused(url, {"id": "v1", "part": "cap"})
        self.assertEqual(len(marks_store.load(space / marks_store.NAME)), 1,
                         "a refused promotion still wrote a mark")

    def test_pruning_the_marks_leaves_the_vetoes_untouched(self):
        """The reason a veto is not a second collection inside `marks.json`.

        ADR 0018 prunes closed marks the last release tag already holds, because
        a mark gets resolved and closed and git is the archive. A veto is never
        resolved, so the same rule applied to one would delete the only record
        that something was prevented. Two opposite retention rules in one file
        means the pruner has to tell them apart — and in separate files it cannot
        get it wrong, which is what this asserts: the pruner really ran, and the
        veto file was not even opened.
        """
        space = self.repo(self.space())
        self.built(space)
        self.vetoed(space)
        path = space / marks_store.NAME
        marks_store.append(path, {"view": "front", "pixel": [1, 1],
                                  "text": "the beak is blunt"})
        marks_store.close(path, "m1")
        self.git(space, "add", "-A")
        self.git(space, "commit", "-qm", "a release")
        self.git(space, "tag", "v1")
        before = (space / "vetoes.json").read_bytes()
        self.launch(space)                    # pruning happens as the page opens
        self.assertEqual(marks_store.load(path), [],
                         "the pruner did not run, so this proves nothing")
        self.assertEqual((space / "vetoes.json").read_bytes(), before)

    def test_the_page_is_told_how_many_vetoes_are_uncommitted(self):
        """Tracked is not committed, and an uncommitted veto dies exactly as an
        ignored one would (ADR 0019, decision 33).

        So the console's contribution is visibility and nothing else: it does not
        commit, and it does not propose a records-only commit at run end, because
        a veto-only commit describes no model state. The count is of vetoes `HEAD`
        does not hold — not of whether the file is dirty — so the ordinary case,
        where earlier vetoes already shipped and this one has not, reads true.
        """
        space = self.repo(self.space())
        self.built(space)
        _, url = self.driven({"call": {"tool": "Bash", "command": "git commit -m one"}},
                             {"call": {"tool": "Bash", "command": "git commit -m two"}},
                             space=space)
        self.ask(url, "/run", {"prompt": "tidy up"})
        first, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": first["id"], "allow": False,
                                   "reason": "measure the neck first"})
        self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        _, said = self.ask(url, "/vetoes")
        self.assertEqual(said["uncommitted"], 1)
        self.assertEqual([v["id"] for v in said["vetoes"]], ["v1"])
        self.git(space, "add", "-A")
        self.git(space, "commit", "-qm", "the neck, and what it did not become")
        _, said = self.ask(url, "/vetoes")
        self.assertEqual(said["uncommitted"], 0)
        self.assertEqual([v["id"] for v in said["vetoes"]], ["v1"],
                         "a committed veto left the file")
        # And the next one is exposure again — one, not two: what is counted is
        # the vetoes git does not hold, not whether the file has been touched.
        second = self.transcript(
            url, lambda ev: len([e for e in ev if e["kind"] == "gate"]) == 2)
        at = [e for e in second if e["kind"] == "gate"][1]
        self.ask(url, "/verdict", {"id": at["id"], "allow": False,
                                   "reason": "and the beak before that"})
        self.transcript(url, lambda ev: len([e for e in ev if e["kind"] == "result"]) == 2)
        self.assertEqual(self.ask(url, "/vetoes")[1]["uncommitted"], 1)

    def test_the_veto_surface_is_declared_against_the_host_that_gates(self):
        """One page, two hosts (ADR 0019, decision 23). Only a console gates, so
        only a console has vetoes — and the page carries the affordance anyway,
        removed under the launcher by the same rule that removes the transcript.

        Checked in the markup because that is where the declaration is: an
        affordance that mentions vetoes outside the section declaring `drive`
        would be on screen in a bare clone, offering to promote records that host
        cannot have. `/can` makes `drive` a name the console really answers.
        """
        page = (ROOT / "lib" / "canvas.html").read_text()
        found = re.search(r'<section id="vetoes"([^>]*)>(.*?)</section>', page,
                          re.S)
        self.assertIsNotNone(found, "the page has no veto surface")
        self.assertIn('data-needs="drive"', found.group(1))
        outside = page[:found.start()] + page[found.end():]
        # What the user can see and reach: the script wires the section, the
        # stylesheet paints it and a comment explains it, and none of the three
        # is an affordance. What must not be out here is markup.
        markup = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "",
                        outside, flags=re.S)
        self.assertNotIn("veto", markup.lower(),
                         "a veto affordance sits outside the section that "
                         "declares the capability it needs")

    def named(self, path):
        """Every call in this file, as the literal words it passes.

        Walked whole rather than read off a command list: the console's git goes
        through a helper, so the words that matter are arguments to *that* and a
        check watching `subprocess.run` for a literal list sees nothing at all.
        Read rather than run, because what is being asked is what this layer is
        *able* to do — a test that waited to catch a commit happening would only
        catch the one a test thought to provoke.
        """
        found = []
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call):
                continue
            found.append((ast.unparse(node.func),
                          [n.value for n in ast.walk(node)
                           if isinstance(n, ast.Constant)
                           and isinstance(n.value, str)]))
        return found

    def test_the_console_can_read_git_and_cannot_write_it(self):
        """Rule 5, flat: the console gets no privilege a terminal would not get,
        including over its own records (ADR 0019, decisions 18 and 33).

        It has a live reason to run git — the exposure count asks `HEAD` what it
        holds — and that is exactly where a commit would be easiest to slip in.
        So a word that would change a repository is a finding wherever it is
        passed: a veto reaches git with the change it prevented, by the user's
        hand and in the commit where the tolerance did not get widened.
        """
        writes = {"commit", "add", "push", "checkout", "restore", "reset",
                  "merge", "rebase", "stash", "tag", "rm", "apply", "mv"}
        for f in sorted((ROOT / "console").glob("*.py")):
            for func, words in self.named(f):
                self.assertEqual(sorted(set(words) & writes), [],
                                 f"{f.name} passes a git write to {func}")

    def test_the_run_ends_without_offering_to_commit_the_records(self):
        """Not even a suggestion at run end. `docs/CONTEXT.md` records that
        version control bought *a commit fully describes a model*, and a
        veto-only commit describes no model state — it would have to be skipped
        past by anyone reading history to understand how the model got here.
        """
        space = self.repo(self.space())
        self.built(space)
        url = self.vetoed(space)
        self.ask(url, "/end", {})
        said = self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        for event in said:
            self.assertNotIn("commit", (event.get("text") or "").lower(), event)
        # and the exposure is still just a number, which is the whole offer
        self.assertEqual(self.ask(url, "/vetoes")[1]["uncommitted"], 1)


class SeedTest(ConsoleCase):
    """Marks seed a run (ADR 0019, decision 21).

    A mark is the one place the user's intent is already located, authored and
    tracked, so a run started from marks starts from something better than a
    re-typed paragraph. And because the console knows which marks were in scope,
    a mark the run never touched is visible at the end instead of silently
    dropped — which is what makes `addressed` checkable without making it a
    close.
    """

    def pinned(self, space, *lines):
        """A space with marks on it, in the order given. Returns their ids."""
        path = space / marks_store.NAME
        return [marks_store.append(path, dict(line))["id"] for line in lines]

    def test_a_run_seeded_from_a_mark_starts_from_what_the_mark_says(self):
        """The slice's demo: select an open mark, and the prompt is composed from
        it. The id is in there too — the agent is going to be asked whether it
        addressed `m1`, so `m1` has to be a name it was given."""
        space = self.space()
        self.pinned(space,
                    {"view": "front", "part": "neck", "text": "the neck is short"},
                    {"view": "side", "part": "beak", "text": "the beak droops"})
        _, url = self.driven({"say": "looking at the neck"}, space=space)
        status, _ = self.ask(url, "/run", {"prompt": "fix these",
                                           "marks": ["m1"]})
        self.assertEqual(status, 200)
        said = self.transcript(url, lambda ev: any(e["kind"] == "text" for e in ev))
        first = said[0]
        self.assertEqual(first["kind"], "prompt")
        self.assertIn("fix these", first["text"])
        self.assertIn("m1", first["text"])
        self.assertIn("the neck is short", first["text"])
        # Selected, not all: a page that sent every open mark would make the
        # checkbox a decoration.
        self.assertNotIn("the beak droops", first["text"])

    def test_a_run_with_nothing_selected_starts_from_the_prose_alone(self):
        """The base case, and it stays the base case. The page sends the
        selection every time, so an empty one is the common shape — and prose is
        what a run is *for*: a measurement is not a mark and not a build loop
        (ADR 0019, decision 21)."""
        space = self.space()
        self.pinned(space, {"view": "front", "text": "the neck is short"})
        _, url = self.driven({"say": "measuring"}, space=space)
        self.ask(url, "/run", {"prompt": "why is the neck 269", "marks": []})
        said = self.transcript(url, lambda ev: any(e["kind"] == "text" for e in ev))
        # Byte for byte: a preamble nobody asked for is a prompt the user did
        # not write, and the transcript would be showing them somebody else's.
        self.assertEqual(said[0], {"n": 0, "kind": "prompt",
                                   "text": "why is the neck 269"})

    def test_a_seeded_mark_says_where_it_is_and_not_only_what_it_says(self):
        """A mark is a *located* comment, and the location is half of what it
        means: *too thin* about the neck and *too thin* about the beak are two
        findings. The part is read from the anchor when a ray has already landed
        and from the mark when one has not, because a resolved mark drops its
        pixel and keeps its answer (ADR 0018)."""
        space = self.space()
        self.pinned(space,
                    {"view": "front", "part": "neck", "pixel": [10, 10],
                     "text": "the neck is short"},
                    {"view": "side", "anchor": {"part": "beak", "local": [0, 0, 0]},
                     "text": "the beak droops"})
        _, url = self.driven({"say": "looking"}, space=space)
        self.ask(url, "/run", {"prompt": "fix these", "marks": ["m1", "m2"]})
        said = self.transcript(url, lambda ev: any(e["kind"] == "text" for e in ev))
        text = said[0]["text"]
        self.assertRegex(text, r"m1\b.*\bfront\b.*\bneck\b")
        self.assertRegex(text, r"m2\b.*\bside\b.*\bbeak\b")

    def test_a_mark_on_a_photograph_seeds_a_run_as_well_as_one_on_the_sheet(self):
        """A ref mark is a finding about the model too — *the real beak is
        shorter than this* — and it is the kind most likely to start a run. It
        names the photograph, because it has no part to name: a reference knows
        nothing about our parts and was drawn by none of our views (ADR 0018)."""
        space = self.space()
        self.pinned(space, {"ref": "side.png", "pixel": [40, 40],
                            "text": "the real beak is shorter than this"})
        _, url = self.driven({"say": "opening the reference"}, space=space)
        self.ask(url, "/run", {"prompt": "measure it", "marks": ["m1"]})
        said = self.transcript(url, lambda ev: any(e["kind"] == "text" for e in ev))
        text = said[0]["text"]
        self.assertRegex(text, r"m1\b.*\bside\.png\b")
        self.assertIn("the real beak is shorter than this", text)
        # And not as a view of ours, which would send the agent to a render that
        # does not exist. `()` empty would say the console had nowhere to put it.
        self.assertNotRegex(text, r"m1 \(\)")

    def test_a_seed_the_store_cannot_honour_is_dropped_and_the_drop_is_named(self):
        """Closed in another tab, or pruned, or never there. The run still starts
        — a mark closed between selecting and clicking should not block work the
        user meant — but the shortening is said out loud, because a seed list
        silently one shorter is exactly the dropped finding this slice exists to
        make visible."""
        space = self.space()
        self.pinned(space,
                    {"view": "front", "part": "neck", "text": "the neck is short"},
                    {"view": "side", "part": "beak", "text": "the beak droops"})
        marks_store.close(space / marks_store.NAME, "m1")
        _, url = self.driven({"say": "looking at the beak"}, space=space)
        self.ask(url, "/run", {"prompt": "fix these",
                               "marks": ["m1", "m2", "m9"]})
        said = self.transcript(url, lambda ev: any(e["kind"] == "text" for e in ev))
        text = said[0]["text"]
        self.assertIn("the beak droops", text)
        self.assertNotIn("the neck is short", text)
        dropped = [ln for ln in text.splitlines() if "not seeded" in ln.lower()]
        self.assertEqual(len(dropped), 1, text)
        self.assertIn("m1", dropped[0])
        self.assertIn("m9", dropped[0])

    def ended(self, url):
        """The transcript once the run is over, and the report in it."""
        said = self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        report = [e for e in said if e["kind"] == "seeds"]
        self.assertEqual(len(report), 1, said)
        return report[0], said

    def test_at_run_end_every_seeded_mark_left_unaddressed_is_named(self):
        """The whole reason seeding is worth building: the console knows what was
        in scope, so a finding the run walked past is visible instead of silently
        dropped. It is a report and nothing more — nothing here closes, dims or
        edits a mark (ADR 0019, decision 21)."""
        space = self.space()
        self.pinned(space,
                    {"view": "front", "part": "neck", "text": "the neck is short"},
                    {"view": "side", "part": "beak", "text": "the beak droops"})
        _, url = self.driven({"say": "I looked at neither"}, space=space)
        self.ask(url, "/run", {"prompt": "fix these", "marks": ["m1", "m2"]})
        report, said = self.ended(url)
        self.assertRegex(report["text"], r"(?s)m1.*unaddressed")
        self.assertRegex(report["text"], r"(?s)m2.*unaddressed")
        # Before the run is declared over: the last line of a conversation is
        # *ended*, and a report after it reads as something that came in later.
        kinds = [e["kind"] for e in said]
        self.assertLess(kinds.index("seeds"), kinds.index("ended"))

    def built(self, space):
        """A build on disk, so `addressed` has a build to name: the stamp is a
        fingerprint of the `.blend` and an empty one would say *no build*."""
        out = space / "out"
        out.mkdir(exist_ok=True)
        blend = out / f"{space.name}.blend"
        blend.write_bytes(b"a blend")
        return views.fingerprint(blend)

    def test_a_mark_the_run_addressed_reads_addressed_and_stays_open(self):
        """`addressed` is a claim, not a disposal. The agent attaches it and the
        badge dims; the finding is still outstanding until the user says
        otherwise, because a finding is not disposed of by the party it is aimed
        at (ADR 0018)."""
        space = self.space()
        build = self.built(space)
        self.pinned(space, {"view": "front", "part": "neck",
                            "text": "the neck is short"})
        _, url = self.driven({"mark": ["--addressed", "m1"]},
                             {"say": "lengthened the neck"}, space=space)
        self.ask(url, "/run", {"prompt": "fix it", "marks": ["m1"]})
        report, _ = self.ended(url)
        self.assertIn(f"addressed in build {build}", report["text"])
        self.assertNotIn("unaddressed", report["text"])
        stored, = json.loads((space / marks_store.NAME).read_text())
        self.assertEqual(stored["status"], "open")
        self.assertEqual(stored["addressed"], build)

    def test_a_stamp_from_an_earlier_build_does_not_count_as_this_runs_work(self):
        """*Addressed* here means addressed by **this** run. A mark the agent
        claimed two builds ago, seeded again and walked past, would otherwise
        report itself dealt with — the check passing exactly when there is nothing
        behind it, which is worse than not checking."""
        space = self.space()
        self.pinned(space, {"view": "front", "part": "neck", "addressed": "0ldbu1ld",
                            "text": "the neck is still short"})
        _, url = self.driven({"say": "I did nothing about it"}, space=space)
        self.ask(url, "/run", {"prompt": "have another look", "marks": ["m1"]})
        report, _ = self.ended(url)
        self.assertIn("unaddressed", report["text"])
        self.assertNotIn("0ldbu1ld", report["text"])

    def test_a_seeded_mark_whose_part_the_run_deleted_reads_orphaned(self):
        """Deleting a part does not answer the question that was asked about it.
        The pin is homeless, so the report says so rather than accepting the
        agent's claim over the top of it — an *addressed* on a mark with nowhere
        left to point is a finding that looks dealt with and cannot be checked
        (ADR 0018)."""
        space = self.space()
        self.built(space)
        self.pinned(space, {"view": "front", "anchor": {"part": "neck",
                                                        "local": [0, 0, 0]},
                            "text": "the neck is short"})
        _, url = self.driven({"mark": ["--addressed", "m1"]},
                             {"rebuilt": ["torso", "beak"]},
                             {"say": "replaced the neck with a torso taper"},
                             space=space)
        self.ask(url, "/run", {"prompt": "fix it", "marks": ["m1"]})
        report, _ = self.ended(url)
        self.assertIn("orphaned", report["text"])
        self.assertNotIn("addressed in build", report["text"])

    def test_ending_the_run_early_still_says_what_became_of_the_seeds(self):
        """The ending a seeded run is most likely to get: the user has seen enough
        at a gate and stops it. That is exactly when the scope report matters — the
        run is over with work outstanding — so it cannot be the ending that skips
        it (ADR 0019, decision 21)."""
        space = self.space()
        self.pinned(space, {"view": "front", "part": "neck",
                            "text": "the neck is short"})
        _, url = self.driven({"call": {"tool": "Bash", "command": "./contour check"}},
                             space=space)
        self.ask(url, "/run", {"prompt": "fix it", "marks": ["m1"]})
        self.gate(url)
        self.ask(url, "/end", {})
        report, said = self.ended(url)
        self.assertIn("unaddressed", report["text"])
        kinds = [e["kind"] for e in said]
        self.assertLess(kinds.index("seeds"), kinds.index("ended"))

    def test_a_whole_seeded_run_leaves_every_marks_status_alone(self):
        """Only the user closes a mark, and seeding does not make the console a
        party to that. The run knows the scope, addresses one, walks past the
        other and ends — and the store comes out of it with two open findings and
        one claim (ADR 0018, ADR 0019, decision 21)."""
        space = self.space()
        build = self.built(space)
        self.pinned(space,
                    {"view": "front", "part": "neck", "text": "the neck is short"},
                    {"view": "side", "part": "beak", "text": "the beak droops"})
        before = json.loads((space / marks_store.NAME).read_text())
        _, url = self.driven({"mark": ["--addressed", "m1"]},
                             {"say": "the beak will have to wait"}, space=space)
        self.ask(url, "/run", {"prompt": "fix these", "marks": ["m1", "m2"]})
        self.ended(url)
        after = json.loads((space / marks_store.NAME).read_text())
        self.assertEqual([m["status"] for m in after], ["open", "open"])
        # One claim, and otherwise the same two findings: the report read the
        # store and wrote nothing back to it.
        self.assertEqual([{**m, "addressed": build} if m["id"] == "m1" else m
                          for m in before], after)

    def test_the_console_names_no_way_to_close_a_mark(self):
        """Read rather than provoked. `marks.close` is one import away from every
        file in `console/`, and the console is the layer with a live reason to
        reach for it — it knows which marks a run was about and when the run
        stopped being about them. So the ban is on the vocabulary: a `close` on
        the mark store, or the word `closed` a status write would need.

        The structural half of this is elsewhere and stronger: `contour mark` has
        no `--close`, so the agent cannot close one either (ADR 0018).
        """
        store = ("marks", "marks_store", "store", "seed", "vetoes", "veto_store")
        for f in sorted((ROOT / "console").glob("*.py")):
            tree = ast.parse(f.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = ast.unparse(node.func)
                    self.assertFalse(
                        func.endswith(".close") and func.split(".")[0] in store,
                        f"{f.name} calls {func}")
                if isinstance(node, ast.Constant) and node.value == "closed":
                    self.fail(f"{f.name} spells out a closed status")

    def test_the_seeding_surface_is_declared_against_the_host_that_runs(self):
        """One page, two hosts (ADR 0019, decision 23). Only a console runs an
        agent, so only a console can seed one — and the page carries the
        affordance anyway, removed under the launcher by the same rule that
        removes the transcript.

        Checked in the markup, where the declaration is: a selection offered by
        `contour canvas` would be a promise to start something that host cannot
        start, and `/can` makes `drive` a name the console really answers.
        """
        page = (ROOT / "lib" / "canvas.html").read_text()
        markup = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "",
                        page, flags=re.S)
        for found in re.finditer(r"<[^>]*\bseed[^>]*>", markup, re.I):
            self.assertIn('data-needs="drive"', found.group(0),
                          "a seeding affordance does not declare the host it "
                          f"needs: {found.group(0)}")
        self.assertRegex(markup, r'<[^>]*id="seeds"[^>]*data-needs="drive"',
                         "the page offers no way to see what a run is seeded with")

    def test_a_selection_on_its_own_is_enough_to_start_a_run(self):
        """A mark is already a sentence about the model, written where it applies.
        Making the user restate it in prose to be allowed to start would ask them
        to type the thing they pointed at — and *these two* is a complete request
        (ADR 0019, decision 21)."""
        space = self.space()
        self.pinned(space, {"view": "front", "part": "neck",
                            "text": "the neck is short"})
        _, url = self.driven({"say": "on it"}, space=space)
        status, said = self.ask(url, "/run", {"prompt": "", "marks": ["m1"]})
        self.assertEqual((status, said["started"]), (200, True))
        first = self.transcript(url,
                                lambda ev: any(e["kind"] == "text" for e in ev))[0]
        self.assertIn("the neck is short", first["text"])
        # No empty last turn where the prose would have been: the transcript is a
        # conversation, and a blank line in it reads as something not yet said.
        self.assertEqual(first["text"], first["text"].strip())


class SpendTest(ConsoleCase):
    """What a run costs, while it happens (ADR 0019, decision 37).

    Token cost is the second of the three stated priorities, and the tool that
    serves it reads a transcript a console run does not produce. So the console
    records what it knows — per turn, cache reads included, which is strictly
    better than anything a transcript could be parsed for — and the page shows
    the same figures live, because a gate that fires often costs a turn of
    re-explanation and *tune the ask-list downward* should be a number rather
    than an irritation.
    """

    def lines(self, space):
        """Every spend line the space holds, oldest first, as JSON."""
        path = space / ".contour" / spend.NAME
        if not path.exists():
            return []
        return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

    def test_a_turn_records_what_it_spent_where_the_accounting_reads(self):
        """The tracer bullet: a run's turn appends one line naming the run and
        what that turn cost. On disk and in the space, because the transcript
        dies with the tab and the accounting outlives the session."""
        space = self.space()
        _, url = self.driven(
            {"say": "thinking about it",
             "usage": {"input_tokens": 120, "output_tokens": 40}},
            space=space)
        self.ask(url, "/run", {"prompt": "why is the neck 269"})
        self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        lines = self.lines(space)
        self.assertEqual(len(lines), 1, f"one turn, {len(lines)} lines: {lines!r}")
        self.assertEqual(lines[0]["input"], 120)
        self.assertEqual(lines[0]["output"], 40)
        # Which run it was. Two runs from one console are two things that cost
        # money, and a file that could not tell them apart would report one.
        self.assertTrue(lines[0]["run"], f"no run named: {lines[0]!r}")

    def test_the_page_is_told_the_running_total_after_every_turn(self):
        """Live means per turn, not at the end: the display's second job is to
        make a gate's cost visible while the user is still deciding how many
        gates they want, and a figure that arrives once the run is over informs
        nothing they can still act on."""
        space = self.space()
        _, url = self.driven({"usage": {"input_tokens": 100, "output_tokens": 10}},
                             {"say": "still going"},
                             {"usage": {"input_tokens": 300, "output_tokens": 20}},
                             space=space)
        self.ask(url, "/run", {"prompt": "why is the neck 269"})
        said = self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        totals = [e for e in said if e["kind"] == "spend"]
        self.assertEqual(len(totals), 2, f"two turns, {len(totals)} figures")
        # Running, not per turn: what the user wants off the page is what this
        # run has cost so far, and a page doing the addition would be a second
        # place the arithmetic lives.
        self.assertEqual([t["input"] for t in totals], [100, 400])
        self.assertEqual([t["output"] for t in totals], [10, 30])
        self.assertEqual([t["turns"] for t in totals], [1, 2])

    def test_a_cached_turn_is_not_reported_as_a_fresh_one(self):
        """The figure the transcript could never give: a gated run re-sends its
        whole context every turn and almost all of it is a cache read, at a tenth
        the price. Folded into fresh input, a long run would read as ten times
        what it cost — and a number that wrong is worse than none (ADR 0019,
        decision 37)."""
        space = self.space()
        _, url = self.driven(
            {"usage": {"input_tokens": 200,
                       "cache_read_input_tokens": 40_000,
                       "cache_creation_input_tokens": 1_000,
                       "output_tokens": 300}},
            space=space)
        self.ask(url, "/run", {"prompt": "why is the neck 269"})
        said = self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        figure = [e for e in said if e["kind"] == "spend"][-1]
        self.assertEqual(figure["cache_read"], 40_000)
        self.assertEqual(figure["cache_write"], 1_000)
        self.assertEqual(figure["input"], 200)
        # One weighted number, in the units `tools/tokens.py` already defines, so
        # the page and the tool do not each invent an idea of what a turn cost:
        # 200 + 0.10*40000 + 1.25*1000 + 5*300 = 6950.
        self.assertEqual(figure["weighted"], 6950)
        self.assertEqual(self.lines(space)[0]["cache_read"], 40_000)

    def test_a_turn_records_how_many_gates_the_run_had_answered_before_it(self):
        """What makes the ask-list tunable with a number. A gate costs a turn of
        re-explanation, and a turn that followed one is only identifiable if the
        line says so — the file has no other way to know a verdict happened
        between two turns (ADR 0019, decisions 36 and 37)."""
        space = self.space()
        _, url = self.driven(
            {"usage": {"input_tokens": 100, "output_tokens": 10}},
            {"call": {"command": "git commit -m done"}},
            {"usage": {"input_tokens": 900, "output_tokens": 20}},
            space=space)
        self.ask(url, "/run", {"prompt": "commit it"})
        waiting, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": waiting["id"], "allow": True})
        self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        lines = self.lines(space)
        self.assertEqual([t["gates"] for t in lines], [0, 1],
                         f"gates not counted per turn: {lines!r}")

    def test_a_recorded_turn_names_what_the_run_was_asked_to_do(self):
        """A run id is not an answer to *what did that cost me*. The accounting's
        table is read by a person deciding where their tokens went, and a row
        labelled `a3f1c0` sends them back to a transcript that no longer exists —
        so the line carries the prompt the run started from."""
        space = self.space()
        _, url = self.driven({"usage": {"input_tokens": 100, "output_tokens": 10}},
                             space=space)
        self.ask(url, "/run", {"prompt": "why is the neck 269"})
        self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        self.assertEqual(self.lines(space)[0]["prompt"], "why is the neck 269")

    def test_a_run_that_spends_enormously_is_not_ended_for_it(self):
        """Rejected on the idle timeout's symmetry: silence is not a verdict, and
        neither is a threshold set before the user knew what the run involved. The
        console does not decide for the user in either direction, and with an
        attended run the stop is the user (ADR 0019, decisions 17 and 37)."""
        space = self.space()
        _, url = self.driven(
            {"usage": {"input_tokens": 9_000_000, "output_tokens": 2_000_000}},
            {"usage": {"input_tokens": 9_000_000, "output_tokens": 2_000_000}},
            {"say": "still working, because nobody stopped me"},
            space=space)
        self.ask(url, "/run", {"prompt": "spend it all"})
        said = self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        ended = [e for e in said if e["kind"] == "ended"]
        self.assertEqual([e["text"] for e in ended], ["the agent stopped"])
        self.assertIn("still working, because nobody stopped me",
                      [e.get("text") for e in said])

    def test_the_spend_recorder_has_no_way_to_end_a_run(self):
        """Structure, not vigilance. The module that knows what a run has cost is
        the one that would be asked to act on it, so it is the one that must not
        be able to: nothing there ends, stops or denies anything (ADR 0019,
        decision 37)."""
        tree = ast.parse((ROOT / "console" / "spend.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                named = ast.unparse(node.func).split(".")[-1]
                self.assertNotIn(named, ("end", "stop", "finish", "deny", "exit"),
                                 f"spend.py calls {ast.unparse(node.func)}")
        # And no figure to compare a run against. A budget is a number before it
        # is a mechanism, and the number is where it would arrive.
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                self.assertNotRegex(
                    node.id, r"(?i)(budget|max_|_max|limit|cap|threshold)",
                    f"spend.py names a figure a run could be judged against: "
                    f"{node.id}")

    def test_two_runs_from_one_console_are_two_things_that_cost_money(self):
        """A console is long-lived and a run is meant to be short — ending one at
        a gate and starting again is the move that keeps a run from reaching
        compaction (ADR 0019, decision 37). So the common shape is several runs in
        one sitting, and an accounting that added them together would report one
        expensive run where there were three cheap ones."""
        space = self.space()
        _, url = self.driven({"usage": {"input_tokens": 100, "output_tokens": 10}},
                             space=space)
        for prompt in ("why is the neck 269", "now the beak"):
            self.ask(url, "/run", {"prompt": prompt})
            self.transcript(
                url, lambda ev, p=prompt: any(
                    e["kind"] == "ended" for e in ev if e["n"] > [
                        i["n"] for i in ev if i["kind"] == "prompt"
                        and i["text"] == p][0]))
        lines = self.lines(space)
        self.assertEqual([l["prompt"] for l in lines],
                         ["why is the neck 269", "now the beak"])
        self.assertEqual(len({l["run"] for l in lines}), 2,
                         f"two runs, one id: {lines!r}")
        # And the running total starts again: the figure on the page is what this
        # run has cost, not what the tab has cost since it was opened.
        _, said = self.ask(url, "/events?since=0")
        totals = [e for e in said["events"] if e["kind"] == "spend"]
        self.assertEqual([t["input"] for t in totals], [100, 100])

    def test_the_spend_surface_is_declared_against_the_host_that_drives(self):
        """One page, two hosts. Spend belongs to a run, and the launcher has no
        run — a cost line under `contour canvas` would be a figure about nothing
        (ADR 0019, decision 23)."""
        page = (ROOT / "lib" / "canvas.html").read_text()
        markup = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "",
                        page, flags=re.S)
        for found in re.finditer(r"<[^>]*\bspend[^>]*>", markup, re.I):
            self.assertIn('data-needs="drive"', found.group(0),
                          "a spend affordance does not declare the host it "
                          f"needs: {found.group(0)}")
        self.assertRegex(markup, r'<[^>]*id="spend"[^>]*data-needs="drive"',
                         "the page offers nowhere to see what a run is costing")

    def test_nothing_offers_a_cost_before_the_first_turn_lands(self):
        """A pre-run estimate was rejected outright: it cannot be known, and a
        wrong one is worse than none (ADR 0019, decision 37). So the line is empty
        until a turn has actually been spent — what is shown is measurement, never
        prediction."""
        space = self.space()
        _, url = self.driven({"say": "thinking"}, space=space)
        # Before any run at all.
        _, said = self.ask(url, "/events?since=0")
        self.assertEqual([e for e in said["events"] if e["kind"] == "spend"], [])
        self.ask(url, "/run", {"prompt": "why is the neck 269"})
        # And after a run that spent nothing the console was told about: a figure
        # invented where no turn reported one would be an estimate by another name.
        said = self.transcript(url, lambda ev: any(e["kind"] == "ended" for e in ev))
        self.assertEqual([e for e in said if e["kind"] == "spend"], [])
        self.assertEqual(self.lines(space), [])
