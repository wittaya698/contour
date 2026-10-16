"""Entering a space from the lobby (ADR 0021, decisions 2 and 9; issue 36).

Entering spawns `contour-console` in the space, exactly as if it had been typed
there. `$CONTOUR_CONSOLE_PYTHON` stands in for the console's environment, so the
console that starts is the real one; `$BROWSER` sees that it opens no tab.
"""
import os
import signal
import subprocess
import sys
import time
import unittest
import urllib.error

from test_lobby_rename import LobbyRenameCase
from executables import executable
import one_run     # one suite run per machine (issue 94)


class LobbyEnterCase(LobbyRenameCase):

    python = sys.executable
    """The console's interpreter, as the lobby will find it."""

    def open(self, **popen):
        self.env["CONTOUR_CONSOLE_PYTHON"] = self.python
        self.addCleanup(self.close_consoles)
        return super().open(**popen)

    def enter(self, path=None):
        return self.ask("/enter", {"path": str(path or self.space)})

    def consoles(self):
        """The consoles serving the space, from its presence, as the lobby
        lists it."""
        [alpha] = self.ask("/spaces")["spaces"]
        return [p for p in alpha["presence"] if p["kind"] == "console"]

    def wait_for_console(self):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            found = self.consoles()
            if found:
                return found
            time.sleep(0.1)
        self.fail("no console came up on the space")

    def close_consoles(self):
        from lib import presence
        for p in presence.live(self.space):
            os.kill(p["pid"], signal.SIGTERM)


class EnterTest(LobbyEnterCase):

    def test_entering_starts_a_console_on_the_space_and_the_lobby_keeps_running(self):
        said = self.enter()
        self.assertIsNone(said["refused"])
        [console] = self.wait_for_console()
        self.assertIn("enter", self.ask("/can")["can"])

    def test_a_ctrl_c_in_the_lobby_s_terminal_ends_the_lobby_and_no_console(self):
        """A terminal's Ctrl-C reaches its whole foreground process group, and
        the lobby is started here in a group of its own to stand for that."""
        lobby = self.open(process_group=0)
        self.enter()
        [console] = self.wait_for_console()
        os.killpg(lobby.pid, signal.SIGINT)
        self.assertEqual(lobby.wait(timeout=30), 0, lobby.stdout.read())
        time.sleep(1)                         # long enough for one started anyway to show
        from lib import presence
        self.assertEqual(presence.live(self.space), [console])

    def test_a_tab_closed_on_the_lobby_ends_no_console(self):
        self.env["CONTOUR_LOBBY_GRACE"] = "0.5"
        lobby = self.open()
        self.enter()
        [console] = self.wait_for_console()
        self.ask("/beat", {})
        self.assertEqual(lobby.wait(timeout=30), 0)
        from lib import presence
        self.assertEqual(presence.live(self.space), [console])

    def test_a_space_open_in_a_console_shows_its_page_and_starts_no_second(self):
        """Its person may have lost the tab: entering again asks the console to
        open its own page (ADR 0031, decision 1)."""
        self.enter()
        [console] = self.wait_for_console()
        self.assertIsNone(self.enter()["refused"])
        time.sleep(1)                         # long enough for one started anyway to show
        self.assertEqual(self.consoles(), [console])

    def test_a_directory_the_lobby_does_not_list_is_not_a_space_to_enter(self):
        for path in (self.tmp, self.space / "refs"):
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as no:
                self.enter(path)
            self.assertEqual(no.exception.code, 404)
            no.exception.close()
        time.sleep(1)                         # long enough for one started anyway to show
        self.assertEqual(self.consoles(), [])


class RevealTest(LobbyEnterCase):
    """Open in Finder: the escape hatch for anything the lobby does not do.
    An `open` ahead of the real one on `$PATH` writes down what it was asked
    to open, so no Finder window opens."""

    def open(self, **popen):
        shim = self.tmp / "bin"
        shim.mkdir(exist_ok=True)
        self.opened = self.tmp / "opened"
        executable(shim / "open",                        # `opened` is beside `bin/`
                   '#!/bin/sh\necho "$@" >> "$(dirname "$0")/../opened"\n')
        self.env["PATH"] = f"{shim}:{os.environ['PATH']}"
        return super().open(**popen)

    def test_it_opens_the_space_s_directory(self):
        said = self.ask("/reveal", {"path": str(self.space)})
        self.assertIsNone(said["refused"])
        self.assertEqual(self.opened.read_text(), f"{self.space}\n")

    def test_it_is_offered_where_there_is_a_finder_to_open(self):
        offered = "reveal" in self.ask("/can")["can"]
        self.assertEqual(offered, sys.platform == "darwin")

    def test_a_lobby_not_granted_it_opens_nothing(self):
        """Elsewhere, `open` is some other program: on Linux it is `openvt`."""
        from lib.lobby import CAN, Lobby
        listing = lambda: {"spaces": [{"path": str(self.space), "presence": []}]}
        said = Lobby(listing, can=CAN).reveal({"path": str(self.space)})
        self.assertIn("no Finder", said["refused"])
        self.assertFalse(self.opened.exists())

    def test_a_directory_the_lobby_does_not_list_is_not_opened(self):
        for path in (self.tmp, self.space / "refs"):
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as no:
                self.ask("/reveal", {"path": str(path)})
            self.assertEqual(no.exception.code, 404)
            no.exception.close()
        self.assertFalse(self.opened.exists())


class NoEnvironmentTest(LobbyEnterCase):

    python = "/nowhere/python"

    def test_with_no_console_environment_enter_is_not_granted_and_starts_nothing(self):
        self.assertNotIn("enter", self.ask("/can")["can"])
        said = self.enter()
        self.assertIn("no console environment", said["refused"])
        time.sleep(1)                         # long enough for one started anyway to show
        self.assertEqual(self.consoles(), [])

    def test_the_page_is_given_the_line_contour_console_prints_to_make_one(self):
        from lib import enter
        r = subprocess.run([str(enter.CONSOLE)], cwd=self.space, env=self.env,
                           capture_output=True, text=True, timeout=30)
        line = self.ask("/environment")["console"]
        self.assertTrue(line)
        self.assertIn(line, r.stderr)

    def test_where_there_is_one_the_page_is_given_no_line(self):
        self.python = sys.executable
        self.open()
        self.assertIsNone(self.ask("/environment")["console"])


if __name__ == "__main__":
    unittest.main()
