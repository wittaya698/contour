"""`contour rename`: it proposes, then does the rename (ADR 0021, decisions 5,
7 and 8; issue 31).

Run as the user runs it — `contour rename` spawned in a throwaway space that
`contour init` made, with `$HOME` and `$CONTOUR_HOME` pointed inside the test so
the transcripts and the ask-list it names are the test's own. No Blender.
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

from lib import rename     # noqa: E402

SPEC = "model: alpha\nrevision: 2\ndescription: a test model\n"


class RenameCase(unittest.TestCase):

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
        (self.space / "spec.yaml").write_text(SPEC)
        self.git("add", "-A")
        self.git("commit", "-qm", "alpha")

    def contour(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(CONTOUR), *args],
                              cwd=str(cwd or self.space), env=self.env,
                              capture_output=True, text=True, timeout=60)

    def git(self, *args, cwd=None):
        return subprocess.run(["git", "-C", str(cwd or self.space), *args], env=self.env,
                              capture_output=True, text=True, check=True).stdout

    def snapshot(self, root):
        """Every file under `root` and what it holds, git's own store aside."""
        return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*"))
                if p.is_file() and ".git" not in p.relative_to(root).parts}

    def leave_behind(self):
        """An ask-list entry and a transcript directory, both keyed on the path."""
        (self.home / ".contour" / "ask-list.yaml").write_text(
            f"spaces:\n  {self.space}:\n    allow: [build]\n")
        slug = "-" + str(self.space).lstrip("/").replace("/", "-")
        (self.home / ".claude" / "projects" / slug).mkdir(parents=True)


class ProposalTest(RenameCase):

    def test_without_the_confirming_flag_it_proposes_and_changes_nothing(self):
        self.leave_behind()
        before = self.snapshot(self.spaces)
        r = self.contour("rename", "beta")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.snapshot(self.spaces), before)
        said = r.stdout
        for line in (str(self.space), str(self.spaces / "beta"),
                     "model:", "alpha -> beta", "revision:", "2 -> 3", "CLAUDE.md",
                     "ask-list", "transcripts", "spend",
                     "cannot see a terminal agent session"):
            self.assertIn(line, said)

    def json(self, *args):
        r = self.contour("rename", *args, "--json")
        return r.returncode, json.loads(r.stdout)

    def test_the_lobby_reads_the_same_proposal(self):
        """For slice 32, which shows it as a diff and confirms it as a click."""
        self.leave_behind()
        code, said = self.json("beta")
        self.assertEqual(code, 0)
        self.assertEqual((said["from"], said["to"], said["refused"]),
                         (str(self.space), str(self.spaces / "beta"), None))
        changes = {c["what"]: (c["from"], c["to"]) for c in said["changes"]}
        self.assertEqual(changes["directory"], (str(self.space), str(self.spaces / "beta")))
        self.assertEqual(changes["model:"], ("alpha", "beta"))
        self.assertEqual(changes["revision:"], (2, 3))
        self.assertEqual(changes["CLAUDE.md"], ("alpha", "beta"))
        self.assertEqual([l["what"] for l in said["leaves"]], ["ask-list", "transcripts"])
        self.assertIn("terminal agent session", said["unseen"])

    def test_what_is_not_there_is_not_said_to_be_left_behind(self):
        """An ask-list that names only other spaces has nothing of this one's to
        orphan, and a space nobody ran Claude Code in has no transcripts."""
        (self.home / ".contour" / "ask-list.yaml").write_text(
            f"spaces:\n  {self.spaces / 'other'}:\n    allow: [build]\n")
        self.assertEqual(self.json("beta")[1]["leaves"], [])

    def test_a_refusal_reads_as_one(self):
        code, said = self.json("be ta")
        self.assertEqual(code, 1)
        self.assertIn("not a name", said["refused"])


