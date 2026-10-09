"""Presence: a page serving a space says so, and stops nothing (ADR 0021,
decision 8; issue 30).

Run as the user runs it — `contour canvas` and `contour-console` spawned in a
space `contour init` made, and asked about by `contour spaces --json`, the one
reader presence has.
"""
import json
import socket
import os
import re
import signal
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTOUR = ROOT / "contour"
sys.path.insert(0, str(ROOT))

from lib import presence                  # noqa: E402
from test_console import ConsoleCase      # noqa: E402
from executables import executable  # noqa: E402


class CanvasPresenceTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.spaces = self.tmp / "spaces"
        self.spaces.mkdir()
        quiet = executable(self.tmp / "no-browser",   # $BROWSER, so none opens
                           "#!/bin/sh\nexit 0\n")
        self.env = dict(os.environ, CONTOUR_SPACES=str(self.spaces),
                        CONTOUR_HOME=str(self.tmp / "home"),
                        BROWSER=str(quiet))
        r = self.contour("init", "alpha", cwd=self.spaces)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.space = self.spaces / "alpha"
        (self.space / "sheet.png").write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")

    def contour(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(CONTOUR), *args],
                              cwd=str(cwd or self.tmp), env=self.env,
                              capture_output=True, text=True, timeout=60)

    def presence(self):
        """What `contour spaces --json` says is open on the space."""
        said = json.loads(self.contour("spaces", "--json").stdout)
        return [{k: p[k] for k in ("kind", "pid")}
                for p in said["spaces"][0]["presence"]]

    def canvas(self):
        """`contour canvas` running in the space, and the URL it printed."""
        proc = subprocess.Popen([sys.executable, str(CONTOUR), "canvas"],
                                cwd=str(self.space), env=self.env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True)
        self.addCleanup(proc.stdout.close)
        self.addCleanup(proc.kill)
        url = re.search(r"http://\S+", proc.stdout.readline()).group(0)
        return proc, url

    def done(self, url):
        origin, token = url.split("/?")[0], url.split("t=")[1]
        req = urllib.request.Request(
            origin + "/done", data=b"{}", method="POST",
            headers={"X-Contour-Token": token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()

    def test_an_open_canvas_is_present_until_it_is_done(self):
        proc, url = self.canvas()
        self.assertEqual(self.presence(), [{"kind": "canvas", "pid": proc.pid}])
        self.done(url)
        proc.wait(timeout=30)
        self.assertEqual(self.presence(), [])

    def test_a_canvas_told_to_stop_leaves_no_presence(self):
        """Ctrl-C, a closed terminal, and anything tidying up: each is an
        ending, and the record goes with the session on every one of them."""
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=sig.name):
                proc, url = self.canvas()
                self.assertEqual(len(self.presence()), 1)
                proc.send_signal(sig)
                proc.wait(timeout=30)
                self.assertEqual(self.presence(), [])
                self.assertEqual(list((self.space / ".contour" / "presence").iterdir()), [])

    def test_a_presence_stops_nothing(self):
        """Not a hold: a build with a canvas open goes ahead exactly as before.
        `$BLENDER` points nowhere, so a check that was not refused fails for its
        own reason instead of spending a minute in Blender first."""
        self.canvas()
        self.assertEqual(len(self.presence()), 1)
        self.env["BLENDER"] = "/nowhere/blender"
        r = self.contour("check", cwd=self.space)
        self.assertNotIn("is held by", r.stderr)
        self.assertNotIn("presence", r.stdout + r.stderr)

    def test_the_space_git_does_not_see_it(self):
        """Like the run lock, it is about this machine now and is nobody's
        history."""
        self.canvas()
        self.assertEqual(len(self.presence()), 1)
        said = subprocess.run(["git", "-C", str(self.space), "status", "--porcelain",
                               "--untracked-files=all"],
                              capture_output=True, text=True).stdout
        self.assertNotIn("presence", said)


class LiveTest(unittest.TestCase):
    """Judged alive by the hold's own rule, so a page that died without a word
    is absent without anybody cleaning up after it."""

    def setUp(self):
        self.space = Path(tempfile.mkdtemp())
        (self.space / ".contour").mkdir()
        (self.space / ".contour" / "project").write_text("# Contour model space\n")

    def left(self, pid, host=None):
        """A record as a page that never got to remove it would leave it."""
        folder = self.space / ".contour" / "presence"
        folder.mkdir(exist_ok=True)
        (folder / f"{pid}.json").write_text(json.dumps(
            {"kind": "canvas", "pid": pid, "host": host or socket.gethostname()}))

    def test_a_page_whose_process_is_gone_is_absent(self):
        gone = subprocess.Popen([sys.executable, "-c", "pass"])
        gone.wait()
        self.left(gone.pid)
        self.assertEqual(presence.live(self.space), [])

    def test_a_page_on_another_machine_is_never_judged_gone(self):
        """A space in a synced folder: the kernel here cannot be asked about a
        pid there, and unknowable is not gone."""
        self.left(999999, host="somewhere-else")
        self.assertEqual(presence.live(self.space), [
            {"kind": "canvas", "pid": 999999, "host": "somewhere-else"}])

    def test_a_space_nothing_ever_opened_has_nobody_present(self):
        self.assertEqual(presence.live(self.space), [])


class ConsolePresenceTest(ConsoleCase):
    """A console holds its space only during a run, so between runs presence is
    the one thing on disk that says it is there."""

    def kinds(self, space):
        return [p["kind"] for p in presence.live(space)]

    def test_an_open_console_is_present_until_it_is_done(self):
        space = self.space()
        proc, url = self.launch(space)
        self.assertEqual(self.kinds(space), ["console"])
        self.ask(url, "/done", {})
        proc.wait(timeout=30)
        self.assertEqual(self.kinds(space), [])

    def test_a_console_told_to_stop_leaves_no_presence(self):
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=sig.name):
                space = self.space()
                proc, url = self.launch(space)
                self.assertEqual(self.kinds(space), ["console"])
                proc.send_signal(sig)
                proc.wait(timeout=30)
                self.assertEqual(list((space / ".contour" / "presence").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
