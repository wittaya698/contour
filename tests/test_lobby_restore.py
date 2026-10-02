"""Restoring from the lobby (ADR 0021, decision 6; issue 35).

The page is one client of `contour restore`: the trash is listed in the same
reading as the live spaces, and a restore is the command, run by the lobby's
server, its answer passed back as it gave it.
"""
import json
import time
import unittest
import urllib.error

from test_lobby_rename import LobbyRenameCase


class LobbyRestoreTest(LobbyRenameCase):

    def setUp(self):
        super().setUp()
        self.before = self.snapshot(self.space)
        r = self.contour("delete", "alpha", "--yes", "--json")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.id = f"alpha-{time.strftime('%Y-%m-%d')}"

    def test_the_trash_is_listed_apart_from_the_live_spaces(self):
        listed = self.ask("/spaces")
        self.assertEqual(listed["spaces"], [])
        self.assertEqual([d["id"] for d in listed["deleted"]], [self.id])

    def test_restoring_brings_it_back_and_it_lists_as_live(self):
        said = self.ask("/restore", {"id": self.id})
        self.assertIsNone(said["refused"])
        self.assertEqual(self.snapshot(self.space), self.before)
        self.assertEqual([s["name"] for s in self.ask("/spaces")["spaces"]], ["alpha"])

    def test_a_refusal_is_the_command_s_worded_as_the_command_worded_it(self):
        self.space.mkdir()
        command = json.loads(self.contour("restore", self.id, "--json",
                                          cwd=self.tmp).stdout)["refused"]
        self.assertIn("already exists", command)
        self.assertEqual(self.ask("/restore", {"id": self.id})["refused"], command)

    def test_a_bundle_the_lobby_does_not_list_is_not_one_to_restore(self):
        with self.assertRaises(urllib.error.HTTPError) as no:
            self.ask("/restore", {"id": "../../etc"})
        self.assertEqual(no.exception.code, 404)
        no.exception.close()

    def test_it_offers_restore_and_purge(self):
        can = self.ask("/can")["can"]
        self.assertIn("restore", can)
        self.assertIn("purge", can)

    def test_asking_to_purge_shows_the_command_s_proposal_and_changes_nothing(self):
        before = self.snapshot(self.tmp)
        said = self.ask("/purge", {"id": self.id})
        self.assertEqual(self.snapshot(self.tmp), before)
        command = json.loads(self.contour("purge", self.id, "--json", cwd=self.tmp).stdout)
        self.assertEqual(said, command)

    def test_purging_with_the_typed_id_removes_the_bundle(self):
        said = self.ask("/purge", {"id": self.id, "typed": self.id})
        self.assertIsNone(said["refused"])
        self.assertEqual(self.ask("/spaces")["deleted"], [])

    def test_a_typed_id_that_is_not_this_bundle_s_removes_nothing(self):
        """Not even another bundle's id, which the command would take."""
        (self.home / ".contour" / "trash" / "other-2026-01-01.bundle").write_bytes(b"x")
        before = self.snapshot(self.tmp)
        for typed in ("other-2026-01-01", "alpha", ""):
            with self.subTest(typed=typed):
                said = self.ask("/purge", {"id": self.id, "typed": typed})
                self.assertIn(f"type {self.id}", said["refused"])
        self.assertEqual(self.snapshot(self.tmp), before)

    def test_a_bundle_the_lobby_does_not_list_is_not_one_to_purge(self):
        with self.assertRaises(urllib.error.HTTPError) as no:
            self.ask("/purge", {"id": "nope", "typed": "nope"})
        self.assertEqual(no.exception.code, 404)
        no.exception.close()


if __name__ == "__main__":
    unittest.main()
