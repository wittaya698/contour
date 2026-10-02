"""`contour delete`: a deleted space leaves a bundle (ADR 0021, decisions 6, 7
and 8; issue 34).

Run as the user runs it — `contour delete` spawned in a throwaway space that
`contour init` made, with `$HOME` and `$CONTOUR_HOME` inside the test so the
trash it writes is the test's own. No Blender.
"""
import hashlib
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from test_rename import RenameCase

from lib import delete    # noqa: E402


class DeleteCase(RenameCase):

    def setUp(self):
        super().setUp()
        (self.space / "refs" / "front.png").write_bytes(bytes(range(256)) * 40)
        self.git("add", "-A")
        self.git("commit", "-qm", "a reference")

    def trash(self):
        """Where the command writes its bundles, asked of the module under the
        test's own `$CONTOUR_HOME`."""
        with mock.patch.dict(os.environ, CONTOUR_HOME=self.env["CONTOUR_HOME"]):
            return delete.trash()

    def delete(self, *args):
        r = self.contour("delete", *args, "--json")
        return r.returncode, json.loads(r.stdout)

    def tracked(self, root):
        """Every tracked file under `root` and the checksum of what it holds."""
        names = self.git("ls-files", cwd=root).split("\n")
        return {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in names if n}


class ProposalTest(DeleteCase):

    def test_without_the_confirming_flag_it_proposes_and_changes_nothing(self):
        before = self.snapshot(self.tmp)
        r = self.contour("delete", "alpha")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.snapshot(self.tmp), before)
        for line in (str(self.space), str(self.trash()), "bundle", "same disk",
                     "cannot see a terminal agent session", "contour delete alpha --yes"):
            self.assertIn(line, r.stdout)

    def test_a_client_reads_the_same_proposal(self):
        """For the lobby, which shows it above a box the name is typed into."""
        code, said = self.delete("alpha")
        self.assertEqual(code, 0)
        self.assertEqual((said["path"], said["name"], said["refused"]),
                         (str(self.space), "alpha", None))
        self.assertTrue(said["bundle"].startswith(str(self.trash())))
        self.assertIn("same disk", said["disk"])
        self.assertIn("terminal agent session", said["unseen"])

    def test_a_refusal_is_said_before_anything_is_confirmed(self):
        (self.space / "notes.txt").write_text("unsaved")
        code, said = self.delete("alpha")
        self.assertEqual(code, 1)
        self.assertIn("notes.txt", said["refused"])


class DeleteTest(DeleteCase):

    def test_a_deleted_space_leaves_a_bundle_that_clones_to_the_same_tree(self):
        before = self.tracked(self.space)
        code, said = self.delete("alpha", "--yes")
        self.assertEqual(code, 0, said)
        self.assertIsNone(said["refused"])
        self.assertFalse(self.space.exists())
        bundles = list(self.trash().glob("alpha-*.bundle"))
        self.assertEqual([str(b) for b in bundles], [said["bundle"]])
        back = self.tmp / "restored"
        subprocess.run(["git", "clone", "-q", str(bundles[0]), str(back)],
                       env=self.env, check=True, capture_output=True)
        self.assertEqual(self.tracked(back), before)
        self.assertIn("refs/front.png", before)

    def test_a_deleted_space_never_lists_as_live(self):
        """Not even where the scan is told to look in the trash itself."""
        self.delete("alpha", "--yes")
        self.env["CONTOUR_SPACES"] = f"{self.spaces}:{self.home}:{self.trash()}"
        said = json.loads(self.contour("spaces", "--json", cwd=self.tmp).stdout)
        self.assertEqual(said["spaces"], [])

    def test_two_deletes_of_one_name_on_one_day_keep_both_bundles(self):
        self.delete("alpha", "--yes")
        r = self.contour("init", "alpha", cwd=self.spaces)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.git("add", "-A")
        self.git("commit", "-qm", "alpha again")
        code, said = self.delete("alpha", "--yes")
        self.assertEqual(code, 0, said)
        self.assertEqual(len(list(self.trash().glob("alpha-*.bundle"))), 2)


