"""Creating a space from the lobby (ADR 0021, decision 4; issue 37).

Create runs `contour init` and hands over: the new space's console opens with
the new-space flow as its first prompt, and the lobby drafts nothing itself.
The console that starts is the real one, under `$CONTOUR_CONSOLE_PYTHON`, with
the scripted stand-in for an agent so that no test reaches the SDK.
"""
import json
import os
import signal
import time
import unittest

from test_lobby_enter import LobbyEnterCase
from test_rename import RenameCase

STAND_IN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_stand_in.py")


class LobbyCreateCase(LobbyEnterCase):

    def open(self, **popen):
        self.made = []
        self.env["CONTOUR_CONSOLE_AGENT"] = f"{STAND_IN}:drive"
        self.prompt = self.tmp / "prompt"
        self.env["CONTOUR_AGENT_SCRIPT"] = json.dumps([{"keep_prompt": str(self.prompt)}])
        return super().open(**popen)

    def create(self, name, location=None, of=None):
        said = self.ask("/create", {"name": name,
                                    "location": str(location or self.spaces),
                                    **({"of": str(of)} if of else {})})
        if not said["refused"] and not said["next"]:
            self.made.append(said["path"])    # a console is coming up on it
        return said

    def listed(self, name):
        found = [s for s in self.ask("/spaces")["spaces"] if s["name"] == name]
        return found[0] if found else None

    def wait_for_console_on(self, name):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            consoles = [p for p in (self.listed(name) or {"presence": []})["presence"]
                        if p["kind"] == "console"]
            if consoles:
                return consoles
            time.sleep(0.1)
        self.fail(f"no console came up on {name}")

    def close_consoles(self):
        """Every console a create started, once it is up: one that came up
        after the test ended would outlive it."""
        from lib import presence
        for space in getattr(self, "made", []):
            deadline = time.monotonic() + 30
            while not presence.live(space) and time.monotonic() < deadline:
                time.sleep(0.1)
            for p in presence.live(space):
                os.kill(p["pid"], signal.SIGTERM)

    def made_by_hand(self, name):
        """What `contour init` makes, typed in a directory this lobby does not
        look in, so it is not a live space that takes the name."""
        elsewhere = self.tmp / "by-hand"
        elsewhere.mkdir(exist_ok=True)
        r = self.contour("init", name, cwd=elsewhere)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return elsewhere / name


class CreateTest(LobbyCreateCase):

    def test_create_makes_what_init_makes_by_hand_then_opens_its_console(self):
        by_hand = self.snapshot(self.made_by_hand("beta"))
        said = self.create("beta")
        self.assertIsNone(said["refused"])
        beta = self.spaces / "beta"
        self.assertEqual(said["path"], str(beta))
        made = self.snapshot(beta)
        self.assertEqual({k: v for k, v in made.items() if k in by_hand}, by_hand)
        self.assertEqual([k for k in made if k not in by_hand and
                          not k.startswith(".contour/")], [])
        self.wait_for_console_on("beta")

    def test_its_console_begins_on_the_new_space_flow(self):
        """The lobby drafts nothing: it hands over, and the drafting happens in
        the console, under its gates (ADR 0021, decision 4)."""
        self.create("beta")
        deadline = time.monotonic() + 30
        while not self.prompt.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertIn("new-space skill", self.prompt.read_text())


class NoEnvironmentTest(LobbyCreateCase):

    python = "/nowhere/python"

    def test_create_still_makes_the_space_and_says_how_to_go_on(self):
        """Making a space needs only the standard library, so a bare clone can
        do it; only the console it hands over to needs more."""
        said = self.create("beta")
        self.assertIsNone(said["refused"])
        self.assertIsNotNone(self.listed("beta"))
        self.assertIn("python3 -m venv .venv", said["next"])
        self.assertIn(f"cd {self.spaces / 'beta'}", said["next"])
        self.assertIn("contour-console --begin new-space", said["next"])
        time.sleep(1)                         # long enough for one started anyway to show
        self.assertFalse(self.prompt.exists())
        self.assertEqual(self.listed("beta")["presence"], [])


