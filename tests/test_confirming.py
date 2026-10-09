"""A command that confirms has one shape (issue 85; ADR 0021, decisions 5 and 6;
ADR 0026, second amendment).

`rename`, `delete`, `update`, `purge` and `restore`, each run as the user runs
it: the first word is the name or id, verbatim; without `--yes` it proposes and
writes nothing; a refusal is `FAIL <command>  <why>`. One table, so a sixth
command that confirms is one row here and not a test file of its own.

Every row gets a fresh fixture: `alpha`, a space made from an older toolkit so
an update has something to do, and `beta`, deleted, so the trash holds a bundle
to restore or purge. A row is walked as a user meets it — refused, a `--yes`
typed as the word, asked, then confirmed — since only the last step writes, and
a fixture per step would cost the suite its time limit. No Blender.
"""
import os
import subprocess
import sys
import time
import unittest
from collections import namedtuple

from test_update import OLD, UpdateCase

Row = namedtuple("Row", "cmd word wrong proposes acted in_space")

ROWS = (
    Row("rename", "gamma", "no/slash", True,
        lambda t: (t.spaces / "gamma").is_dir(), True),
    Row("delete", "alpha", "beta", True,
        lambda t: not t.space.exists(), True),
    Row("update", None, None, True,
        lambda t: f"toolkit: {OLD}" not in (t.space / ".contour" / "project").read_text(), True),
    Row("purge", "ID", "nope", True,
        lambda t: not (t.home / ".contour" / "trash" / f"{t.id}.bundle").exists(), False),
    Row("restore", "ID", "nope", False,
        lambda t: (t.spaces / "beta").is_dir(), False),
)
"""`ID` stands for the bundle the fixture deleted."""


class ConfirmingCase(UpdateCase):

    def setUp(self):
        super().setUp()
        r = self.contour("init", "beta", cwd=self.spaces)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        beta = self.spaces / "beta"
        self.git("add", "-A", cwd=beta)
        self.git("commit", "-qm", "beta", cwd=beta)
        r = self.contour("delete", "beta", "--yes", cwd=beta)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.id = f"beta-{time.strftime('%Y-%m-%d')}"

    def run_row(self, row, *args):
        """The row's command, standing where it stands: in `alpha`, or for the
        trash's two, outside any space."""
        args = [self.id if a == "ID" else a for a in args]
        return self.contour(row.cmd, *args, cwd=self.space if row.in_space else self.tmp)

    def tree(self):
        """Every file under the test's directory, git's own stores aside."""
        return {str(p.relative_to(self.tmp)): p.read_bytes()
                for p in sorted(self.tmp.rglob("*"))
                if p.is_file() and ".git" not in p.relative_to(self.tmp).parts}

    def word(self, row):
        return [row.word] if row.word else []


class ShapeTest(ConfirmingCase):

    def test_every_command_that_confirms_refuses_proposes_then_does_it(self):
        for n, row in enumerate(ROWS):
            with self.subTest(command=row.cmd):
                if n:
                    self.setUp()        # the first row's is unittest's own
                self.refuses(row)
                self.takes_a_typed_yes_for_a_wrong_word(row)
                self.proposes(row)
                self.does_it(row)

    def refuses(self, row):
        """Asked or confirmed, a refusal is `FAIL <command>  <why>`, and nothing
        moves. `update` takes no word, so what it refuses is a space a run holds."""
        record = None
        if row.wrong is None:
            from lib import lock
            record = lock.take(self.space, "contour run claude")
        try:
            before = self.tree()
            for flags in ((), ("--yes",)):
                with self.subTest(step="refused", flags=flags):
                    r = self.run_row(row, *([row.wrong] if row.wrong else []), *flags)
                    self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                    self.assertTrue(r.stdout.startswith(f"FAIL {row.cmd}  "), r.stdout)
                    self.assertEqual(self.tree(), before)
        finally:
            if record:
                lock.release(self.space, record)

    def takes_a_typed_yes_for_a_wrong_word(self, row):
        """What a page sends is whatever was typed, so a typed `--yes` is the
        word, refused as any wrong one is, and never a confirm."""
        if row.word is None:
            return
        with self.subTest(step="typed --yes"):
            before = self.tree()
            r = self.run_row(row, "--yes")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertTrue(r.stdout.startswith(f"FAIL {row.cmd}  "), r.stdout)
            self.assertIn("--yes", r.stdout)
            self.assertEqual(self.tree(), before)

    def proposes(self, row):
        """Without `--yes`, a proposal that names it, and nothing written.
        `restore` has no proposal: it acts on its own word, as it always has."""
        if not row.proposes:
            return
        with self.subTest(step="proposed"):
            before = self.tree()
            r = self.run_row(row, *self.word(row))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(self.tree(), before)
            self.assertIn(f"contour {row.cmd}", r.stdout)
            self.assertIn("--yes", r.stdout)
            self.assertFalse(row.acted(self))

    def does_it(self, row):
        with self.subTest(step="done"):
            r = self.run_row(row, *self.word(row), "--yes")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(r.stdout.startswith(("ok   ", "update ")), r.stdout)
            self.assertTrue(row.acted(self))


class UpdateTest(ConfirmingCase):

    def test_dry_run_is_gone(self):
        """Proposing is the default now (ADR 0026, second amendment)."""
        before = self.tree()
        r = self.contour("update", "--dry-run")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertEqual(self.tree(), before)


if __name__ == "__main__":
    unittest.main()
