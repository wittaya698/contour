"""Deleting from the lobby (ADR 0021, decision 6; issue 34).

The page is one client of `contour delete`: the lobby's server runs the
command and passes its answer back, and holds none of the rules itself. The
confirm is the space's name, typed, and it is the command that checks it.
"""
import json
import unittest
import urllib.error

from test_lobby_rename import LobbyRenameCase


class LobbyDeleteTest(LobbyRenameCase):

    def remove(self, **more):
        return self.ask("/delete", {"path": str(self.space), **more})

    def test_asking_shows_the_command_s_proposal_and_changes_nothing(self):
        before = self.snapshot(self.tmp)
        said = self.remove()
        self.assertEqual(self.snapshot(self.tmp), before)
        proposed = json.loads(self.contour("delete", "alpha", "--json").stdout)
        self.assertEqual(said, proposed)

    def test_confirming_with_the_typed_name_deletes_and_the_list_says_so(self):
        said = self.remove(name="alpha")
        self.assertIsNone(said["refused"])
        self.assertFalse(self.space.exists())
        self.assertEqual(self.ask("/spaces")["spaces"], [])
        self.assertEqual(len(list((self.home / ".contour" / "trash").glob("alpha-*.bundle"))), 1)

    def test_a_typed_name_that_is_not_the_space_s_is_refused_as_the_command_words_it(self):
        for typed in ("alph", "beta", "--yes", ""):
            with self.subTest(typed=typed):
                before = self.snapshot(self.spaces)
                said = self.remove(name=typed)
                self.assertIn("is not this space's name", said["refused"])
                self.assertEqual(self.snapshot(self.spaces), before)

    def test_a_directory_the_lobby_does_not_list_is_not_a_space_to_delete(self):
        for path in (self.tmp, self.space / "refs"):
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as no:
                self.ask("/delete", {"path": str(path), "name": "alpha"})
            self.assertEqual(no.exception.code, 404)
            no.exception.close()
        self.assertTrue(self.space.exists())

    def test_a_refusal_is_the_command_s_worded_as_the_command_worded_it(self):
        from lib import presence
        (self.space / "work").mkdir()
        (self.space / "work" / "scene.blend").write_bytes(b"yours")
        self.enterContext(presence.present(self.space, "console"))
        command = json.loads(self.contour("delete", "alpha", "--json").stdout)["refused"]
        self.assertIn("console", command)
        before = self.snapshot(self.spaces)
        for more in ({}, {"name": "alpha"}):
            with self.subTest(confirm=bool(more)):
                self.assertEqual(self.remove(**more)["refused"], command)
                self.assertEqual(self.snapshot(self.spaces), before)

    def test_it_offers_delete(self):
        self.assertIn("delete", self.ask("/can")["can"])


if __name__ == "__main__":
    unittest.main()
