"""Build gates can be allowed for good, and undone (ADR 0025, decision 6; issue 69).

*Always for this model* writes this space's ask-list entry as the user's own act
from the page. The per-space list replaces the global one whole (ADR 0019,
decision 36), so what is written is the list as it resolves now plus `build` —
never `build` alone, which would silently retire whatever the global list let
through. These drive the command the page is a client of, and read the result
back through `contour asks`, the audit a person runs.
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

from lib import policy    # noqa: E402
from test_console import ConsoleCase    # noqa: E402


class AlwaysTest(unittest.TestCase):

    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.space = Path(tempfile.mkdtemp())
        (self.space / ".contour").mkdir()
        (self.space / ".contour" / "project").write_text("# Contour model space\n")

    def contour(self, *args):
        done = subprocess.run([sys.executable, str(ROOT / "contour"), *args],
                              cwd=str(self.space), capture_output=True, text=True,
                              timeout=30, env=dict(os.environ, CONTOUR_HOME=str(self.home)))
        return done.returncode, done.stdout + done.stderr

    def asks(self):
        return self.contour("asks")[1].splitlines()

    def test_always_lets_builds_through_for_this_model_and_asks_shows_it(self):
        code, said = self.contour("asks", "--always", "build", "--json")
        self.assertEqual(code, 0, said)
        self.assertEqual(json.loads(said)["allowed"], ["build"])
        self.assertIn("allow build", self.asks())
        self.assertIn("ask commit", self.asks())

    def test_a_global_entry_survives_a_per_space_always(self):
        """The resolved list, plus `build`: a space's own list replaces the
        global one whole, so writing `build` alone would quietly ask again about
        the commits the user let through everywhere. Another space's entry is
        none of this write's business, and it is still there afterwards.

        Named and left silent, which is how a space takes the global list: one
        the file never names lets nothing through, so it has none to keep."""
        other = Path(tempfile.mkdtemp())
        (self.home / "ask-list.yaml").write_text(
            f"allow:\n  - commit\nspaces:\n  {self.space}:\n"
            f"  {other}:\n    allow:\n      - spec-write\n")
        self.assertEqual(self.contour("asks", "--always", "build")[0], 0)
        self.assertIn("allow commit", self.asks())
        self.assertIn("allow build", self.asks())
        self.assertEqual(policy.allowed(None, self.home / "ask-list.yaml"), ("commit",))
        self.assertEqual(policy.allowed(other, self.home / "ask-list.yaml"), ("spec-write",))

    def test_only_a_build_can_be_allowed_for_good(self):
        """Spec writes, reference writes and saving a version always ask, and a
        push is never offered: the command refuses them, so a page that offered
        one by mistake still could not write it."""
        for category in ("spec-write", "ref-write", "commit", "push"):
            code, said = self.contour("asks", "--always", category, "--json")
            self.assertEqual(code, 1, category)
            self.assertIn("always asks", json.loads(said)["refused"])
        self.assertFalse((self.home / "ask-list.yaml").exists())

    def test_undo_asks_again_and_keeps_the_rest(self):
        (self.home / "ask-list.yaml").write_text(f"allow:\n  - commit\nspaces:\n  {self.space}:\n")
        self.contour("asks", "--always", "build")
        code, said = self.contour("asks", "--undo", "build", "--json")
        self.assertEqual(code, 0, said)
        self.assertEqual(json.loads(said)["allowed"], ["commit"])
        self.assertIn("ask build", self.asks())


class GateTest(ConsoleCase):
    """*Always* at the gate it belongs to, through the real console: a scripted
    agent raises the gate as `test_console.RunTest` raises one."""

    def gated(self, command, home, space=None):
        _, url = self.driven({"call": {"tool": "Bash", "command": command}},
                             space=space or self.space(), CONTOUR_HOME=str(home))
        self.ask(url, "/run", {"prompt": "go on"})
        return url, self.gate(url)[0]

    def test_a_build_gate_offers_always_and_no_other_gate_does(self):
        home = Path(tempfile.mkdtemp())
        _, build = self.gated("contour check", home)
        self.assertTrue(build["said"]["always"])
        for command in ("git commit -m seat", "git push", "sed -i s/1/2/ spec.yaml"):
            _, other = self.gated(command, home)
            self.assertFalse(other["said"]["always"], command)

    def test_always_allows_this_build_and_the_next_runs_unwatched(self):
        home, space = Path(tempfile.mkdtemp()), self.space()
        url, gate = self.gated("contour check", home, space)
        self.ask(url, "/verdict", {"id": gate["id"], "allow": True, "always": True})
        said = self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        self.assertTrue([e for e in said if e["kind"] == "result"][0]["allowed"])
        self.assertEqual(policy.allowed(space, home / "ask-list.yaml"), ("build",))

    def test_always_on_a_gate_that_does_not_offer_it_writes_nothing(self):
        """The page never sends it there; a request that does is answered as
        the plain allow it also says, and the list is left as it was."""
        home = Path(tempfile.mkdtemp())
        url, gate = self.gated("git commit -m seat", home)
        self.ask(url, "/verdict", {"id": gate["id"], "allow": True, "always": True})
        self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        self.assertFalse((home / "ask-list.yaml").exists())


class AgentTest(ConsoleCase):
    """The writer is the page's and never the agent's: an agent widening its
    own permissions is what the ask-list exists to prevent. Refused by the
    console outright — not a gate, since a gate the user allowed by reflex
    would be the agent granting itself builds by the user's hand."""

    def ran(self, call, home):
        _, url = self.driven({"call": call}, CONTOUR_HOME=str(home))
        self.ask(url, "/run", {"prompt": "go on"})
        said = self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        return said

    def test_the_agents_call_to_the_writer_is_refused_without_a_gate(self):
        home = Path(tempfile.mkdtemp())
        for call in ({"tool": "Bash", "command": "contour asks --always build"},
                     {"tool": "Bash", "command": "cd .. && ./contour asks --undo build --json"},
                     {"tool": "Write", "file_path": str(home / "ask-list.yaml"),
                      "content": "allow: [build]\n"},
                     {"tool": "Bash", "command": f"echo 'allow: [push]' > {home}/ask-list.yaml"}):
            said = self.ran(call, home)
            self.assertFalse(any(e["kind"] == "gate" for e in said), call)
            self.assertFalse([e for e in said if e["kind"] == "result"][0]["allowed"], call)
        self.assertFalse((home / "ask-list.yaml").exists())

    def test_reading_the_list_is_still_the_agents_to_do(self):
        """`contour asks` is the audit, and an agent may read what it is let do."""
        said = self.ran({"tool": "Bash", "command": "contour asks"}, Path(tempfile.mkdtemp()))
        self.assertTrue([e for e in said if e["kind"] == "result"][0]["allowed"])


