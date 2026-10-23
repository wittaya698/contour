"""The transcript shows activity, not calls (ADR 0025, decision 8; issue 72).

Each tool call is one plain line, from one table keyed by tool and, for
`contour`, by command; the raw call stays one click away. Consecutive calls
that only read fold into one line. These drive the console with a scripted
agent, as `test_console` does, and read the transcript a page reads.
"""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from test_console import ConsoleCase    # noqa: E402


class TranscriptTest(ConsoleCase):

    def calls(self, *uses):
        """What the page has on screen once the agent has made these calls."""
        _, url = self.driven(*[{"use": u} for u in uses], {"say": "done"})
        self.ask(url, "/run", {"prompt": "go on"})
        said = self.transcript(url, lambda ev: any(e.get("text") == "done" for e in ev))
        return [e for e in said if e["kind"] == "call"]

    def test_a_call_reads_as_what_was_done_and_keeps_the_raw_call(self):
        call, = self.calls({"tool": "Edit", "file_path": "/m/beaky/build.py",
                            "old_string": "a", "new_string": "b"})
        self.assertEqual(call["activity"], "Changed the build script")
        self.assertEqual(call["tool"], "Edit")
        self.assertEqual(call["call"]["file_path"], "/m/beaky/build.py")

    def test_a_tool_the_table_does_not_know_arrives_raw(self):
        """No words, so the page shows the call itself: a tool added to the
        harness later arrives visible, never hidden."""
        call, = self.calls({"tool": "WebSearch", "query": "glTF bone roll"})
        self.assertIsNone(call["activity"])
        self.assertEqual(call["call"], {"query": "glTF bone roll"})

    def test_consecutive_reads_fold_into_one_line(self):
        """Each read names the line it belongs to, and says that line as it
        now stands; the page redraws one line and not three. Anything else in
        between starts a new one."""
        calls = self.calls({"tool": "Read", "file_path": "/m/beaky/spec.yaml"},
                           {"tool": "Grep", "pattern": "seat"},
                           {"tool": "Read", "file_path": "/m/beaky/build.py"},
                           {"tool": "Edit", "file_path": "/m/beaky/build.py"},
                           {"tool": "Read", "file_path": "/m/beaky/build.py"})
        self.assertEqual([c["activity"] for c in calls],
                         ["Looked at 1 file", "Looked at 2 files", "Looked at 3 files",
                          "Changed the build script", "Looked at 1 file"])
        first = calls[0]["n"]
        self.assertEqual([c["fold"] for c in calls],
                         [first, first, first, None, calls[4]["n"]])

    def test_a_reloaded_tab_ends_on_the_same_lines(self):
        """A tab that was open reads the transcript in pieces, one cursor at a
        time; a reloaded one reads it whole from zero. Drawn the way the page
        draws them — one line per fold, holding its latest words — both end on
        the same lines, because no event is ever rewritten after it lands."""
        _, url = self.driven(*[{"use": {"tool": "Read", "file_path": f"/m/{n}.py"}}
                               for n in "abc"],
                             {"use": {"tool": "Bash", "command": "contour check"}},
                             {"say": "done"})
        self.ask(url, "/run", {"prompt": "go on"})
        whole = self.transcript(url, lambda ev: any(e.get("text") == "done" for e in ev))
        pieces = []
        for cursor in (0, 3, 4):     # the open tab polled mid-fold
            pieces = pieces[:cursor] + self.ask(url, f"/events?since={cursor}")[1]["events"]
        self.assertEqual(drawn(pieces), drawn(whole))
        self.assertEqual(drawn(whole), ["Looked at 3 files", "Built the model"])


def drawn(events):
    """The transcript's call lines, as the page leaves them on screen."""
    lines = {}
    for e in events:
        if e["kind"] == "call":
            lines[e["fold"] if e["fold"] is not None else f"n{e['n']}"] = e["activity"]
    return list(lines.values())


