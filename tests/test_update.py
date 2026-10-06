"""`contour update`: a space's copies brought in step, where nobody edited them
(ADR 0026, decisions 1, 3, 4 and 5; issue 80).

Run as the user runs it, in a throwaway space `contour init` made. The space is
then made *behind*: its marker names an older toolkit commit, the last one
before the template's `CLAUDE.md` last changed, and its copies are that
commit's — read from the toolkit's own history, as update reads them. No
Blender.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTOUR = ROOT / "contour"
sys.path.insert(0, str(ROOT))

from lib import space as space_lib, update     # noqa: E402

RULES = "CLAUDE.md"
SETTINGS = ".claude/settings.json"


def toolkit_git(*args):
    """Unstripped: a template is compared byte for byte."""
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                          text=True, check=True).stdout


OLD = toolkit_git("rev-parse", "--short", toolkit_git(
    "log", "-1", "--format=%h", "--", f"templates/space/{RULES}").strip() + "^").strip()
"""A toolkit commit whose template `CLAUDE.md` is not today's."""


def then(rel, name):
    """What the template wrote at `rel` for `name` at the old commit."""
    return toolkit_git("show", f"{OLD}:templates/space/{rel}").replace("<NAME>", name)


class UpdateCase(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.spaces = self.tmp / "spaces"
        self.spaces.mkdir()
        self.home = self.tmp / "home"
        (self.home / ".contour").mkdir(parents=True)
        self.env = dict(os.environ, CONTOUR_SPACES=str(self.spaces),
                        CONTOUR_HOME=str(self.home / ".contour"), HOME=str(self.home),
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        r = self.contour("init", "alpha", cwd=self.spaces)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.space = self.spaces / "alpha"
        self.behind(self.space, OLD)
        (self.space / "spec.yaml").write_text("model: alpha\nrevision: 1\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "alpha")

    def behind(self, space, commit):
        """Make `space` one made from `commit`: its marker and its copies."""
        marker = space / ".contour" / "project"
        marker.write_text("".join(f"toolkit: {commit}\n" if l.startswith("toolkit:") else l
                                  for l in marker.read_text().splitlines(keepends=True)))
        for rel in space_lib.SCAFFOLD:
            (space / rel).write_text(then(rel, space.name))

    def contour(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(CONTOUR), *args],
                              cwd=str(cwd or self.space), env=self.env,
                              capture_output=True, text=True, timeout=60)

    def git(self, *args, cwd=None):
        return subprocess.run(["git", "-C", str(cwd or self.space), *args], env=self.env,
                              capture_output=True, text=True, check=True).stdout

    def json(self, *flags, cwd=None):
        r = self.contour("update", *flags, "--json", cwd=cwd)
        return json.loads(r.stdout)

    def snapshot(self):
        """Every file in the space and what it holds, git's own store aside."""
        return {str(p.relative_to(self.space)): p.read_bytes()
                for p in sorted(self.space.rglob("*"))
                if p.is_file() and ".git" not in p.relative_to(self.space).parts}

    def toolkit_head(self):
        return toolkit_git("rev-parse", "--short", "HEAD").strip()

    def now(self, rel, name="alpha"):
        return space_lib.template(ROOT, rel, name)


class UpdateTest(UpdateCase):

    def test_an_untouched_file_is_replaced_and_an_edited_one_is_named_and_left(self):
        self.assertNotEqual(then(RULES, "alpha"), self.now(RULES))
        edited = then(SETTINGS, "alpha") + "\n"
        (self.space / SETTINGS).write_text(edited)
        r = self.contour("update")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.space / RULES).read_text(), self.now(RULES))
        self.assertEqual((self.space / SETTINGS).read_text(), edited)
        self.assertIn(SETTINGS, r.stdout)
        self.assertIn("edited", r.stdout)

    def test_a_renamed_spaces_untouched_files_count_as_untouched(self):
        """Compared under the name `rename` rewrote them to."""
        r = self.contour("rename", "beta", "--yes")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        beta = self.spaces / "beta"
        self.assertEqual((beta / RULES).read_text(), then(RULES, "beta"))
        r = self.contour("update", cwd=beta)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((beta / RULES).read_text(), self.now(RULES, "beta"))
        self.assertIn(RULES, r.stdout)
        self.assertEqual(self.json("--dry-run", cwd=beta)["left"], [])

    def test_a_recorded_commit_missing_from_history_overwrites_nothing(self):
        """A rewritten history, or a space from another machine: nothing to tell
        an edit from, so every differing file counts as one."""
        self.behind(self.space, "0" * 40)
        before = {rel: (self.space / rel).read_text() for rel in space_lib.SCAFFOLD}
        said = self.json()
        self.assertIsNone(said["refused"])
        self.assertEqual(said["replaced"], [])
        self.assertIn(RULES, [l["what"] for l in said["left"]])
        self.assertIn("not in this toolkit's history", said["left"][0]["why"])
        self.assertEqual({rel: (self.space / rel).read_text() for rel in space_lib.SCAFFOLD},
                         before)


    def test_a_missing_file_is_written(self):
        recipes = ".claude/skills/build-model/references/bpy-recipes.md"
        (self.space / recipes).unlink()
        r = self.contour("update")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.space / recipes).read_text(), self.now(recipes))
        self.assertIn("written", r.stdout)

    def test_a_dry_run_changes_nothing_and_says_what_it_would(self):
        before = self.snapshot()
        r = self.contour("update", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertIn(RULES, r.stdout)
        self.assertIn("nothing changed", r.stdout)
        moved_on = [rel for rel in space_lib.SCAFFOLD if then(rel, "alpha") != self.now(rel)]
        self.assertIn(RULES, moved_on)
        self.assertEqual(self.json("--dry-run")["replaced"], moved_on)

    def test_doctor_finds_the_space_in_step_but_for_what_was_left(self):
        (self.space / SETTINGS).write_text(then(SETTINGS, "alpha") + "\n")
        self.assertEqual(self.contour("update").returncode, 0)
        said = self.contour("doctor").stdout
        self.assertEqual([l for l in said.splitlines() if l.startswith(("DRIFT", "MISS"))],
                         [f"DRIFT {SETTINGS} — differs from the toolkit's template"])
        self.assertIn(f"ok   toolkit {self.toolkit_head()}", said)

    def test_doctor_points_a_space_behind_at_update(self):
        self.assertIn("run contour update", self.contour("doctor").stdout)

    def test_it_leaves_its_changes_unsaved(self):
        self.assertEqual(self.contour("update").returncode, 0)
        self.assertIn(RULES, self.git("status", "--porcelain"))
        self.assertEqual(self.git("log", "--format=%s").split(), ["alpha"])


class WrittenFromTest(unittest.TestCase):
    """An unedited copy is the template written for one name, whichever."""

    TEMPLATE = "# <NAME>\nexports/<NAME>.glb\n"

    def test_one_name_throughout_is_unedited(self):
        self.assertTrue(update.written_from("# beaky\nexports/beaky.glb\n", self.TEMPLATE))

    def test_two_names_is_an_edit(self):
        self.assertFalse(update.written_from("# beta\nexports/alpha.glb\n", self.TEMPLATE))

    def test_a_template_without_a_name_is_compared_as_it_is(self):
        self.assertTrue(update.written_from("{}\n", "{}\n"))
        self.assertFalse(update.written_from("{ }\n", "{}\n"))


class RefusalTest(UpdateCase):
    """Where a rename refuses, worded as rename words it (ADR 0026, decision 3),
    and with every file where it was, under the dry run and without it."""

    def refused(self, *reason):
        before = self.snapshot()
        for flags in ((), ("--dry-run",)):
            with self.subTest(flags=flags):
                r = self.contour("update", *flags)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                for word in reason:
                    self.assertIn(word, r.stdout)
                self.assertEqual(self.snapshot(), before)

    def test_a_space_held_by_a_run_is_not_updated(self):
        from lib import lock
        record = lock.take(self.space, "contour run claude")
        self.addCleanup(lock.release, self.space, record)
        self.refused("held by", f"pid {os.getpid()}", "contour run claude",
                     "update it once that run ends")

    def test_a_space_a_page_is_open_on_is_not_updated(self):
        from lib import presence
        with presence.present(self.space, "console"):
            self.refused("console", "open", f"pid {os.getpid()}", "close it, then update")


if __name__ == "__main__":
    unittest.main()