class UnwatchedTest(ConsoleCase):
    """What runs without asking for this model, on the page, each with Undo."""

    def test_the_page_is_told_what_runs_unwatched_and_undo_removes_one(self):
        home, space = Path(tempfile.mkdtemp()), self.space()
        (home / "ask-list.yaml").write_text(f"allow:\n  - commit\nspaces:\n  {space}:\n")
        policy.always(space, "build", home / "ask-list.yaml")
        _, url = self.launch(space, CONTOUR_HOME=str(home))
        _, said = self.ask(url, "/asks")
        self.assertEqual([r["category"] for r in said["unwatched"]], ["build", "commit"])
        self.assertEqual(said["unwatched"][0]["says"], "Building the model to check its work")
        _, said = self.ask(url, "/undo", {"category": "build"})
        self.assertEqual([r["category"] for r in said["unwatched"]], ["commit"])
        self.assertTrue(policy.gated("build", space, home / "ask-list.yaml"))

    def test_silence_still_means_ask(self):
        """No list, nothing unwatched: the page shows no section to undo."""
        _, url = self.launch(self.space(), CONTOUR_HOME=tempfile.mkdtemp())
        self.assertEqual(self.ask(url, "/asks")[1]["unwatched"], [])


class PageTest(unittest.TestCase):
    """The page's source, as `test_gate.GatePageTest` reads it."""

    def setUp(self):
        from lib.canvas import PAGE
        self.page = PAGE.read_text(encoding="utf-8")
        self.template = self.page.split('<template id="gate">', 1)[1].split("</template>", 1)[0]

    def test_the_gate_carries_always_only_where_it_is_offered(self):
        self.assertIn('class="always"', self.template)
        self.assertIn("Always for this model", self.template)
        script = self.page.split("function gate(", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("said.always", script)
        self.assertRegex(script, r"'/verdict', \{[^}]*always", "the verdict says it")

    def test_the_page_lists_what_runs_unwatched_with_undo(self):
        self.assertIn('id="unwatched"', self.page)
        self.assertIn("'/asks'", self.page)
        self.assertIn("'/undo'", self.page)


if __name__ == "__main__":
    unittest.main()
