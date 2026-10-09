"""Creating a variation of a space from the lobby (ADR 0021, decision 4; issue 38).

A variation is a new space, never a copy (ADR 0015): create, with a first prompt
that points at the source's `spec.yaml` and `build.py` for reference. Nothing is
copied, because a copied spec would arrive already agreed to.
"""
import time
import unittest

from test_lobby_create import LobbyCreateCase


class LobbyVariationCase(LobbyCreateCase):

    def setUp(self):
        super().setUp()
        (self.space / "build.py").write_text("# alpha's build\n")
        (self.space / "refs").mkdir(exist_ok=True)
        (self.space / "refs" / "front.png").write_bytes(b"alpha's picture")

    def vary(self, name, of=None):
        return self.create(name, of=of or self.space)

    def first_prompt(self):
        deadline = time.monotonic() + 30
        while not self.prompt.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        return self.prompt.read_text()


class VariationTest(LobbyVariationCase):

    def test_its_first_prompt_names_the_source_s_spec_and_build_as_reference(self):
        self.vary("alpha-lite")
        prompt = self.first_prompt()
        self.assertIn("variation of alpha", prompt)
        self.assertIn(str(self.space / "spec.yaml"), prompt)
        self.assertIn(str(self.space / "build.py"), prompt)
        self.assertIn("for reference", prompt)
        self.assertIn("new-space skill", prompt)

    def test_it_holds_what_init_makes_and_nothing_from_the_source(self):
        by_hand = self.snapshot(self.made_by_hand("alpha-lite"))
        said = self.vary("alpha-lite")
        self.assertIsNone(said["refused"])
        made = self.snapshot(self.spaces / "alpha-lite")
        self.assertEqual({k: v for k, v in made.items() if k in by_hand}, by_hand)
        self.assertEqual([k for k in made if k not in by_hand and
                          not k.startswith(".contour/")], [])
        self.first_prompt()

    def test_the_source_is_untouched_and_gets_no_presence_from_the_new_console(self):
        before = self.snapshot(self.space)
        self.vary("alpha-lite")
        self.wait_for_console_on("alpha-lite")
        self.assertEqual(self.snapshot(self.space), before)
        self.assertEqual(self.listed("alpha")["presence"], [])


class NoEnvironmentVariationTest(LobbyVariationCase):

    python = "/nowhere/python"

    def test_the_line_to_go_on_with_begins_the_variation_of_its_source(self):
        said = self.vary("alpha-lite")
        self.assertIsNone(said["refused"])
        self.assertIn(f"cd {self.spaces / 'alpha-lite'}", said["next"])
        self.assertIn(f"contour-console --begin variation --of {self.space}", said["next"])


class RefusedVariationTest(LobbyVariationCase):

    def test_a_source_the_lobby_does_not_list_is_refused_and_nothing_is_made(self):
        """`of` names a space of the page's, as a rename's path does: the
        prompt is about it, so it has to be one."""
        elsewhere = self.made_by_hand("gamma")
        for of in (elsewhere, self.tmp / "nowhere", self.spaces):
            with self.subTest(of=of):
                before = sorted(self.tmp.rglob("*"))
                said = self.vary("alpha-lite", of=of)
                self.assertTrue(said["refused"])
                self.assertEqual(sorted(self.tmp.rglob("*")), before)
        time.sleep(1)                         # long enough for one started anyway to show
        self.assertFalse(self.prompt.exists())


if __name__ == "__main__":
    unittest.main()
