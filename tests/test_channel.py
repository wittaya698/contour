"""The channel: a pointer to a parked run, never a key (ADR 0027, decision 7;
issue 91).

A requester that needs the person at a gate asks Contour to show them the page.
The asking carries nothing, and the console opens its own URL in this machine's
browser, so the secret goes from console to browser and never through the
caller. `$BROWSER` writes down what the browser was asked to open, as it does
for every page a call starts.
"""
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_connector import PagesCase, call    # noqa: E402
from test_console import STAND_IN    # noqa: E402
from test_lobby_enter import LobbyEnterCase    # noqa: E402
from executables import executable    # noqa: E402
from test_run_record import RecordCase    # noqa: E402

from console.run import Run    # noqa: E402

from lib import last_run, notify, presence    # noqa: E402

SPEC_WRITE = {"tool": "Edit", "file_path": "spec.yaml",
              "old_string": "a", "new_string": "b"}
WAIT_S = 15


class ChannelCase(PagesCase):

    def setUp(self):
        super().setUp()
        (self.home / "ceiling.json").write_text('{"weighted": 1000000}\n')

    def requested(self, *script):
        """A console running unattended on `alpha`, parked where the script
        parks it."""
        r = self.contour("request", "alpha", "make the beak longer", "--as", "the nightly agent",
                         env=dict(CONTOUR_CONSOLE_AGENT=f"{STAND_IN}:drive",
                                  CONTOUR_AGENT_SCRIPT=json.dumps(list(script))))
        said = json.loads(r.stdout)
        self.assertTrue(said["started"], said)
        return said

    def contour(self, *args, stdin="", env=None):
        if env:
            self.env.update(env)
        return super().contour(*args, stdin=stdin)

    def until(self, state):
        deadline = time.monotonic() + WAIT_S
        while time.monotonic() < deadline:
            said = last_run.read(self.space)
            if said and said["state"] == state:
                return said
            time.sleep(0.05)
        self.fail(f"the record never said {state!r}: {last_run.read(self.space)}")

    def open(self):
        """`open console` on `alpha`, as raw text and as a reading."""
        r = self.contour("mcp", stdin=json.dumps(call(
            1, "tools/call", name="open", arguments={"page": "console", "space": "alpha"})) + "\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        [block] = json.loads(r.stdout)["result"]["content"]
        return block["text"], json.loads(block["text"])


class ShowTest(ChannelCase):

    def test_open_console_brings_up_an_unattended_consoles_page(self):
        self.requested({"call": SPEC_WRITE})
        self.until("waiting for you")
        text, said = self.open()
        self.assertIsNone(said["refused"], said)
        [url] = self.urls()
        self.serving(url)
        self.assertSecretless(text, url)
        [console] = presence.live(self.space)
        self.assertEqual(int(self.opened.read_text().split()[0]), console["pid"])

    def test_asking_twice_opens_the_page_twice_and_never_a_second_console(self):
        self.requested({"call": SPEC_WRITE})
        self.until("waiting for you")
        for _ in range(2):
            self.assertIsNone(self.open()[1]["refused"])
        deadline = time.monotonic() + WAIT_S
        while len(self.urls()) < 2 and time.monotonic() < deadline:
            time.sleep(0.1)
        first, second = self.urls()
        self.assertEqual(first, second)
        self.assertEqual(len(presence.live(self.space)), 1)

    def test_a_console_somebody_is_watching_is_still_its_tabs(self):
        """An attended run's console: a person's workspace, whose tab is the
        way in, and not a page to throw up on their screen (ADR 0027,
        decision 6)."""
        # And so is one whose unattended run is over: the page's rule has it,
        # like any (ADR 0027, decision 4). This process stands for its console.
        self.requested({"say": "done"})
        self.until("finished")
        with presence.present(self.space, "console"):
            _, said = self.open()
        self.assertIn("its tab is the way in", said["refused"])
        time.sleep(1)                         # long enough for a page to show
        self.assertFalse(self.opened.exists(), "a page was opened anyway")


class RowTest(ChannelCase):
    """The lobby's row, from `contour spaces --json`, the one reading behind it."""

    def row(self):
        [alpha] = json.loads(self.contour("spaces", "--json").stdout)["spaces"]
        return alpha

    def test_a_parked_run_reads_waiting_for_you_and_unattended(self):
        self.requested({"call": SPEC_WRITE})
        self.until("waiting for you")
        row = self.row()
        self.assertEqual(row["waiting"], "Claude wants to change the spec")
        self.assertTrue(row["unattended"])

    def test_a_working_or_finished_run_is_not_waiting(self):
        self.requested({"busy": 2}, {"say": "done"})
        self.until("running")
        self.assertIsNone(self.row()["waiting"])
        self.until("finished")
        row = self.row()
        self.assertIsNone(row["waiting"])
        self.assertFalse(row["unattended"])


class LobbyPageTest(unittest.TestCase):
    """The lobby page's source, structural as `test_lobby`'s page tests are:
    there is no browser here."""

    def setUp(self):
        page = (Path(__file__).resolve().parent.parent / "lib" / "lobby.html").read_text()
        self.row = page.split("function row(")[1].split("\n}\n")[0]

    def test_a_parked_run_reads_waiting_for_you_with_its_act(self):
        self.assertIn("'waiting for you: ' + s.waiting", self.row)

    def test_an_unattended_console_is_entered_and_a_watched_one_is_its_tabs(self):
        """Open asks the console to show its page; a person's console is
        still reached by its tab."""
        self.assertIn("const open = s.presence.some(p => p.kind === 'console') "
                      "&& !s.unattended", self.row)


class NotifiedTest(RecordCase):
    """When a run nobody is watching parks, the console says so on this
    machine itself, so reaching the person never rests on a requester relaying
    anything. It names the space and the act and holds no link."""

    def setUp(self):
        super().setUp()
        self.said = self.space / "notified"
        notifier = executable(self.space / "notifier",
                              '#!/bin/sh\nprintf "%s\\n" "$*" >> "$(dirname "$0")/notified"\n')
        patched = mock.patch.dict(os.environ, {"CONTOUR_NOTIFIER": str(notifier),
                                               "CONTOUR_HOME": str(self.space / "home")})
        patched.start()
        self.addCleanup(patched.stop)

    def parked(self, tool, call, requester="the nightly agent"):
        run = Run(self.space, drive=lambda prompt, options, gate, say: gate(tool, dict(call)))
        run.start("make the beak longer", ceiling=10**6, requester=requester)
        self.addCleanup(lambda: run.live and run.end())
        deadline = time.monotonic() + WAIT_S
        while (last_run.read(self.space) or {}).get("state") != "waiting for you":
            self.assertLess(time.monotonic(), deadline, last_run.read(self.space))
            time.sleep(0.01)
        # The notifier runs on its own; long enough for one that was posted
        # to have written, and for one that was not to have had the chance.
        settle = time.monotonic() + (WAIT_S if requester else 1)
        while not self.said.exists() and time.monotonic() < settle:
            time.sleep(0.05)
        time.sleep(0.1)
        return self.said.read_text().splitlines() if self.said.exists() else []

    def test_a_parked_gate_says_the_space_and_the_act(self):
        said = self.parked("Edit", {"file_path": "spec.yaml", "old_string": "a",
                                    "new_string": "b"})
        self.assertEqual(said, [f"{self.space.name} is waiting for you: "
                                f"Claude wants to change the spec"])

    def test_a_parked_question_says_so_too(self):
        said = self.parked("AskUserQuestion", {"questions": [{"question": "How long?"}]})
        self.assertEqual(said, [f"{self.space.name} is waiting for you: "
                                f"Claude has a question"])

    def test_a_run_somebody_is_watching_posts_nothing(self):
        self.assertEqual(self.parked("Edit", {"file_path": "spec.yaml",
                                              "old_string": "a", "new_string": "b"},
                                     requester=None), [])


class OnMacTest(unittest.TestCase):
    """What posts it with no hatch set, on this machine's kind of machine."""

    def test_a_quote_in_the_words_stays_inside_the_notification(self):
        with mock.patch.dict(os.environ, {"CONTOUR_NOTIFIER": ""}), \
                mock.patch.object(notify.sys, "platform", "darwin"):
            argv = notify.command('the "big" chair is waiting for you: a\\b')
        self.assertEqual(argv, ["osascript", "-e", 'display notification '
                                '"the \\"big\\" chair is waiting for you: a\\\\b" '
                                'with title "Contour"'])


class LobbyTest(LobbyEnterCase):
    """The lobby's enter, the other door to the same console."""

    def setUp(self):
        super().setUp()
        (self.home / ".contour" / "ceiling.json").write_text('{"weighted": 1000000}\n')
        self.opened = self.tmp / "opened"
        self.env["BROWSER"] = str(executable(
            self.tmp / "browser", '#!/bin/sh\necho "$PPID $1" >> "$(dirname "$0")/opened"\n'))
        self.env.update(CONTOUR_CONSOLE_PYTHON=sys.executable,
                        CONTOUR_CONSOLE_AGENT=f"{STAND_IN}:drive",
                        CONTOUR_AGENT_SCRIPT=json.dumps([{"call": SPEC_WRITE}]))
        self.addCleanup(self.close_consoles)
        said = json.loads(self.contour("request", "alpha", "make the beak longer",
                                       cwd=self.spaces).stdout)
        self.assertTrue(said["started"], said)
        deadline = time.monotonic() + WAIT_S
        while (last_run.read(self.space) or {}).get("state") != "waiting for you":
            self.assertLess(time.monotonic(), deadline, last_run.read(self.space))
            time.sleep(0.05)

    def test_enter_brings_up_an_unattended_consoles_page(self):
        said = self.enter()
        self.assertIsNone(said["refused"], said)
        deadline = time.monotonic() + WAIT_S
        while not (self.opened.exists() and self.opened.read_text().strip()):
            self.assertLess(time.monotonic(), deadline, "no page asked for a browser")
            time.sleep(0.1)
        self.assertNotIn("http", json.dumps(said))
        self.assertEqual(len(self.consoles()), 1)


if __name__ == "__main__":
    unittest.main()
