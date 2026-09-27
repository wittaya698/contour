"""The ask-list: which calls run unwatched, and everything else asks.

ADR 0019, decisions 6, 7, 10 and 30. These drive the reader the way the
console's gate will — a category from `lib.intent` and the space the agent is
working in — and they always pass the file explicitly, because the point of the
thing living in `~/.contour` is that no test and no agent has to go looking for
it where the real one is.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import intent, policy


class ResolveTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())

    def file(self, text):
        """An ask-list on disk, as the user hand-writes one."""
        path = self.home / "ask-list.yaml"
        path.write_text(text)
        return path

    def test_a_category_the_file_does_not_name_is_gated(self):
        """The whole posture in one assertion: the file names what runs
        unwatched, and a category it is silent about asks. A list of what to
        *gate* fails the other way — a category forgotten runs unwatched."""
        file = self.file("allow:\n  - build\n")
        self.assertFalse(policy.gated("build", None, file=file))
        self.assertTrue(policy.gated("push", None, file=file))

    def test_a_space_the_file_never_names_lets_nothing_through(self):
        """Not the global default: a space has no identity today, so the key is
        its path, and a moved or renamed space would otherwise inherit
        permissions nobody granted it. Fail-closed turns that into the console
        asking about more than expected, which is annoying in the right
        direction."""
        file = self.file("allow:\n  - build\n")
        stranger = self.home / "beaky"
        self.assertEqual(policy.allowed(stranger, file=file), ())
        self.assertTrue(policy.gated("build", stranger, file=file))

    def test_a_spaces_own_list_replaces_the_global_one(self):
        """Merging two permission lists can silently *narrow* the result, and an
        override that reads as adding a rule can shadow one invisibly in both
        files. So `build` does not survive into a space that did not say it."""
        space = self.home / "beaky"
        file = self.file(f"allow:\n  - build\nspaces:\n"
                         f"  {space}:\n    allow:\n      - spec-write\n")
        self.assertEqual(policy.allowed(space, file=file), ("spec-write",))

    def test_a_space_that_names_no_list_of_its_own_takes_the_global_one(self):
        """The level that gives the global default something to govern. Naming
        the path is the recognition; the list beside it is the override. A space
        listed and left silent is the user saying *the usual*, which is a
        decision they made, unlike the space they never mentioned."""
        space = self.home / "beaky"
        file = self.file(f"allow:\n  - build\nspaces:\n  {space}:\n")
        self.assertEqual(policy.allowed(space, file=file), ("build",))

    def test_no_file_at_all_lets_nothing_through(self):
        """The first run, before anyone has written a line: silence taken to its
        limit, so the console asks about everything and is tuned downward from
        there. Not a crash — a fresh install has no ask-list and that is a
        state, not a fault."""
        missing = self.home / "ask-list.yaml"
        self.assertEqual(policy.allowed(None, file=missing), ())
        self.assertTrue(policy.gated("build", None, file=missing))

    def test_an_unreadable_file_says_which_file_and_never_resolves_a_list(self):
        """Empty is a list the user could have chosen on purpose, so it must not
        double as *I could not read your policy*. The distinction is the type:
        there is no resolved list at all, and the message names the file because
        it reaches a person who has to go and fix it."""
        file = self.file("allow:\n\t- build\n")
        for call in (lambda: policy.allowed(None, file=file),
                     lambda: policy.gated("push", None, file=file)):
            with self.assertRaises(policy.PolicyError) as caught:
                call()
            self.assertIn(str(file), str(caught.exception))

    def test_an_empty_list_is_not_the_same_as_no_list(self):
        """`allow: []` is a released model, deliberately letting nothing
        through; a bare key is the user saying *the usual*. Reading both as
        falsy collapses them, and it collapses in the widening direction — the
        strict space quietly inherits the global list."""
        space = self.home / "beaky"
        file = self.file(f"allow:\n  - build\nspaces:\n"
                         f"  {space}:\n    allow: []\n")
        self.assertEqual(policy.allowed(space, file=file), ())

    def test_a_key_naming_the_same_directory_another_way_is_the_same_space(self):
        """The launcher resolves the space it walks up to, and the user writes
        the path their shell shows them; on this machine those differ by a
        symlink. Matched as strings, the entry silently governs nothing — which
        is fail-closed, and also indistinguishable from a typo, so the user
        tunes a list that was never being read."""
        space = self.home / "beaky"
        space.mkdir()
        file = self.file(f"spaces:\n  {space}:\n    allow:\n      - build\n")
        self.assertEqual(policy.allowed(space.resolve(), file=file), ("build",))

    def test_a_key_written_with_a_tilde_names_the_users_home(self):
        """How anyone actually writes a path into a config file by hand. `~` is
        the shell's, not the filesystem's, so a reader that only normalises
        symlinks turns the most natural spelling into a line that governs
        nothing."""
        space = Path.home() / ".contour-test-space"
        file = self.file("spaces:\n  ~/.contour-test-space:\n    allow:\n"
                         "      - build\n")
        self.assertEqual(policy.allowed(space, file=file), ("build",))

    def test_a_name_the_toolkit_no_longer_knows_is_reported(self):
        """The file is meaningful only against the current set of categories, so
        a name that has been renamed or retired is the one case where the user's
        intent is on file and unreachable. Silently honouring it is impossible
        and silently dropping it is how a permission the user believes they
        granted stops existing without anyone saying so."""
        file = self.file("allow:\n  - build\n  - telemetry\n")
        said = " ".join(policy.report(None, file=file))
        self.assertIn("telemetry", said)
        self.assertNotIn("telemetry", policy.allowed(None, file=file))

    def test_the_report_gives_a_verdict_for_every_category_the_toolkit_knows(self):
        """Auditing is comparing the file against the whole vocabulary, so the
        report prints a verdict per category rather than only what was allowed:
        a list of allowances cannot show what is being watched, and *what is
        being watched* is the thing the user is checking."""
        space = self.home / "beaky"
        file = self.file(f"allow:\n  - build\nspaces:\n"
                         f"  {space}:\n    allow:\n      - spec-write\n")
        lines = policy.report(space, file=file)
        verdict = {words[1]: words[0] for words in map(str.split, lines)
                   if len(words) == 2 and words[0] in ("allow", "ask")}
        self.assertEqual(set(verdict), set(intent.categories()))
        self.assertEqual(verdict["spec-write"], "allow")
        self.assertEqual(verdict["build"], "ask")
        self.assertIn(str(space), "\n".join(lines))


class AsksTest(unittest.TestCase):
    """`contour asks` is the other half of `contour intents`: one prints what
    the toolkit knows, the other what this space lets through, and the audit is
    reading them side by side."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp())

    def asks(self, body=None, cwd=None):
        if body is not None:
            (self.home / "ask-list.yaml").write_text(body)
        return subprocess.run([sys.executable, str(ROOT / "contour"), "asks"],
                              cwd=str(cwd or ROOT), capture_output=True,
                              text=True, timeout=60,
                              env=dict(os.environ, CONTOUR_HOME=str(self.home),
                                       BLENDER="/nowhere/blender"))

    def test_the_launcher_prints_the_resolved_list_with_no_blender(self):
        """The user runs this to see what they have actually granted, before a
        session and without a space; a Blender run for a policy question would
        make the audit cost a minute."""
        r = self.asks("allow:\n  - build\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        verdict = {w[1]: w[0] for w in map(str.split, r.stdout.splitlines())
                   if len(w) == 2 and w[0] in ("allow", "ask")}
        self.assertEqual(set(verdict), set(intent.categories()))
        self.assertEqual(verdict["build"], "allow")
        self.assertEqual(verdict["push"], "ask")

    def test_the_report_names_the_file_it_read(self):
        """An audit that does not say which file it read cannot be acted on:
        the user has to know where to go and change it, and `~/.contour` is a
        directory nothing else in the toolkit has ever mentioned."""
        r = self.asks("allow:\n  - build\n")
        self.assertIn(str(self.home / "ask-list.yaml"), r.stdout)

    def test_an_unreadable_file_stops_the_command_and_names_it(self):
        """The audit's own fail-closed case. A reader that printed `ask spec-write`
        five times over a file it could not parse would look exactly like a
        correctly strict one, and the user would go on believing they had a
        policy."""
        r = self.asks("allow:\n\t- build\n")
        self.assertNotEqual(r.returncode, 0)
        said = r.stdout + r.stderr
        self.assertIn(str(self.home / "ask-list.yaml"), said)
        self.assertNotIn("allow ", said)
        self.assertNotIn("Traceback", said)   # a message, not a stack trace

    def test_with_no_file_written_everything_asks(self):
        r = self.asks()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("allow ", r.stdout)

    def test_a_policy_file_planted_in_a_space_or_the_toolkit_is_not_read(self):
        """The reason the list lives in `~/.contour` at all. An agent with Bash
        can write any path, so this does not make tampering impossible — it
        makes it stop being a plausible edit, because there is no file inside
        the space or the toolkit that widening the list could be spelled as.
        """
        space = self.home / "beaky"
        (space / ".contour").mkdir(parents=True)
        (space / ".contour" / "project").write_text("toolkit: contour\n")
        every = "".join(f"  - {c}\n" for c in intent.categories())
        wide = (f"allow:\n{every}spaces:\n  {space}:\n    allow:\n"
                + every.replace("  - ", "      - "))
        empty = Path(tempfile.mkdtemp())
        for at in (space, space / ".contour", ROOT):
            planted = at / "ask-list.yaml"
            planted.write_text(wide)
            self.addCleanup(planted.unlink, missing_ok=True)
        r = subprocess.run([sys.executable, str(ROOT / "contour"), "asks"],
                           cwd=str(space), capture_output=True, text=True,
                           timeout=60,
                           env=dict(os.environ, CONTOUR_HOME=str(empty),
                                    BLENDER="/nowhere/blender"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(str(space), r.stdout)
        self.assertNotIn("allow ", r.stdout)


if __name__ == "__main__":
    unittest.main()
