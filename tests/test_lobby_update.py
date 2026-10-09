"""Updating from the lobby (ADR 0026, decision 2; issue 81).

The page is one client of `contour update`: the lobby's server runs the command
and passes its answer back, and holds none of the rules itself. Run as the user
runs it — `contour lobby` spawned over a space `contour update` would bring in
step, asked the way the page asks it.
"""
import json
import os
import unittest
import urllib.error

import test_lobby_rename
from test_update import OLD, RULES, UpdateCase

from lib.lobby import PAGE    # noqa: E402
from executables import executable  # noqa: E402


class UpdatedUnsavedTest(UpdateCase):
    """The row says updated-not-saved until a commit carries the update, and
    the listing works that out from git each time, storing nothing."""

    def listed(self):
        said = json.loads(self.contour("spaces", "--json", cwd=self.spaces).stdout)
        return {s["name"]: s for s in said["spaces"]}

    def test_a_space_as_committed_is_not_updated(self):
        self.assertIsNone(self.listed()["alpha"]["updated"])

    def test_an_update_reads_as_unsaved_until_the_next_commit(self):
        self.contour("update", "--yes")
        self.assertEqual(self.listed()["alpha"]["updated"], {"from": OLD})
        self.git("commit", "-qam", "updated")
        self.assertIsNone(self.listed()["alpha"]["updated"])


class LobbyUpdateCase(UpdateCase):

    open = test_lobby_rename.LobbyRenameCase.open
    ask = test_lobby_rename.LobbyRenameCase.ask

    def setUp(self):
        super().setUp()
        quiet = executable(self.tmp / "no-browser",   # $BROWSER, so none opens
                           "#!/bin/sh\nexit 0\n")
        self.env["BROWSER"] = str(quiet)
        self.open()

    def update(self, **more):
        return self.ask("/update", {"path": str(self.space), **more})


class LobbyProposalTest(LobbyUpdateCase):

    def test_asking_shows_the_command_s_proposal_and_changes_nothing(self):
        before = self.snapshot()
        said = self.update()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(said, self.json())
        self.assertIn(RULES, said["replaced"])

    def test_it_offers_update(self):
        self.assertIn("update", self.ask("/can")["can"])

    def test_a_directory_the_lobby_does_not_list_is_not_a_space_to_update(self):
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        for path in (elsewhere, self.tmp, self.space / "refs"):
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as no:
                self.ask("/update", {"path": str(path)})
            self.assertEqual(no.exception.code, 404)
            no.exception.close()


class LobbyPerformTest(LobbyUpdateCase):

    def test_confirming_what_was_shown_updates_and_the_list_says_unsaved(self):
        shown = self.update()
        said = self.update(shown=shown)
        self.assertIsNone(said["refused"])
        self.assertEqual((self.space / RULES).read_text(), self.now(RULES))
        listed = {s["name"]: s for s in self.ask("/spaces")["spaces"]}
        self.assertEqual(listed["alpha"]["updated"], {"from": OLD})
        self.assertEqual(self.git("log", "--format=%s").split(), ["alpha"])

    def test_a_confirm_for_a_proposal_that_has_since_changed_is_refused(self):
        """Here a copy edited after the page showed it would be replaced: the
        click must not overwrite the edit."""
        shown = self.update()
        (self.space / RULES).write_text((self.space / RULES).read_text() + "mine\n")
        before = self.snapshot()
        said = self.update(shown=shown)
        self.assertIn("changed since it was shown", said["refused"])
        self.assertEqual(self.snapshot(), before)

    def test_a_confirm_that_shows_nothing_confirms_nothing(self):
        before = self.snapshot()
        said = self.update(shown={})
        self.assertIn("changed since it was shown", said["refused"])
        self.assertEqual(self.snapshot(), before)


class LobbyRefusalTest(LobbyUpdateCase):
    """A refusal is the command's, worded as the command worded it, and the
    page's confirm cannot get past one."""

    def refused(self, obstacle):
        shown = self.update()
        obstacle()
        before = self.snapshot()
        command = self.json()["refused"]
        self.assertTrue(command)
        for more in ({}, {"shown": shown}):
            with self.subTest(confirm=bool(more)):
                self.assertEqual(self.update(**more)["refused"], command)
                self.assertEqual(self.snapshot(), before)

    def test_a_space_held_by_a_run_is_refused(self):
        from lib import lock

        def hold():
            record = lock.take(self.space, "contour run claude")
            self.addCleanup(lock.release, self.space, record)
        self.refused(hold)

    def test_a_space_with_a_console_open_on_it_is_refused(self):
        from lib import presence
        self.refused(lambda: self.enterContext(presence.present(self.space, "console")))


class PageTest(unittest.TestCase):
    """The page's source, because there is no browser here: structural, as
    `test_lobby`'s page tests are."""

    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")

    def function(self, name):
        """One top-level function's source, to its closing brace at column 0."""
        return self.page.split(f"function {name}(")[1].split("\n}\n")[0]

    def test_needs_an_update_carries_its_action_where_the_host_can_do_it(self):
        """ADR 0025, decision 10: health appears with the action ADR 0026 decides."""
        health = self.function("health")
        self.assertIn("needs an update", health)
        self.assertIn("'Update…'", health)
        self.assertIn("can.has('update')", self.function("row"))

    def test_the_confirm_exists_only_under_the_whole_proposal(self):
        """What it will change, and what it will leave alone and why, before it
        does anything (ADR 0026, decision 2)."""
        self.assertEqual(self.page.count("'Confirm update'"), 1)
        shown = self.function("updating")
        made = shown.index("'Confirm update'")
        for part in ("p.replaced", "p.written", "p.left", "l.why", "p.unseen"):
            self.assertLess(shown.index(part), made, part)

    def test_the_confirm_sends_back_what_it_showed(self):
        self.assertIn("shown: p", self.function("updating"))

    def test_a_refusal_is_shown_as_the_command_worded_it_with_no_confirm(self):
        shown = self.function("updating")
        refused = shown.index("if (p.refused)")
        self.assertIn("p.refused", shown[refused:shown.index("return", refused)])
        self.assertLess(refused, shown.index("'Confirm update'"))

    def test_an_updated_space_says_so_until_it_is_saved(self):
        """*Not saved yet*: commit is a hidden term (ADR 0025, decision 1)."""
        row = self.function("row")
        self.assertIn("s.updated", row)
        self.assertIn("'updated, not saved yet'", row)


if __name__ == "__main__":
    unittest.main()