class LocationTest(LobbyCreateCase):

    def test_a_location_this_lobby_does_not_look_in_is_refused(self):
        """The new space would never appear in the list it was made from."""
        elsewhere = self.tmp / "elsewhere"
        said = self.create("beta", elsewhere)
        self.assertIn("this lobby looks in", said["refused"])
        self.assertIn("$CONTOUR_SPACES", said["refused"])
        self.assertFalse(elsewhere.exists())

    def test_a_folder_not_made_yet_inside_where_it_looks_is_made(self):
        """`project/` does not exist on a fresh clone, and is the default."""
        said = self.create("beta", self.spaces / "project")
        self.assertIsNone(said["refused"])
        self.assertTrue((self.spaces / "project" / "beta" / ".contour" / "project").exists())

    def test_the_page_is_offered_project_as_where_to_make_it(self):
        """`project/` in the toolkit, which this repo ignores and the push
        guard blocks (ADR 0021, decision 4) — when the lobby looks there."""
        from lib.lobby import CONTOUR
        project = CONTOUR.parent / "project"
        self.assertEqual(self.ask("/location")["default"], str(self.spaces))
        self.env["CONTOUR_SPACES"] = str(CONTOUR.parent.parent)
        self.open()
        self.assertEqual(self.ask("/location")["default"], str(project))

    def test_a_refused_name_makes_no_folder_either(self):
        self.create("Oak Chair", self.spaces / "project")
        self.assertFalse((self.spaces / "project").exists())


ILLEGAL = ("Oak Chair", "a/b", "../escape", "-dash", "x" * 65, "")


class InitRefusalTest(RenameCase):
    """`contour init` refuses before it writes anything: the command is the
    contract, so these are the lobby's refusals too (ADR 0021, decision 3)."""

    def init(self, *args, cwd):
        r = self.contour("init", *args, "--json", cwd=cwd)
        said = json.loads(r.stdout)
        self.assertNotEqual(r.returncode, 0)
        return said["refused"]

    def test_an_illegal_name_is_refused_and_nothing_is_made(self):
        for name in ILLEGAL:
            with self.subTest(name=name):
                before = sorted(self.tmp.rglob("*"))
                self.assertIn("not a name a space can have", self.init(name, cwd=self.spaces))
                self.assertEqual(sorted(self.tmp.rglob("*")), before)

    def test_a_name_a_live_space_holds_is_refused_wherever_it_is_typed(self):
        """A space's name is its identity, as `restore` already holds."""
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        self.assertIn("a live space is already called alpha",
                      self.init("alpha", cwd=elsewhere))
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_with_new_an_existing_directory_is_refused_and_left_alone(self):
        """Typed into a form, a name that matches a folder of somebody's is no
        reason to make that folder a git repository."""
        photos = self.spaces / "photos"
        photos.mkdir()
        (photos / "cat.jpg").write_bytes(b"not a model")
        self.assertIn("already exists", self.init("photos", "--new", cwd=self.spaces))
        self.assertEqual([p.name for p in photos.iterdir()], ["cat.jpg"])


class LobbyRefusalTest(LobbyCreateCase):

    def test_an_illegal_or_taken_name_is_refused_before_anything_is_made(self):
        (self.spaces / "photos").mkdir()
        for name in ("Oak Chair", "alpha", "photos"):
            with self.subTest(name=name):
                before = sorted(self.tmp.rglob("*"))
                said = self.create(name)
                self.assertTrue(said["refused"])
                self.assertEqual(sorted(self.tmp.rglob("*")), before)
        time.sleep(1)                         # long enough for one started anyway to show
        self.assertFalse(self.prompt.exists())


if __name__ == "__main__":
    unittest.main()