class PerformTest(RenameCase):

    def test_with_the_confirming_flag_every_part_carries_the_new_name(self):
        r = self.contour("rename", "beta", "--yes")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        beta = self.spaces / "beta"
        self.assertFalse(self.space.exists())
        spec = (beta / "spec.yaml").read_text()
        self.assertIn("model: beta\n", spec)
        self.assertIn("revision: 3\n", spec)
        self.assertTrue((beta / "CLAUDE.md").read_text().startswith("# beta — "))
        self.assertIn(f"cd {beta}", r.stdout)

    def test_nothing_is_committed(self):
        """Rule 5: the rename is shown to the user as uncommitted change, and
        reaches history only through their next approved commit."""
        head = self.git("rev-parse", "HEAD")
        self.contour("rename", "beta", "--yes")
        beta = self.spaces / "beta"
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=beta), head)
        self.assertIn("spec.yaml", self.git("status", "--porcelain", cwd=beta))

    def test_the_renamed_space_is_not_left_held(self):
        """The hold moves with the directory, and is let go of there."""
        from lib import lock
        self.contour("rename", "beta", "--yes")
        self.assertIsNone(lock.holder(self.spaces / "beta"))

    def revision_check(self, space):
        """What `contour check` says about the revision. `$BLENDER` points
        nowhere: the revision check runs before Blender is asked for."""
        r = subprocess.run([sys.executable, str(CONTOUR), "check"], cwd=str(space),
                           env=dict(self.env, BLENDER="/nowhere/blender"),
                           capture_output=True, text=True, timeout=60)
        self.assertIn("no Blender at", r.stdout, r.stdout + r.stderr)   # it got past
        return [l for l in r.stdout.splitlines() if "revision" in l]

    def test_the_renamed_space_passes_its_revision_check(self):
        self.contour("rename", "beta", "--yes")
        self.assertEqual(self.revision_check(self.spaces / "beta"), [])

    def test_an_already_confirmed_spec_change_is_bumped_past_too(self):
        """HEAD says 2 and the file, confirmed and not yet committed, says 3:
        the rename writes 4, not 3 again."""
        (self.space / "spec.yaml").write_text(SPEC.replace("revision: 2", "revision: 3")
                                              + "notes: confirmed\n")
        self.contour("rename", "beta", "--yes")
        beta = self.spaces / "beta"
        self.assertIn("revision: 4\n", (beta / "spec.yaml").read_text())
        self.assertIn("notes: confirmed\n", (beta / "spec.yaml").read_text())
        self.assertEqual(self.revision_check(beta), [])

    def test_doctor_finds_no_drift_from_the_rename(self):
        """Every scaffold file carries the name, the skills included, so a
        rename that only rewrote `CLAUDE.md` would read as drift."""
        self.contour("rename", "beta", "--yes")
        said = self.contour("doctor", cwd=self.spaces / "beta").stdout
        self.assertIn("ok   CLAUDE.md", said)
        self.assertNotIn("DRIFT", said)
        self.assertNotIn("MISS", said)

    def test_a_drifted_claude_md_still_has_its_header_renamed(self):
        """The user's own rules below the header are theirs and stay; the
        header is the name, and is the rename's."""
        claude = self.space / "CLAUDE.md"
        claude.write_text(claude.read_text() + "\n## Mine\n\nKeep the beak short.\n")
        self.assertIn("CLAUDE.md", self.contour("rename", "beta").stdout)
        self.contour("rename", "beta", "--yes")
        now = (self.spaces / "beta" / "CLAUDE.md").read_text()
        self.assertTrue(now.startswith("# beta — agent operating rules\n"))
        self.assertIn("Keep the beak short.", now)

    def test_a_drifted_file_whose_header_carries_no_name_is_not_offered(self):
        """A skill opens with `---`, which no rename changes; offering its
        header would list a change that writes nothing. It is the user's
        drift, and stays theirs to settle with `contour doctor`."""
        skill = self.space / ".claude" / "skills" / "build-model" / "SKILL.md"
        skill.write_text(skill.read_text() + "\nMine.\n")
        said = json.loads(self.contour("rename", "beta", "--json").stdout)
        changes = [c["what"] for c in said["changes"]]
        self.assertNotIn(".claude/skills/build-model/SKILL.md", changes)
        self.assertIn("CLAUDE.md", changes)
        self.assertEqual(said["untouched"], [".claude/skills/build-model/SKILL.md"])
        self.assertIn("untouched", self.contour("rename", "beta").stdout)


