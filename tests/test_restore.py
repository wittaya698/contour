"""`contour restore`: a deleted space comes back from its bundle (ADR 0021,
decision 6; issue 35).

Run as the user runs it — a throwaway space deleted with `contour delete`, then
restored from outside any space, with `$HOME` and `$CONTOUR_HOME` inside the
test. No Blender.
"""
import json
import os
import subprocess
import time
import unittest
from unittest import mock

from test_delete import DeleteCase
from test_rename import CONTOUR

from lib import restore    # noqa: E402


class RestoreCase(DeleteCase):

    def setUp(self):
        super().setUp()
        self.before = self.tracked(self.space)
        code, said = self.delete("alpha", "--yes")
        self.assertEqual(code, 0, said)
        self.id = f"alpha-{time.strftime('%Y-%m-%d')}"

    def restore(self, *args):
        r = self.contour("restore", *args, "--json", cwd=self.tmp)
        return r.returncode, json.loads(r.stdout)


class RestoreTest(RestoreCase):

    def test_a_restored_space_is_back_where_it_was_with_the_same_tree(self):
        code, said = self.restore(self.id)
        self.assertEqual(code, 0, said)
        self.assertIsNone(said["refused"])
        self.assertEqual(said["path"], str(self.space))
        self.assertEqual(self.tracked(self.space), self.before)

    def test_a_space_can_be_restored_somewhere_else_under_its_own_name(self):
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        code, said = self.restore(self.id, "--to", str(elsewhere))
        self.assertEqual(code, 0, said)
        self.assertEqual(said["path"], str(elsewhere / "alpha"))
        self.assertEqual(self.tracked(elsewhere / "alpha"), self.before)
        self.assertFalse(self.space.exists())

    def test_the_bundle_stays_in_the_trash_after_a_restore(self):
        self.restore(self.id)
        self.assertEqual([b.stem for b in self.trash().glob("*.bundle")], [self.id])

    def test_a_bundle_whose_record_is_lost_still_restores_where_it_is_told(self):
        """The name is in the bundle's own file name; the old path is not."""
        (self.trash() / f"{self.id}.json").unlink()
        code, said = self.restore(self.id)
        self.assertEqual(code, 1)
        self.assertIn("--to", said["refused"])
        code, said = self.restore(self.id, "--to", str(self.spaces))
        self.assertEqual(code, 0, said)
        self.assertEqual(self.tracked(self.space), self.before)

    def test_a_restored_space_refuses_every_push(self):
        """The stub lives in `.git/hooks`, which no clone carries."""
        self.restore(self.id)
        bare = self.tmp / "elsewhere.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
        r = subprocess.run(["git", "-C", str(self.space), "push", str(bare), "--all"],
                           env=self.env, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("never pushed", r.stderr)
        self.assertEqual(self.git("for-each-ref", cwd=bare), "")

    def test_doctor_in_a_restored_space_is_all_ok(self):
        self.restore(self.id)
        on_path = self.tmp / "bin"
        on_path.mkdir()
        (on_path / "contour").symlink_to(CONTOUR)
        self.env["PATH"] = f"{on_path}:{self.env['PATH']}"
        r = self.contour("doctor")
        self.assertEqual(r.returncode, 0, r.stdout)
        said = [l.split()[0] for l in r.stdout.splitlines() if l.strip()]
        self.assertEqual(set(said) - {"ok", "toolkit"}, set(), r.stdout)


class ListingTest(RestoreCase):

    def test_deleted_spaces_are_listed_apart_from_live_ones_with_name_and_date(self):
        said = json.loads(self.contour("spaces", "--json", cwd=self.tmp).stdout)
        self.assertEqual(said["spaces"], [])
        [gone] = said["deleted"]
        self.assertEqual((gone["id"], gone["name"], gone["deleted"], gone["path"]),
                         (self.id, "alpha", time.strftime("%Y-%m-%d"), str(self.space)))

    def test_the_list_is_the_trash_as_the_module_reads_it(self):
        said = json.loads(self.contour("spaces", "--json", cwd=self.tmp).stdout)
        with mock.patch.dict(os.environ, CONTOUR_HOME=self.env["CONTOUR_HOME"]):
            self.assertEqual(said["deleted"], restore.deleted())

    def test_the_plain_list_says_so_too_and_how_to_restore(self):
        said = self.contour("spaces", cwd=self.tmp).stdout
        self.assertIn("deleted", said)
        self.assertIn(time.strftime("%Y-%m-%d"), said)
        self.assertIn(f"contour restore {self.id}", said)

    def test_a_restored_space_is_live_and_its_bundle_still_listed(self):
        self.restore(self.id)
        said = json.loads(self.contour("spaces", "--json", cwd=self.tmp).stdout)
        self.assertEqual([s["name"] for s in said["spaces"]], ["alpha"])
        self.assertEqual([d["id"] for d in said["deleted"]], [self.id])

    def test_a_bundle_whose_space_stands_again_says_where_it_is_live(self):
        [gone] = json.loads(self.contour("spaces", "--json", cwd=self.tmp).stdout)["deleted"]
        self.assertIsNone(gone["live"])
        self.restore(self.id)
        [gone] = json.loads(self.contour("spaces", "--json", cwd=self.tmp).stdout)["deleted"]
        self.assertEqual(gone["live"], str(self.space))
        said = self.contour("spaces", cwd=self.tmp).stdout
        self.assertIn(f"restored, live at {self.space}", said)
        self.assertNotIn(f"contour restore {self.id}", said)


class PurgeTest(RestoreCase):
    """Removing a bundle: the one act in the trash nothing undoes."""

    def purge(self, *args):
        r = self.contour("purge", *args, "--json", cwd=self.tmp)
        return r.returncode, json.loads(r.stdout)

    def test_without_the_confirming_flag_it_proposes_and_changes_nothing(self):
        before = self.snapshot(self.tmp)
        r = self.contour("purge", self.id, cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.snapshot(self.tmp), before)
        for line in (self.id, "only copy", "cannot be undone", f"contour purge {self.id} --yes"):
            self.assertIn(line, r.stdout)

    def test_confirmed_it_removes_the_bundle_and_its_record_and_nothing_else(self):
        self.restore(self.id)
        live = self.snapshot(self.space)
        code, said = self.purge(self.id)
        self.assertIn(f"live space still stands at {self.space}", said["copy"])
        code, said = self.purge(self.id, "--yes")
        self.assertEqual(code, 0, said)
        self.assertEqual(list(self.trash().iterdir()), [])
        self.assertEqual(self.snapshot(self.space), live)
        listed = json.loads(self.contour("spaces", "--json", cwd=self.tmp).stdout)
        self.assertEqual(listed["deleted"], [])

    def test_a_bundle_the_trash_does_not_hold_is_refused(self):
        before = self.snapshot(self.tmp)
        for id in ("beta-2026-01-01", "--yes"):
            with self.subTest(id=id):
                code, said = self.purge(id, "--yes")
                self.assertEqual(code, 1)
                self.assertIn("nothing in the trash", said["refused"])
        self.assertEqual(self.snapshot(self.tmp), before)


class RefusalTest(RestoreCase):

    def refused(self, *args):
        before = self.snapshot(self.tmp)
        code, said = self.restore(*args)
        self.assertEqual(code, 1, said)
        self.assertEqual(self.snapshot(self.tmp), before)
        return said["refused"]

    def test_a_path_that_is_taken_is_refused(self):
        """Even by an empty directory, which git would clone into happily."""
        self.space.mkdir()
        self.assertIn("already exists", self.refused(self.id))

    def test_a_name_a_live_space_has_is_refused_wherever_it_would_go(self):
        r = self.contour("init", "alpha", cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.env["CONTOUR_SPACES"] = f"{self.spaces}:{self.tmp}"
        said = self.refused(self.id, "--to", str(self.spaces))
        self.assertIn("a live space is already called alpha", said)

    def test_a_bundle_the_trash_does_not_hold_is_refused(self):
        self.assertIn("nothing in the trash", self.refused("beta-2026-01-01"))


if __name__ == "__main__":
    unittest.main()
