"""`tools/tokens.py`: what an iteration cost, from either kind of session.

Token cost is the second of the three stated priorities, and this tool is the
whole of Contour's accounting for it. It grew up reading the Claude Code
transcript for a project; a console run produces no transcript and records its
own turns instead (ADR 0019, decision 37). Both have to arrive in one table in
one set of units, or the priority is served by two numbers that cannot be
compared.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from console import spend

TOKENS = ROOT / "tools" / "tokens.py"


class TokensCase(unittest.TestCase):
    """A project on disk, and the tool run over it the way a person runs it."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp())

    def space(self):
        space = Path(tempfile.mkdtemp())
        (space / ".contour").mkdir()
        (space / ".contour" / "project").write_text("# Contour model space\n")
        return space

    def spent(self, space, run, *turns, prompt="why is the neck 269"):
        """A console run's worth of recorded turns, as the console records them."""
        for turn in turns:
            spend.record(space, run, turn, turn.pop("gates", 0), prompt)
        return run

    def typed(self, space, prompt, *turns):
        """A terminal session for this project: a prompt, and the turns it caused.

        Written where Claude Code writes one, under a `$HOME` of our own — the
        tool finds transcripts by the home directory, and a test that wrote into
        the real one would be editing the user's own accounting to prove a point
        about it.
        """
        # Resolved, as the tool resolves it: on macOS a temp path is a
        # symlink, and the two spellings are two different slugs.
        slug = "-" + str(space.resolve()).lstrip("/").replace("/", "-")
        where = self.home / ".claude" / "projects" / slug
        where.mkdir(parents=True, exist_ok=True)
        events = [{"type": "user", "timestamp": "2026-09-27T12:00:00Z",
                   "gitBranch": "terminal",
                   "message": {"content": [{"type": "text", "text": prompt}]}}]
        events += [{"type": "assistant",
                    "message": {"content": [], "usage": turn}} for turn in turns]
        (where / "session.jsonl").write_text(
            "\n".join(json.dumps(e) for e in events) + "\n")

    def report(self, space, *args):
        """What the tool prints for this project."""
        done = subprocess.run([sys.executable, str(TOKENS), "--project", str(space),
                               *args], capture_output=True, text=True,
                              env=dict(os.environ, HOME=str(self.home)))
        return done.returncode, done.stdout + done.stderr