class DriverTest(unittest.TestCase):
    """The real driver hands over the call raw, for the console to word: the
    words are the console's, and a driver that wrote its own would be a
    second table. Run under the console's interpreter, where the SDK is."""

    def test_the_driver_says_a_tool_call_as_its_tool_and_input(self):
        python = ROOT / ".venv" / "bin" / "python"
        if not python.exists():
            self.skipTest("no console environment")
        done = subprocess.run([str(python), "-c", (
            "from claude_agent_sdk import AssistantMessage, TextBlock, ToolUseBlock\n"
            "from console import agent\n"
            "m = AssistantMessage(content=[TextBlock(text='fixing it'), ToolUseBlock("
            "id='t1', name='Bash', input={'command': 'contour check'})], model='m')\n"
            "print(list(agent.said(m)))")], cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(done.stdout.strip(), str([
            ("text", {"text": "fixing it"}),
            ("call", {"tool": "Bash", "call": {"command": "contour check"}})]), done.stderr)


class TableTest(unittest.TestCase):
    """The table itself, read off the launcher's own list of commands."""

    def test_every_contour_command_has_an_activity_line(self):
        """Read from `lib/commands.py`, so a command added to the launcher
        without a line here fails, rather than arriving raw by accident."""
        from lib import activity, commands
        unworded = [c.name for c in commands.TABLE
                    if activity.line("Bash", {"command": f"contour {c.name}"}) is None]
        self.assertEqual(unworded, [])

    def test_the_consoles_own_tools_read_as_what_they_do(self):
        """Its form, spec write and topic proposal have words: raw, `ask` was
        a wall of JSON above the form that said it again."""
        from lib import activity
        asked = {"questions": [{"question": "What is it?"}, {"question": "How big?"}]}
        self.assertEqual(activity.line("mcp__contour__ask", asked), "Asked you 2 questions")
        self.assertEqual(activity.line("mcp__contour__ask", {"questions": [{}]}),
                         "Asked you 1 question")
        self.assertEqual(activity.line("mcp__contour__spec_write", {"content": "", "case": ""}),
                         "Proposed a change to the spec")
        self.assertEqual(activity.line("mcp__contour__topics_propose", {"words": []}),
                         "Suggested words to find this model by")
        self.assertEqual(activity.line("ToolSearch", {"query": "select:x"}),
                         "Looked up its tools")

    def test_a_contour_command_reads_as_its_act_however_it_is_spelled(self):
        from lib import activity
        for spelled in ("contour check", "./contour check", "cd /m/beaky && contour check"):
            self.assertEqual(activity.line("Bash", {"command": spelled}), "Built the model")
        self.assertEqual(activity.line("Bash", {"command": "contour measure side.png --runs 3,4"}),
                         "Measured the side picture")

    def test_a_picture_named_by_a_variable_reads_as_that_picture(self):
        """Issue 153: a run set `R=…` and the page said *Measured the $R
        picture*. A `$` word is shell, and the user is never shown one."""
        from lib import activity
        for spelled in ("R=refs/side.png; contour measure $R --runs 3,4",
                        'R="refs/side.png" && contour measure "${R}" --help 2>&1'):
            with self.subTest(spelled=spelled):
                self.assertEqual(activity.line("Bash", {"command": spelled}),
                                 "Measured the side picture")

    def test_a_picture_that_cannot_be_known_is_a_picture(self):
        from lib import activity
        for spelled in ("contour measure $R --runs 3,4",
                        "contour measure refs/$NAME.png",
                        "contour measure $(ls refs/*.png | head -1)"):
            with self.subTest(spelled=spelled):
                self.assertEqual(activity.line("Bash", {"command": spelled}),
                                 "Measured a picture")


class PageTest(unittest.TestCase):
    """The page's source, as `test_always.PageTest` reads it."""

    def setUp(self):
        from lib.canvas import PAGE
        self.page = PAGE.read_text(encoding="utf-8")
        self.script = self.page.split("function activity(", 1)[1].split("\n}\n", 1)[0]

    def test_a_call_is_its_activity_with_the_raw_call_a_click_away(self):
        self.assertIn("event.activity || called(event)", self.script)
        self.assertIn("the exact call", self.script)

    def test_a_fold_redraws_its_one_line(self):
        self.assertIn("event.fold", self.script)
        self.assertIn("activity(event)", self.page.split("function turn(", 1)[1])


if __name__ == "__main__":
    unittest.main()