class NoBundleTest(DeleteCase):
    """The space goes only once its bundle is written and proved."""

    def untouched(self):
        before = self.snapshot(self.space)
        code, said = self.delete("alpha", "--yes")
        self.assertEqual(code, 1, said)
        self.assertIn("nothing was deleted", said["refused"])
        self.assertEqual(self.snapshot(self.space), before)
        return said

    def test_a_bundle_that_cannot_be_written_deletes_nothing(self):
        for blocked in ("a file where the trash goes", "a trash nobody may write in"):
            with self.subTest(blocked):
                if self.trash().is_dir():
                    self.trash().chmod(0o755)
                    self.trash().rmdir()
                if blocked.startswith("a file"):
                    self.trash().write_text("")
                else:
                    self.trash().unlink(missing_ok=True)
                    self.trash().mkdir()
                    self.trash().chmod(0o555)
                    self.addCleanup(self.trash().chmod, 0o755)
                self.untouched()

    def test_a_bundle_that_does_not_verify_deletes_nothing(self):
        """A `git` ahead of the real one on `$PATH` truncates every bundle it
        is asked to create, as a full disk would, so the write succeeds and
        the proof fails."""
        shim = self.tmp / "bin"
        shim.mkdir()
        real = shutil.which("git")
        (shim / "git").write_text(
            "#!/bin/sh\n"
            f'"{real}" "$@" || exit $?\n'
            'case "$*" in *"bundle create"*) for a; do case "$a" in *.bundle) '
            ': > "$a";; esac; done;; esac\n')
        (shim / "git").chmod(0o755)
        self.env["PATH"] = f"{shim}:{self.env['PATH']}"
        self.untouched()
        self.assertEqual(list(self.trash().glob("*")), [])

    def test_a_space_that_will_not_come_away_says_where_its_bundle_is(self):
        """The bundle is proved before anything is removed, so a removal that
        stops partway has lost nothing committed, and says so."""
        (self.space / "refs").chmod(0o555)
        self.addCleanup((self.space / "refs").chmod, 0o755)
        code, said = self.delete("alpha", "--yes")
        self.assertEqual(code, 1, said)
        self.assertIn("stopped partway", said["refused"])
        self.assertIn(said["bundle"], said["refused"])
        self.assertTrue(Path(said["bundle"]).is_file())


class RefusalTest(DeleteCase):
    """Each refusal names its reason, and leaves the space as it was and the
    trash empty."""

    def refused(self, *args):
        before = self.snapshot(self.space)
        code, said = self.delete(*args, "--yes")
        self.assertEqual(code, 1, said)
        self.assertEqual(self.snapshot(self.space), before)
        self.assertEqual(list(self.trash().glob("*")) if self.trash().exists() else [], [])
        return said["refused"]

    def test_a_confirm_that_is_not_this_space_s_name_deletes_nothing(self):
        self.assertIn("type alpha", self.refused("beta"))

    def test_uncommitted_changes_are_refused_and_listed(self):
        (self.space / "spec.yaml").write_text("model: alpha\nrevision: 3\n")
        (self.space / "refs" / "side.png").write_bytes(b"new")
        said = self.refused("alpha")
        self.assertIn("uncommitted", said)
        self.assertIn("spec.yaml", said)
        self.assertIn("refs/side.png", said)

    def test_a_working_file_is_refused_though_git_ignores_it(self):
        (self.space / "work").mkdir()
        (self.space / "work" / "scene.blend").write_bytes(b"yours")
        said = self.refused("alpha")
        self.assertIn("work/scene.blend", said)

    def test_a_space_held_by_a_run_is_refused(self):
        from lib import lock
        record = lock.take(self.space, "contour run claude")
        self.addCleanup(lock.release, self.space, record)
        self.assertIn("held by pid", self.refused("alpha"))

    def test_a_space_with_a_page_open_on_it_is_refused(self):
        from lib import presence
        self.enterContext(presence.present(self.space, "canvas"))
        said = self.refused("alpha")
        self.assertIn("canvas", said)
        self.assertIn("close it", said)


if __name__ == "__main__":
    unittest.main()
