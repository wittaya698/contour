"""One look, and a way back to the lobby (ADR 0025, decision 12; issue 76).

The lobby and the canvas-and-console page take their colours, type, buttons
and verdict styles from one stylesheet both hosts serve, and every page carries
the same thin header: *Models › oak-chair* and the verdict. *Models* goes to
the lobby, starting one if none is running.

Served as a browser asks for them, because the stylesheet arrives in the page
and a page's source alone does not show it.
"""
import contextlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.canvas import Canvas    # noqa: E402
from lib.lobby import Lobby    # noqa: E402
from lib.page import LOOK    # noqa: E402
from client import open_url, post    # noqa: E402
from executables import executable  # noqa: E402

CONTOUR = ROOT / "contour"


def served(page):
    """`page` started, and the HTML a browser gets from it."""
    page.start()
    try:
        with open_url(page, "/", timeout=5) as r:
            return r.read().decode()
    finally:
        page.stop()


def lobby():
    return Lobby(lambda: {"spaces": [], "deleted": [], "roots": []}, can=())


def canvas():
    tmp = Path(tempfile.mkdtemp())
    return Canvas(sheet=tmp / "sheet.png", marks=tmp / "marks.json")


class LookTest(unittest.TestCase):

    def test_both_pages_render_from_the_one_stylesheet(self):
        look = LOOK.read_text(encoding="utf-8")
        for page in (lobby(), canvas()):
            self.assertIn(look, served(page), type(page).__name__)

    def test_the_stylesheet_is_light_and_dark(self):
        """Each colour the pages use is a token, said once for light and once
        again for dark."""
        look = LOOK.read_text(encoding="utf-8")
        light = re.search(r":root \{([^}]*)\}", look).group(1)
        dark = look.split("prefers-color-scheme: dark", 1)[1]
        tokens = set(re.findall(r"(--[a-z]+):", light))
        self.assertTrue({"--bg", "--fg", "--muted", "--line", "--warn", "--ok"} <= tokens)
        for token in tokens - {"--agent", "--pin"}:
            self.assertIn(token + ":", dark, f"{token} has no dark value")

    def test_no_page_says_its_own_colours(self):
        """A page that redefined a token would be a second look."""
        from lib.canvas import PAGE as CANVAS
        from lib.lobby import PAGE as LOBBY
        for page in (CANVAS, LOBBY):
            own = page.read_text(encoding="utf-8").split("<style>", 1)[1].split("</style>", 1)[0]
            self.assertNotIn(":root", own, page.name)
            self.assertNotIn("prefers-color-scheme", own, page.name)


class HeaderTest(unittest.TestCase):
    """The page's source, because there is no browser here."""

    def header(self, page):
        return page.split('<header class="top">', 1)[1].split("</header>", 1)[0]

    def test_the_lobby_canvas_and_console_carry_the_header(self):
        """The console is the canvas's page under another host, so two pages
        are all three."""
        from lib.canvas import PAGE as CANVAS
        from lib.lobby import PAGE as LOBBY
        for page in (CANVAS, LOBBY):
            source = page.read_text(encoding="utf-8")
            self.assertEqual(source.count('<header class="top">'), 1, page.name)
            self.assertIn(">Models<", self.header(source), page.name)
            self.assertNotIn("data-needs", self.header(source), "every host has it")

    def test_the_canvas_header_names_the_model_and_carries_the_verdict(self):
        from lib.canvas import PAGE
        page = PAGE.read_text(encoding="utf-8")
        header = self.header(page)
        self.assertIn('class="model"', header)
        self.assertIn('id="verdict"', header)
        self.assertEqual(page.count('id="verdict"'), 1, "the verdict moved, not copied")
        labelled = page.split("async function labelled(", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("said.model", labelled)

    def test_models_asks_the_host_for_the_lobby(self):
        """The page never knows the lobby's address, which carries its
        secret: it asks its own host, which opens the lobby or starts one."""
        from lib.canvas import PAGE
        page = PAGE.read_text(encoding="utf-8")
        self.assertEqual(page.count("function backToModels("), 1)
        back = page.split("function backToModels(", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("ask('/models', {})", back)
        self.assertIn("preventDefault()", back)


class WayBackTest(unittest.TestCase):
    """*Models* goes to the lobby, starting one if none is running. Real
    lobbies, started as the user starts one, with a browser that writes down
    what it was asked to open instead of opening it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        (self.tmp / "spaces").mkdir()
        self.opened = self.tmp / "opened"
        browser = executable(self.tmp / "browser",       # `opened` is beside it
                             '#!/bin/sh\necho "$1" >> "$(dirname "$0")/opened"\n')
        self.env = {"CONTOUR_SPACES": str(self.tmp / "spaces"),
                    "CONTOUR_HOME": str(self.tmp / "home"), "BROWSER": str(browser)}
        self.addCleanup(self.stop_lobbies)

    def stop_lobbies(self):
        record = self.tmp / "home" / "lobby.json"
        if record.exists():
            with contextlib.suppress(ProcessLookupError, ValueError):
                os.kill(json.loads(record.read_text())["pid"], signal.SIGTERM)

    def lobby(self):
        """`contour lobby`, as typed; the address it printed."""
        proc = subprocess.Popen([sys.executable, str(CONTOUR), "lobby"], cwd=str(self.tmp),
                                env=dict(os.environ, **self.env), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        self.addCleanup(proc.stdout.close)
        self.addCleanup(proc.kill)
        return proc, re.search(r"http://\S+", proc.stdout.readline()).group(0)

    def browsed(self, count):
        """What the browser was asked to open, once it has been asked `count`
        times."""
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            said = self.opened.read_text().split() if self.opened.exists() else []
            if len(said) >= count:
                return said
            time.sleep(0.1)
        self.fail(f"the browser was asked to open {count}, and got {said}")

    def test_a_second_lobby_shows_the_running_one_and_starts_nothing(self):
        _, url = self.lobby()
        self.browsed(1)
        again = subprocess.run([sys.executable, str(CONTOUR), "lobby"], cwd=str(self.tmp),
                               env=dict(os.environ, **self.env), capture_output=True,
                               text=True, timeout=30)
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertNotIn("http://", again.stdout, "its address is the running one's to say")
        self.assertEqual(self.browsed(2), [url, url])

    def test_models_opens_the_running_lobby(self):
        _, url = self.lobby()
        self.browsed(1)
        self.models()
        self.assertEqual(self.browsed(2), [url, url])

    def test_models_starts_a_lobby_when_none_is_running(self):
        self.models()
        started = self.browsed(1)[0]
        self.assertRegex(started, r"^http://127\.0\.0\.1:\d+/\?t=")

    def models(self):
        """The header's *Models*, pressed on a canvas: the page's POST."""
        page = canvas()
        page.start()
        self.addCleanup(page.stop)
        with mock.patch.dict(os.environ, self.env):
            self.assertEqual(post(page, "/models", {})[0], 200)


if __name__ == "__main__":
    unittest.main()
