"""References dropped on the lobby's create (ADR 0024, decision 11; issue 65).

The page reads each file raw and sends it base64 inside the create request's
JSON; the lobby checks every one before `contour init` runs, so a bad drop is
refused whole and no space is made. The console that starts is the real one,
with the scripted stand-in for an agent.
"""
import base64
import unittest

from test_lobby_create import LobbyCreateCase


def dropped(name, data):
    """A file as the page sends it: its name, and its bytes read raw."""
    return {"name": name, "data": base64.b64encode(data).decode("ascii")}


class LobbyReferencesCase(LobbyCreateCase):

    JPEG = b"\xff\xd8\xff\xe0 a photo of the front"
    PNG = b"\x89PNG\r\n\x1a\n a drawing of the side"

    def create(self, name, location=None, of=None, references=()):
        said = self.ask("/create", {"name": name,
                                    "location": str(location or self.spaces),
                                    "references": list(references),
                                    **({"of": str(of)} if of else {})})
        if not said["refused"] and not said["next"]:
            self.made.append(said["path"])    # a console is coming up on it
        return said


class DroppedTest(LobbyReferencesCase):

    def test_dropped_references_land_in_refs_byte_for_byte(self):
        said = self.create("beta", references=[dropped("front.jpg", self.JPEG),
                                               dropped("side.png", self.PNG)])
        self.assertIsNone(said["refused"])
        refs = self.spaces / "beta" / "refs"
        self.assertEqual((refs / "front.jpg").read_bytes(), self.JPEG)
        self.assertEqual((refs / "side.png").read_bytes(), self.PNG)
        self.wait_for_console_on("beta")

    def test_a_variation_takes_them_too(self):
        said = self.create("alpha-2", location=self.spaces, of=self.space,
                           references=[dropped("front.jpg", self.JPEG)])
        self.assertIsNone(said["refused"])
        refs = self.spaces / "alpha-2" / "refs"
        self.assertEqual(sorted(p.name for p in refs.iterdir()), ["front.jpg"])
        self.assertEqual((refs / "front.jpg").read_bytes(), self.JPEG)
        self.wait_for_console_on("alpha-2")


class RefusedTest(LobbyReferencesCase):
    """Every file is checked before `contour init` runs, so a bad drop is
    refused whole, names the file, and leaves no space behind."""

    def refused(self, bad, named):
        said = self.create("beta", references=[dropped("front.jpg", self.JPEG), bad])
        self.assertIsNone(said["path"])
        self.assertIn(named, said["refused"])
        self.assertFalse((self.spaces / "beta").exists())
        return said["refused"]

    def test_a_file_that_is_not_an_image_is_refused(self):
        self.refused(dropped("notes.png", b"just some text"), "notes.png")

    def test_a_name_that_says_another_kind_is_refused(self):
        self.refused(dropped("side.jpg", self.PNG), "side.jpg")

    def test_a_file_that_will_not_decode_is_refused(self):
        self.refused({"name": "side.png", "data": "not base64 at all!"}, "side.png")

    def test_a_file_over_the_cap_is_refused(self):
        from lib.lobby import REFERENCE_CAP
        big = self.PNG + b"\0" * REFERENCE_CAP
        self.assertIn("MB", self.refused(dropped("huge.png", big), "huge.png"))

    def test_a_name_that_is_a_path_is_refused(self):
        for name in ("../side.png", "sub/side.png", ".png"):
            with self.subTest(name=name):
                self.refused(dropped(name, self.PNG), name)

    def test_two_files_of_one_name_are_refused(self):
        self.refused(dropped("front.jpg", self.JPEG), "front.jpg")


if __name__ == "__main__":
    unittest.main()