class RefusalTest(RenameCase):
    """Each refusal names its reason, in the proposal and under the confirming
    flag alike, and leaves every file where it was."""

    def refused(self, name, *reason):
        before = self.snapshot(self.spaces)
        for flags in ((), ("--yes",)):
            with self.subTest(flags=flags):
                r = self.contour("rename", name, *flags)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                for word in reason:
                    self.assertIn(word, r.stdout + r.stderr)
                self.assertEqual(self.snapshot(self.spaces), before)

    def test_a_space_held_by_a_run_is_not_renamed(self):
        from lib import lock
        record = lock.take(self.space, "contour run claude")
        self.addCleanup(lock.release, self.space, record)
        self.refused("beta", "held by", f"pid {os.getpid()}", "contour run claude")

    def test_a_space_a_page_is_open_on_is_not_renamed(self):
        """An idle console holds nothing, so only its presence says it would be
        left writing to a path that no longer exists."""
        from lib import presence
        with presence.present(self.space, "console"):
            self.refused("beta", "console", "open", f"pid {os.getpid()}")

    def test_a_name_already_taken_is_refused(self):
        """Taken by anything at all: an empty directory is as much in the way
        as another space, and `rename(2)` would quietly replace an empty one."""
        (self.spaces / "beta").mkdir()
        self.refused("beta", "beta", "already exists")

    def test_an_unconfirmed_spec_change_is_not_carried_past_its_check(self):
        """The spec differs from HEAD and nobody bumped it, so `contour check`
        is red. The rename's own bump would turn it green, and a change nobody
        confirmed would pass as one somebody did (rules 1 and 2)."""
        (self.space / "spec.yaml").write_text(SPEC + "notes: nobody confirmed this\n")
        self.refused("beta", "spec.yaml differs from HEAD", "revision still 2")

    def test_a_rename_that_fails_partway_leaves_the_old_space_whole(self):
        """The directory cannot move — its parent is read-only — after the spec
        and the scaffolding were already rewritten. They are put back: never a
        directory whose name disagrees with its spec."""
        before = self.snapshot(self.spaces)
        self.spaces.chmod(0o555)
        self.addCleanup(self.spaces.chmod, 0o755)
        r = self.contour("rename", "beta", "--yes")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("FAIL", r.stdout)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self.snapshot(self.spaces), before)

    def test_an_illegal_name_is_refused(self):
        for name in ("../beta", "be ta", ".beta", "be.ta", "-beta", "b" * 65, "alpha"):
            with self.subTest(name=name):
                self.refused(name, "not a name", name)



class RespelledTest(unittest.TestCase):
    """The spec under its new name, one revision on, for the specs the four
    spaces on this machine actually have."""

    def test_a_spec_from_before_revisions_gains_its_first(self):
        """`beaky`'s spec has no `revision:`: it is revision 0, so this is 1."""
        self.assertEqual(rename.respelled("model: beaky\ndescription: x\n", "kiwi"),
                         "model: kiwi\nrevision: 1\ndescription: x\n")

    def test_only_the_fields_move(self):
        """The same words further down, in a block scalar, are the user's prose."""
        text = "notes: |\n  model: beaky\n  revision: 9\nmodel: beaky\nrevision: 3\n"
        self.assertEqual(rename.respelled(text, "kiwi"),
                         "notes: |\n  model: beaky\n  revision: 9\nmodel: kiwi\nrevision: 4\n")


if __name__ == "__main__":
    unittest.main()