class ConsoleRunTest(TokensCase):

    def test_a_console_run_is_reported_as_one_iteration(self):
        """One run is one prompt and every turn it caused, which is exactly what
        this tool has always called an iteration. Same unit, so a console run and
        a terminal one can be read off one table and compared."""
        space = self.space()
        self.spent(space, "r1",
                   {"input_tokens": 200, "cache_read_input_tokens": 40_000,
                    "output_tokens": 300},
                   {"input_tokens": 100, "output_tokens": 50, "gates": 1})
        code, said = self.report(space, "--json")
        self.assertEqual(code, 0, said)
        payload = json.loads(said)
        runs = [it for group in payload.values() for it in group]
        self.assertEqual(len(runs), 1, f"one run, {len(runs)} iterations: {said}")
        self.assertEqual(runs[0]["turns"], 2)
        self.assertEqual(runs[0]["input"], 300)
        self.assertEqual(runs[0]["cache_read"], 40_000)
        self.assertEqual(runs[0]["output"], 350)

    def test_a_console_run_and_a_terminal_iteration_are_weighed_the_same_way(self):
        """One set of units, or the priority is served by two numbers nobody can
        compare. The same four figures spent at a console and spent at a terminal
        have to come back as the same cost — which is a claim about the two
        readers agreeing, so both are read here, off one report."""
        space = self.space()
        figures = {"input_tokens": 200, "cache_read_input_tokens": 40_000,
                   "cache_creation_input_tokens": 1_000, "output_tokens": 300}
        self.spent(space, "r1", dict(figures))
        self.typed(space, "why is the neck 269", dict(figures))
        code, said = self.report(space, "--json")
        self.assertEqual(code, 0, said)
        every = [it for group in json.loads(said).values() for it in group]
        self.assertEqual(len(every), 2, f"a run and an iteration: {said}")
        self.assertEqual(len({it["weighted"] for it in every}), 1,
                         f"one spend, two prices: {every!r}")
        # And the figure itself, so the two agreeing on a wrong number is not a
        # pass: 200 + 0.10*40000 + 1.25*1000 + 5*300.
        self.assertEqual(every[0]["weighted"], 6950)

    def test_the_table_names_a_console_run_by_its_prompt(self):
        """Read by somebody asking where their tokens went. A row labelled with a
        run id sends them to a transcript that ended with the tab."""
        space = self.space()
        self.spent(space, "r1", {"input_tokens": 100, "output_tokens": 10},
                   prompt="why is the neck 269")
        code, said = self.report(space)
        self.assertEqual(code, 0, said)
        self.assertIn("why is the neck 269", said)

    def test_the_report_says_what_the_gates_cost(self):
        """The display's second job, in the tool as well as on the page. A gate
        costs a turn of re-explanation, and *tune the ask-list downward* should be
        an informed act rather than an irritated one (ADR 0019, decisions 36
        and 37)."""
        space = self.space()
        self.spent(space, "r1",
                   {"input_tokens": 100, "output_tokens": 10},
                   {"input_tokens": 100, "output_tokens": 10, "gates": 1},
                   {"input_tokens": 100, "output_tokens": 10, "gates": 2})
        code, said = self.report(space, "--json")
        run = [it for group in json.loads(said).values() for it in group][0]
        self.assertEqual((code, run["gates"]), (0, 2), said)
        # Two of the three turns followed a verdict: 2 * (100 + 5*10).
        self.assertEqual(run["after_gates"], 300)
        _, printed = self.report(space)
        self.assertIn("gates", printed)
        self.assertIn("300", printed, "what the gates cost is not on the report")


class TerminalOnlyTest(TokensCase):
    """The tool as it was. This slice adds a second source and must subtract
    nothing: most projects have no console runs at all, and the accounting for the
    second stated priority is not a thing to break while extending."""

    def test_a_project_with_no_console_runs_reports_what_it_always_did(self):
        space = self.space()
        self.typed(space, "why is the neck 269",
                   {"input_tokens": 200, "output_tokens": 300})
        code, said = self.report(space, "--json")
        self.assertEqual(code, 0, said)
        payload = json.loads(said)
        self.assertNotIn("console", payload,
                         "a console section for a project with no console runs")
        every = [it for group in payload.values() for it in group]
        self.assertEqual(len(every), 1)
        self.assertEqual(every[0]["weighted"], 200 + 5 * 300)
        _, printed = self.report(space)
        self.assertNotIn("gates", printed,
                         "a gate line where no gate ever happened")

    def test_a_project_with_neither_still_says_where_it_looked(self):
        """The error that tells a first-time reader what this tool reads. It has
        to survive the slice: a console run is a second source, not a reason for
        *nothing here* to become silence."""
        code, said = self.report(self.space())
        self.assertEqual(code, 1)
        self.assertIn("no transcripts at", said)

    def test_the_accounting_reads_a_console_run_on_a_bare_clone(self):
        """The tool now imports `console/spend.py`, which is how one definition of
        what a turn cost serves both readers. That import must stay free: the
        accounting is run from the toolkit, `console/` is the one directory
        allowed a dependency, and a tool that needed the SDK installed to say what
        a run cost would go silent exactly where a clone has no environment.
        """
        space = self.space()
        self.spent(space, "r1", {"input_tokens": 100, "output_tokens": 10})
        done = subprocess.run(
            [sys.executable, "-S", str(TOKENS), "--project", str(space), "--json"],
            capture_output=True, text=True,
            # No site-packages at all (`-S`) and nothing handed in on the path:
            # whatever answers here answers on a clone with nothing installed.
            env={"HOME": str(self.home), "PATH": os.environ.get("PATH", "")})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("weighted", done.stdout)


if __name__ == "__main__":
    unittest.main()
