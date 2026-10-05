"""A lobby row is a picture and a verdict (ADR 0025, decision 10; issue 67).

What the row shows is read off the space, by `contour spaces --json`, the one
reading the lobby serves (ADR 0021, decision 3): spaces `contour init` made in a
temporary directory that `$CONTOUR_SPACES` points at, and what a check would
have left in them, written as a check writes it.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTOUR = ROOT / "contour"
sys.path.insert(0, str(ROOT))

from lib import panel, store    # noqa: E402
from lib.lobby import PAGE, Lobby    # noqa: E402


def kept(*results, built=True):
    """A verdict as `check` keeps it in `.contour/last-build.json`."""
    return {"built": built, "ok": built and all(r["ok"] for r in results),
            "lines": [], "results": list(results), "secs": 1.0, "build": None,
            "when": "2026-10-04T09:30:00+07:00"}


PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32
"""Enough of a PNG to be served as one; nothing here decodes it."""

HEIGHT_RED ={"id": "height", "ok": False, "info": "1640.0",
              "msg": "height 1640.0mm, want 1700±5"}


class RowTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.spaces = self.tmp / "spaces"
        self.spaces.mkdir()
        self.env = dict(os.environ, CONTOUR_SPACES=str(self.spaces),
                        CONTOUR_HOME=str(self.tmp / "home"))

    def contour(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(CONTOUR), *args],
                              cwd=str(cwd or self.tmp), env=self.env,
                              capture_output=True, text=True, timeout=60)

    def init(self, name):
        r = self.contour("init", name, cwd=self.spaces)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return self.spaces / name

    def checked(self, root, verdict):
        store.save(root / ".contour" / panel.NAME, verdict)

    def row(self, name):
        said = json.loads(self.contour("spaces", "--json").stdout)
        return next(s for s in said["spaces"] if s["name"] == name)

    def test_a_checked_model_is_listed_with_its_verdict_in_plain_words(self):
        """Issue 66's words, so the row and the console say the same thing."""
        chair = self.init("chair")
        self.checked(chair, kept(HEIGHT_RED))
        said = self.row("chair")["verdict"]
        self.assertEqual(said["line"], "1 thing doesn't match the spec")
        self.assertEqual(said["failing"],
                         ["Height is 1640 mm; the spec wants 1700, give or take 5."])

    def test_a_model_never_built_has_no_verdict_and_a_reference_for_a_picture(self):
        """Nothing judged it, so there is nothing to say about whether it is
        right; the picture is what the user gave it to be built from."""
        chair = self.init("chair")
        (chair / "refs" / "front.png").write_bytes(PNG)
        row = self.row("chair")
        self.assertIsNone(row["verdict"])
        self.assertEqual(row["picture"], "reference")

    def test_last_worked_on_is_the_newest_of_what_the_work_touches(self):
        """An edit to the build counts though nothing was built or saved since,
        and a fresh model was worked on when it was made."""
        chair = self.init("chair")
        made, edited = 1_790_000_000, 1_790_086_400
        for p in chair.rglob("*"):
            if ".git" not in p.parts:
                os.utime(p, (made, made))
        self.assertEqual(self.worked("chair"), made)
        (chair / "build.py").write_text("# the seat\n")
        os.utime(chair / "build.py", (edited, edited))
        self.assertEqual(self.worked("chair"), edited)

    def worked(self, name):
        return datetime.fromisoformat(self.row(name)["worked"]).timestamp()

    def lobby(self):
        """A lobby serving what `contour spaces --json` prints."""
        lobby = Lobby(lambda: json.loads(self.contour("spaces", "--json").stdout),
                      grace=None)
        self.addCleanup(lobby.stop)
        lobby.start()
        return lobby

    def picture(self, lobby, path):
        """What a row's `<img>` is handed: the token in the query, since an
        image cannot send a header."""
        url = (f"{lobby.origin}/picture?{urllib.parse.urlencode({'path': str(path)})}"
               f"&t={lobby.token}")
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.headers["Content-Type"], r.read()

    def test_the_lobby_hands_a_row_its_sheet_or_its_reference(self):
        chair, stool = self.init("chair"), self.init("stool")
        (chair / "refs" / "front.png").write_bytes(PNG)
        (stool / "refs" / "side.jpg").write_bytes(b"\xff\xd8\xff" + b"\0" * 32)
        (stool / "sheet.png").write_bytes(PNG + b"sheet")
        lobby = self.lobby()
        self.assertEqual(self.picture(lobby, chair), ("image/png", PNG))
        self.assertEqual(self.picture(lobby, stool), ("image/png", PNG + b"sheet"))

    def test_a_path_the_lobby_does_not_list_has_no_picture(self):
        """Only a listed space's picture, so the route reads no other file."""
        chair = self.init("chair")
        (chair / "refs" / "front.png").write_bytes(PNG)
        lobby = self.lobby()
        for path in (self.tmp, chair / "refs" / "front.png"):
            with self.subTest(path=path):
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    self.picture(lobby, path)
                self.assertEqual(caught.exception.code, 404)
                caught.exception.close()


