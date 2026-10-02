"""`contour lobby`: the spaces on this machine, on one page (ADR 0021).

Run as the user runs it — the launcher spawned, the page's server talked to the
way the page talks to it — over spaces `contour init` made in a temporary
directory that `$CONTOUR_SPACES` points at.
"""
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTOUR = ROOT / "contour"
sys.path.insert(0, str(ROOT))

from lib.lobby import PAGE, Lobby    # noqa: E402
from lib.page import TOKEN_HEADER    # noqa: E402


class LobbyTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.spaces = self.tmp / "spaces"
        self.spaces.mkdir()
        quiet = self.tmp / "no-browser"
        quiet.write_text("#!/bin/sh\nexit 0\n")     # $BROWSER, so none opens
        quiet.chmod(0o755)
        self.env = dict(os.environ, CONTOUR_SPACES=str(self.spaces),
                        CONTOUR_HOME=str(self.tmp / "home"),
                        BROWSER=str(quiet))

    def contour(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(CONTOUR), *args],
                              cwd=str(cwd or self.tmp), env=self.env,
                              capture_output=True, text=True, timeout=60)

    def init(self, name):
        r = self.contour("init", name, cwd=self.spaces)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return self.spaces / name

    def lobby(self, cwd=None, **env):
        """`contour lobby` running, and the origin and token its first line
        printed — the URL a person would click."""
        proc = subprocess.Popen([sys.executable, str(CONTOUR), "lobby"],
                                cwd=str(cwd or self.tmp), env=dict(self.env, **env),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True)
        self.addCleanup(proc.stdout.close)
        self.addCleanup(proc.kill)
        url = re.search(r"http://\S+", proc.stdout.readline()).group(0)
        self.origin, self.token = url.split("/?")[0], url.split("t=")[1]
        return proc

    def get(self, path, **headers):
        req = urllib.request.Request(self.origin + path,
                                     headers={TOKEN_HEADER: self.token, **headers})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def test_it_lists_what_contour_spaces_lists_from_outside_any_space(self):
        """The page is one client of the command line, and it asks the same
        reading the JSON form prints (ADR 0021, decision 3)."""
        self.init("alpha"), self.init("beta")
        said = json.loads(self.contour("spaces", "--json").stdout)
        self.lobby()
        self.assertEqual(self.get("/spaces")["spaces"], said["spaces"])

    def test_it_works_from_inside_a_space_too(self):
        """Not a model command: standing in a space changes nothing it shows."""
        alpha = self.init("alpha")
        self.lobby(cwd=alpha)
        self.assertEqual([s["name"] for s in self.get("/spaces")["spaces"]], ["alpha"])

    def beat(self):
        req = urllib.request.Request(
            self.origin + "/beat", data=b"{}", method="POST",
            headers={TOKEN_HEADER: self.token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()

    def test_closing_the_tab_ends_it_with_one_terse_line(self):
        """A page that stopped beating is a tab that closed. There is no Done
        button: a list has nothing to finish."""
        proc = self.lobby(CONTOUR_LOBBY_GRACE="0.5")
        self.beat()
        self.assertEqual(proc.wait(timeout=30), 0)
        self.assertEqual(proc.stdout.read(), "lobby closed — the page closed\n")

    def test_a_page_that_never_beat_has_not_closed(self):
        """Before a first beat nothing has opened the page yet, and ending then
        would make a slow browser look like a closed tab."""
        proc = self.lobby(CONTOUR_LOBBY_GRACE="0.2")
        with self.assertRaises(subprocess.TimeoutExpired):
            proc.wait(timeout=1.5)
        self.assertIn("rename", self.get("/can")["can"])


class LobbyPageTest(unittest.TestCase):
    """The page's source, because there is no browser here: structural where
    the tests above are behavioural, as `test_canvas_auth` is about the canvas
    page. It cannot prove the page behaves, only that it is built the one way
    that can."""

    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")

    def test_every_request_goes_through_one_helper(self):
        """A second bare `fetch` is how the token gets forgotten."""
        self.assertEqual(self.page.count("fetch("), 1)
        self.assertIn(TOKEN_HEADER, self.page)
        self.assertIn("application/json", self.page)

    def test_it_beats(self):
        self.assertRegex(self.page, r"ask\('/beat', \{\}\)")

    def test_no_spaces_is_onboarding_and_not_an_empty_table(self):
        """The table and the onboarding copy are shown for exactly opposite
        answers, and the copy says what a space is and how one is made."""
        self.assertIn("getElementById('list').hidden = spaces.length === 0", self.page)
        self.assertIn("getElementById('onboarding').hidden = spaces.length !== 0", self.page)
        onboarding = self.page.split('id="onboarding"')[1].split("</section>")[0]
        self.assertIn("model space", onboarding)
        self.assertIn("contour init", onboarding)

    def test_it_asks_the_host_what_it_can_do(self):
        self.assertIn("ask('/can')", self.page)

    def function(self, name):
        """One top-level function's source, to its closing brace at column 0."""
        return self.page.split(f"function {name}(")[1].split("\n}\n")[0]

    def test_rename_is_offered_only_where_the_host_can_do_it(self):
        self.assertIn("can.has('rename')", self.function("row"))

    def test_the_confirm_exists_only_under_the_whole_proposal(self):
        """The one place a confirm is made is the function that lays out the
        proposal, after every part of it, so the page cannot confirm a rename
        it has not shown (ADR 0021, decision 5)."""
        self.assertEqual(self.page.count("'Confirm rename'"), 1)
        shown = self.function("proposal")
        made = shown.index("'Confirm rename'")
        for part in ("p.changes", "p.untouched", "p.leaves", "p.unseen"):
            self.assertLess(shown.index(part), made, part)

    def test_the_confirm_sends_back_what_it_showed(self):
        """The server confirms that proposal only, and refuses if the command
        no longer says the same."""
        self.assertIn("shown: p", self.function("proposal"))

    def test_a_refusal_is_shown_as_the_command_worded_it_with_no_confirm(self):
        shown = self.function("proposal")
        refused = shown.index("if (p.refused)")
        self.assertIn("p.refused", shown[refused:shown.index("return", refused)])
        self.assertLess(refused, shown.index("'Confirm rename'"))

    def test_a_renamed_space_says_so_until_it_is_committed(self):
        row = self.function("row")
        self.assertIn("s.renamed", row)
        self.assertIn("uncommitted", row)

    def test_delete_is_offered_only_where_the_host_can_do_it(self):
        self.assertIn("can.has('delete')", self.function("row"))

    def test_the_delete_is_enabled_only_once_the_typed_name_matches(self):
        """Typing the name is the confirm (ADR 0021, decision 6): the button
        starts disabled, and every keystroke enables it only on an exact match."""
        shown = self.function("deleting")
        self.assertEqual(self.page.count("'Delete for good'"), 1)
        self.assertIn("go.disabled = true", shown)
        self.assertIn("go.disabled = typed.value !== s.name", shown)
        self.assertIn("typed.oninput", shown)

    def test_the_delete_confirm_says_what_it_cannot_undo_and_cannot_see(self):
        shown = self.function("deleting")
        made = shown.index("'Delete for good'")
        for part in ("p.bundle", "p.disk", "p.left", "p.unseen"):
            self.assertLess(shown.index(part), made, part)

    def test_the_delete_sends_what_was_typed_and_the_command_judges_it(self):
        self.assertIn("name: typed.value", self.function("deleting"))

    def test_a_delete_refusal_is_shown_as_the_command_worded_it_with_no_confirm(self):
        shown = self.function("deleting")
        refused = shown.index("if (p.refused)")
        self.assertIn("p.refused", shown[refused:shown.index("return", refused)])
        self.assertLess(refused, shown.index("'Delete for good'"))

    def test_the_trash_is_its_own_list_under_the_live_one(self):
        """Apart from the live spaces, so a deleted one never reads as live,
        and shown only when there is something in it."""
        shown = self.function("render")
        self.assertIn("deleted", shown)
        self.assertIn("getElementById('trash').hidden = deleted.length === 0", shown)
        self.assertIn('id="trash"', self.page)

    def test_restore_is_offered_only_where_the_host_can_do_it(self):
        gone = self.function("gone")
        self.assertIn("can.has('restore')", gone)
        self.assertIn("ask('/restore', { id: d.id", gone)

    def test_a_bundle_whose_space_is_live_says_so_and_offers_no_restore(self):
        gone = self.function("gone")
        self.assertIn("'restored, live at ' + d.live", gone)
        self.assertIn("can.has('restore') && !d.live", gone)

    def test_removing_a_bundle_is_offered_only_where_the_host_can_do_it(self):
        self.assertIn("can.has('purge')", self.function("gone"))

    def test_removing_a_bundle_is_enabled_only_once_its_id_is_typed(self):
        shown = self.function("purging")
        self.assertEqual(self.page.count("'Remove for good'"), 1)
        self.assertIn("go.disabled = true", shown)
        self.assertIn("go.disabled = typed.value !== d.id", shown)
        self.assertIn("typed: typed.value", shown)

    def test_the_purge_confirm_says_whether_this_is_the_only_copy(self):
        shown = self.function("purging")
        made = shown.index("'Remove for good'")
        for part in ("p.copy", "p.gone", "p.bundle"):
            self.assertLess(shown.index(part), made, part)
        refused = shown.index("if (p.refused)")
        self.assertLess(refused, made)

    def test_a_restore_refusal_is_shown_as_the_command_worded_it(self):
        gone = self.function("gone")
        self.assertIn("'Not restored: ' + done.refused", gone)

    def test_enter_is_offered_only_where_the_host_can_do_it(self):
        row = self.function("row")
        self.assertIn("can.has('enter')", row)
        self.assertIn("ask('/enter'", self.page)

    def test_without_enter_the_row_shows_the_line_that_makes_an_environment(self):
        """The line is the host's, asked once, so it is the one
        `contour-console` prints and never a copy kept in the page."""
        self.assertIn("ask('/environment')", self.page)
        row = self.function("row")
        self.assertIn("environment.console", row)
        self.assertNotIn(".venv", self.page)

    def test_a_space_open_in_a_console_says_so_and_offers_no_second_one(self):
        row = self.function("row")
        self.assertIn("p.kind === 'console'", row)
        self.assertIn("open in a console", row)
        self.assertIn("!open", row)

    def test_an_enter_refusal_is_shown_as_the_host_worded_it(self):
        self.assertIn("'Not entered: ' + done.refused", self.function("entering"))

    def test_open_in_finder_is_offered_only_where_the_host_can_do_it(self):
        row = self.function("row")
        self.assertIn("can.has('reveal')", row)
        self.assertIn("Open in Finder", row)
        self.assertIn("ask('/reveal'", self.page)


class LobbyProtectionTest(unittest.TestCase):
    """Issue 01's protections, held by the lobby itself and not only inherited
    on paper: each is asked of a running `Lobby` the way an attacker's page
    would ask it. `/done`, `/rename` and `/delete` are the state-changing
    POSTs: one ends the session, the others move or remove a space, and a
    request that is turned away never reaches the listing they check a path
    against."""

    LISTED = {"roots": ["/nowhere"], "spaces": [], "deleted": []}

    def setUp(self):
        self.asked = 0
        self.lobby = Lobby(self.listing, grace=None)
        self.addCleanup(self.lobby.stop)
        self.lobby.start()

    def listing(self):
        self.asked += 1
        return self.LISTED

    def request(self, path, body=None, token=True, **headers):
        if token:
            headers[TOKEN_HEADER] = self.lobby.token
        if body is not None:
            headers.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(
            self.lobby.origin + path, headers=headers,
            data=None if body is None else json.dumps(body).encode(),
            method="GET" if body is None else "POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status

    def refused(self, code, *args, **kwargs):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        caught.exception.close()

    def test_without_the_token_nothing_is_listed(self):
        self.refused(403, "/spaces", token=False)
        self.assertEqual(self.asked, 0)

    def test_without_the_token_nothing_ends(self):
        self.refused(403, "/done", {}, token=False)
        self.assertFalse(self.lobby.done)

    RENAME = {"path": "/nowhere/alpha", "name": "beta"}

    def test_without_the_token_nothing_is_renamed(self):
        self.refused(403, "/rename", self.RENAME, token=False)
        self.assertEqual(self.asked, 0)

    def test_a_rename_that_is_not_json_goes_nowhere(self):
        self.refused(415, "/rename", self.RENAME,
                     **{"Content-Type": "text/plain;charset=UTF-8"})
        self.assertEqual(self.asked, 0)

    def test_a_rename_from_another_origin_goes_nowhere(self):
        self.refused(403, "/rename", self.RENAME, Origin="https://example.com")
        self.refused(403, "/rename", self.RENAME, **{"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(self.asked, 0)

    DELETE = {"path": "/nowhere/alpha", "name": "alpha"}

    def test_without_the_token_nothing_is_deleted(self):
        self.refused(403, "/delete", self.DELETE, token=False)
        self.assertEqual(self.asked, 0)

    def test_a_delete_that_is_not_json_or_from_another_origin_goes_nowhere(self):
        self.refused(415, "/delete", self.DELETE,
                     **{"Content-Type": "text/plain;charset=UTF-8"})
        self.refused(403, "/delete", self.DELETE, Origin="https://example.com")
        self.refused(403, "/delete", self.DELETE, **{"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(self.asked, 0)

    RESTORE = {"id": "alpha-2026-10-02"}

    def test_without_the_token_or_from_another_origin_nothing_is_restored(self):
        self.refused(403, "/restore", self.RESTORE, token=False)
        self.refused(415, "/restore", self.RESTORE,
                     **{"Content-Type": "text/plain;charset=UTF-8"})
        self.refused(403, "/restore", self.RESTORE, Origin="https://example.com")
        self.assertEqual(self.asked, 0)

    PURGE = {"id": "alpha-2026-10-02", "typed": "alpha-2026-10-02"}

    def test_without_the_token_or_from_another_origin_nothing_is_purged(self):
        self.refused(403, "/purge", self.PURGE, token=False)
        self.refused(415, "/purge", self.PURGE,
                     **{"Content-Type": "text/plain;charset=UTF-8"})
        self.refused(403, "/purge", self.PURGE, Origin="https://example.com")
        self.assertEqual(self.asked, 0)

    ENTER = {"path": "/nowhere/alpha"}

    def test_without_the_token_or_from_another_origin_nothing_is_entered_or_opened(self):
        for path in ("/enter", "/reveal"):
            with self.subTest(path=path):
                self.refused(403, path, self.ENTER, token=False)
                self.refused(415, path, self.ENTER,
                             **{"Content-Type": "text/plain;charset=UTF-8"})
                self.refused(403, path, self.ENTER, Origin="https://example.com")
                self.refused(403, path, self.ENTER, **{"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(self.asked, 0)

    def test_a_post_that_is_not_json_ends_nothing(self):
        self.refused(415, "/done", {}, **{"Content-Type": "text/plain;charset=UTF-8"})
        self.assertFalse(self.lobby.done)

    def test_another_origin_is_refused(self):
        """DNS rebinding hands another site this address; the token is then
        not the whole story."""
        self.refused(403, "/spaces", Origin="https://example.com")
        self.refused(403, "/done", {}, Origin="https://example.com")
        self.assertEqual((self.asked, self.lobby.done), (0, False))

    def test_a_request_the_browser_calls_cross_site_is_refused(self):
        for site in ("cross-site", "same-site"):
            with self.subTest(site=site):
                self.refused(403, "/done", {}, **{"Sec-Fetch-Site": site})
        self.assertFalse(self.lobby.done)

    def test_the_page_and_its_own_requests_are_served(self):
        """The guard lets the only caller there is through."""
        req = urllib.request.Request(self.lobby.url, headers={"Sec-Fetch-Site": "none"})
        with urllib.request.urlopen(req, timeout=5) as r:
            self.assertEqual(r.status, 200)
        self.assertEqual(self.request("/spaces", Origin=self.lobby.origin,
                                      **{"Sec-Fetch-Site": "same-origin"}), 200)

    def test_it_listens_on_the_loopback_address_only(self):
        self.assertTrue(self.lobby.origin.startswith("http://127.0.0.1:"),
                        self.lobby.origin)

    def test_two_sessions_do_not_share_a_token(self):
        other = Lobby(self.listing)
        self.assertNotEqual(self.lobby.token, other.token)
        self.assertGreater(len(other.token), 20)

    def test_serving_the_page_never_writes_the_token_to_stderr(self):
        caught = io.StringIO()
        req = urllib.request.Request(self.lobby.url, headers={"Sec-Fetch-Site": "none"})
        with contextlib.redirect_stderr(caught):
            with urllib.request.urlopen(req, timeout=5) as r:
                self.assertEqual(r.status, 200)
            self.lobby._thread.join(0.2)
        self.assertNotIn(self.lobby.token, caught.getvalue())


if __name__ == "__main__":
    unittest.main()
