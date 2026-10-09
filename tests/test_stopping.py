"""A page lets go of its port promptly (issue 95).

Every host stops through `Page.stop`: the canvas on Done, the lobby and the
console when their tab closes or a signal arrives. A stop that sat out a
serving loop's poll was half a second of a port still bound and a terminal not
yet given back, every time, and most of the suite's wall clock.
"""
import socket
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.page import Page  # noqa: E402

PROMPT_S = 0.2
"""Well under the 0.5 s a default `serve_forever` poll costs, and well over a
loaded machine's scheduling noise."""


class StoppingTest(unittest.TestCase):
    def started(self):
        page = Page(Path(__file__))
        self.addCleanup(page.stop)
        page.start()
        return page

    def test_a_stop_is_prompt(self):
        page = self.started()
        time.sleep(0.05)                      # the serving loop is in its poll
        began = time.monotonic()
        page.stop()
        self.assertLess(time.monotonic() - began, PROMPT_S)

    def test_a_stopped_page_has_let_go_of_its_port(self):
        """Prompt is worth nothing if it is prompt because it skipped the part
        that releases the port."""
        page = self.started()
        host, port = page._addr
        page.stop()
        with self.assertRaises(ConnectionRefusedError):
            socket.create_connection((host, port), timeout=1).close()

    def test_a_finished_page_stops_promptly_from_wait(self):
        """The path every host takes out: a session ends, `wait` returns."""
        page = self.started()
        time.sleep(0.05)
        began = time.monotonic()
        page.finish()
        page.wait()
        self.assertLess(time.monotonic() - began, PROMPT_S)


if __name__ == "__main__":
    unittest.main()