class RowPageTest(unittest.TestCase):
    """The page's source, because there is no browser here, as
    `test_lobby.LobbyPageTest` reads it: what a row is built from, not that a
    browser draws it."""

    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")

    def function(self, name):
        """One top-level function's source, to its closing brace at column 0."""
        return self.page.split(f"function {name}(")[1].split("\n}\n")[0]

    def test_a_row_is_a_picture_a_name_a_verdict_when_and_open(self):
        row = self.function("row")
        self.assertIn("thumbnail(s)", row)
        self.assertIn("s.picture", self.function("thumbnail"))
        self.assertIn("'/picture?path=' + encodeURIComponent(s.path) + '&t=' + TOKEN",
                      self.function("thumbnail"))
        self.assertIn("s.name", row)
        self.assertIn("s.verdict", row)
        self.assertIn("s.worked", row)
        self.assertIn("'Open'", self.function("entering"))

    def test_a_model_never_built_says_so(self):
        self.assertIn("'not built yet'", self.function("verdict"))

    def test_rename_a_new_model_from_this_one_and_delete_sit_in_a_menu(self):
        """Behind one control, so the row's one button is Open; each still
        lays itself out in the room under the row, as before."""
        row = self.function("row")
        menu = row.split("const menu = ")[1].split("actions.append(menu)")[0]
        for label, opens in (("'Rename…'", "askName(s, room)"),
                             ("'New model from this one…'", "creating(room, s)"),
                             ("'Delete…'", "deleting(s, room)")):
            with self.subTest(label=label):
                self.assertIn(label, menu)
                self.assertIn(opens, menu)
        self.assertNotIn("entering(", menu)
        self.assertNotIn("Variation", self.page)

    def test_no_row_shows_a_toolkit_commit_or_a_commit_count(self):
        """Hidden terms leave the page (ADR 0025, decision 1)."""
        listed = self.page.split('id="list"')[1].split("</div>")[0]
        for hidden in ("Toolkit", "Commits"):
            self.assertNotIn(hidden, listed)
        for read in ("s.toolkit", "s.commits", "uncommitted"):
            self.assertNotIn(read, self.function("row"))

    def test_the_page_is_called_models(self):
        self.assertIn("<h1>Models</h1>", self.page)
        self.assertNotIn("Model spaces", self.page)

    def test_the_empty_state_suggests_no_terminal_command(self):
        """Someone with no models is asked to name one, and that is the whole
        way in; a terminal is not a way this person has."""
        onboarding = self.page.split('id="onboarding"')[1].split("</section>")[0]
        self.assertIn("Name your first model", onboarding)
        self.assertIn('id="first"', onboarding)
        for terminal in ("contour init", "terminal", "<code>", "git"):
            self.assertNotIn(terminal, onboarding)

    def test_health_says_nothing_when_nothing_is_wrong_and_the_outcome_when_it_is(self):
        """Not *in step*, and not which template file differs: a remote is a
        warning, and anything an update would put right is *needs an update*
        (ADR 0025, decision 10; ADR 0026 gives it an action)."""
        health = self.function("health")
        self.assertNotIn("in step", self.page)
        self.assertNotIn("template", health)
        self.assertIn("'has a remote — a model is never pushed', 'warn'", health)
        for wrong in ("s.scaffold.missing.length", "s.scaffold.drift.length", "!s.rules"):
            self.assertIn(wrong, health)
        self.assertIn("'needs an update'", health)


if __name__ == "__main__":
    unittest.main()
