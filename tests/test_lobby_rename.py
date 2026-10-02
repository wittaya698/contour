"""Renaming from the lobby (ADR 0021, decision 5; issue 32).

The page is one client of `contour rename`: the lobby's server runs the
command and passes its answer back, and holds none of the rules itself. Run as
the user runs it — `contour lobby` spawned over a throwaway space, asked the
way the page asks it.
"""
import json
import re
import subprocess
import sys
import unittest
import urllib.error
import urllib.request

from test_rename import CONTOUR, RenameCase

from lib.page import TOKEN_HEADER    # noqa: E402


class RenamedUncommittedTest(RenameCase):
    """The row says renamed-uncommitted until a commit carries the rename,
    and the listing works that out from git each time, storing nothing."""

    def listed(self):
        said = json.loads(self.contour("spaces", "--json", cwd=self.spaces).stdout)
        return {s["name"]: s for s in said["spaces"]}

    def test_a_space_as_committed_is_not_renamed(self):
        self.assertIsNone(self.listed()["alpha"]["renamed"])

    def test_a_rename_reads_as_uncommitted_until_the_next_commit(self):
        self.contour("rename", "beta", "--yes")
        self.assertEqual(self.listed()["beta"]["renamed"], {"from": "alpha"})
        self.git("commit", "-qam", "renamed", cwd=self.spaces / "beta")
        self.assertIsNone(self.listed()["beta"]["renamed"])


class LobbyRenameCase(RenameCase):

    def setUp(self):
        super().setUp()
        quiet = self.tmp / "no-browser"
        quiet.write_text("#!/bin/sh\nexit 0\n")     # $BROWSER, so none opens
        quiet.chmod(0o755)
        self.env["BROWSER"] = str(quiet)
        self.open()

    def open(self, **popen):
        """`contour lobby` over the test's environment, as it stands now."""
        proc = subprocess.Popen([sys.executable, str(CONTOUR), "lobby"],
                                cwd=str(self.tmp), env=self.env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                **popen)
        self.addCleanup(proc.stdout.close)
        self.addCleanup(proc.kill)
        url = re.search(r"http://\S+", proc.stdout.readline()).group(0)
        self.origin, self.token = url.split("/?")[0], url.split("t=")[1]
        return proc

    def ask(self, path, body=None):
        """As the page asks: the token as a header, a POST as JSON."""
        req = urllib.request.Request(
            self.origin + path, method="GET" if body is None else "POST",
            data=None if body is None else json.dumps(body).encode(),
            headers={TOKEN_HEADER: self.token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    def rename(self, name, **more):
        return self.ask("/rename", {"path": str(self.space), "name": name, **more})


class LobbyProposalTest(LobbyRenameCase):

    def test_asking_shows_the_command_s_whole_proposal_and_changes_nothing(self):
        self.leave_behind()
        before = self.snapshot(self.spaces)
        said = self.rename("beta")
        self.assertEqual(self.snapshot(self.spaces), before)
        proposed = json.loads(self.contour("rename", "beta", "--json").stdout)
        self.assertEqual(said, proposed)

    def test_it_offers_rename(self):
        self.assertIn("rename", self.ask("/can")["can"])

    def test_a_directory_the_lobby_does_not_list_is_not_a_space_to_rename(self):
        """The page names a space by its path, so the path is checked against
        the listing: anywhere else, the command would run in a directory the
        lobby never showed."""
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        for path in (elsewhere, self.tmp, self.space / "refs"):
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as no:
                self.ask("/rename", {"path": str(path), "name": "beta"})
            self.assertEqual(no.exception.code, 404)
            no.exception.close()


class LobbyPerformTest(LobbyRenameCase):

    def test_confirming_what_was_shown_renames_and_the_list_says_uncommitted(self):
        """End to end: the space under its new name, its revision check clean
        with `revision:` bumped, and nothing committed."""
        shown = self.rename("beta")
        said = self.rename("beta", shown=shown)
        self.assertIsNone(said["refused"])
        beta = self.spaces / "beta"
        listed = {s["name"]: s for s in self.ask("/spaces")["spaces"]}
        self.assertEqual(list(listed), ["beta"])
        self.assertEqual(listed["beta"]["renamed"], {"from": "alpha"})
        self.assertIn("revision: 3", (beta / "spec.yaml").read_text())
        self.assertEqual(self.revision_check(beta), [])
        self.assertEqual(self.git("rev-list", "--count", "HEAD", cwd=beta).strip(), "1")


    def test_a_confirm_for_a_proposal_that_has_since_changed_is_refused(self):
        """What the user read is what is written: once the space has moved on
        from what the page showed — here, a transcript directory now to be left
        behind — the click confirms nothing, and the page must show it again."""
        shown = self.rename("beta")
        self.leave_behind()
        before = self.snapshot(self.spaces)
        said = self.rename("beta", shown=shown)
        self.assertIn("changed since it was shown", said["refused"])
        self.assertEqual(self.snapshot(self.spaces), before)

    def test_a_confirm_that_shows_nothing_confirms_nothing(self):
        before = self.snapshot(self.spaces)
        said = self.rename("beta", shown={})
        self.assertIn("changed since it was shown", said["refused"])
        self.assertEqual(self.snapshot(self.spaces), before)


class LobbyRefusalTest(LobbyRenameCase):
    """A refusal is the command's, worded as the command worded it, and the
    page's confirm cannot get past one."""

    def refused(self, obstacle):
        """After `obstacle`, the refusal, asked and confirmed alike, and the
        same as the command line's. The confirm carries a proposal from before
        the obstacle, as a page left open would."""
        shown = self.rename("beta")
        obstacle()
        before = self.snapshot(self.spaces)
        command = json.loads(self.contour("rename", "beta", "--json").stdout)["refused"]
        self.assertTrue(command)
        for more in ({}, {"shown": shown}):
            with self.subTest(confirm=bool(more)):
                self.assertEqual(self.rename("beta", **more)["refused"], command)
                self.assertEqual(self.snapshot(self.spaces), before)

    def test_a_name_already_taken_is_refused(self):
        self.refused(lambda: (self.spaces / "beta").mkdir())

    def test_a_space_held_by_a_run_is_refused(self):
        from lib import lock

        def hold():
            record = lock.take(self.space, "contour run claude")
            self.addCleanup(lock.release, self.space, record)
        self.refused(hold)

    def test_a_space_with_a_console_open_on_it_is_refused(self):
        from lib import presence
        self.refused(lambda: self.enterContext(presence.present(self.space, "console")))

if __name__ == "__main__":
    unittest.main()
