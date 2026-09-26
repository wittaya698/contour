"""`contour-console`: the executable above the launcher, and its lifetime.

ADR 0019, decisions 4, 11, 33. The console is the one layer allowed
dependencies, so the first thing it has to do well is not have them: every test
here runs it as a subprocess the way a person would type it, and the ones that
need it to actually serve point `$CONTOUR_CONSOLE_PYTHON` at this interpreter —
honest in slice 06, where the console needs nothing but the standard library and
the environment requirement is structural.
"""
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

CONSOLE = ROOT / "contour-console"


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

class ServesTest(unittest.TestCase):
    """The slice's demo: run it in a space and the sheet is in a browser.

    Launched as a subprocess the way a person launches it, because what is being
    proved includes the handover from the stdlib shim to the half that may have
    dependencies. `$CONTOUR_CONSOLE_PYTHON` stands in for the environment.
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

    def beat(self, url):
        """One heartbeat, exactly as the page sends it: a header-carried token,
        which is what makes the request one another site cannot forge."""
        origin, token = url.split("/?")[0], url.split("t=")[1]
        req = urllib.request.Request(
            origin + "/beat", data=b"{}", method="POST",
            headers={"Content-Type": "application/json",
                     "X-Contour-Token": token})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status

    def test_the_console_exits_when_the_page_stops_beating(self):
        """Closing the last tab exits the process. A closed tab and a quiet one
        differ only in how long you wait, so the page beats and the console ends
        when the beats stop — there is no onbeforeunload that can be trusted to
        arrive."""
        proc, url = self.launch(CONTOUR_CONSOLE_GRACE="1")
        self.assertEqual(self.beat(url), 200)
        self.assertEqual(proc.wait(timeout=30), 0)

    def test_a_space_with_no_sheet_says_what_to_run(self):
        """The console's page is the sheet; a space that has never been rendered
        has none. Refused the way `contour canvas` refuses it, because a page
        whose only panel is a broken image is a worse answer than a sentence."""
        bare = self.space()
        (bare / "sheet.png").unlink()
        r = subprocess.run([str(CONSOLE), "--no-browser"], cwd=str(bare),
                           capture_output=True, text=True, timeout=60,
                           env=dict(os.environ,
                                    CONTOUR_CONSOLE_PYTHON=sys.executable))
        said = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("contour render", said)
        self.assertNotIn("Traceback", said)

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


if __name__ == "__main__":
    unittest.main()
