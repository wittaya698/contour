"""Export from the console, and the file handed over (ADR 0025, decision 5; issue 71).

Two ways in and one result. The page's button spawns `contour export` the way
the console spawns everything — no agent turn — and only on a green build; the
agent may still export inside a run. Either way one card says what the file is,
who made it, and whether it reopens the same as it was built. These drive the
console as a person does, with a stubbed Blender standing in for the stages.
"""
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from test_console import ConsoleCase    # noqa: E402
from test_launcher import stages, stub_blender    # noqa: E402


class ButtonTest(ConsoleCase):

    def built(self, ok=True, **stub):
        """A space whose last check came to `ok`, checked the way a person
        checks one, and the Blender its console will export with."""
        space = self.space()
        blender = str(stub_blender(space, ok=ok, **stub))
        subprocess.run([sys.executable, str(ROOT / "contour"), "check"], cwd=str(space),
                       capture_output=True, text=True, timeout=60,
                       env=dict(os.environ, BLENDER=blender))
        return space, blender

    def test_the_button_exports_with_no_agent_turn_and_the_card_shows_the_file(self):
        space, blender = self.built()
        _, url = self.launch(space, BLENDER=blender, CONTOUR_HOME=tempfile.mkdtemp())
        _, said = self.ask(url, "/export", {})
        self.assertTrue(said["exported"], said)
        self.assertEqual(stages(space)[-2:], ["export", "roundtrip"])
        self.assertEqual(self.ask(url, "/events?since=0")[1]["events"], [])
        card = said["card"]
        self.assertEqual(card["name"], f"{space.name}.glb")
        self.assertEqual(card["size"], "15 bytes")
        self.assertEqual(card["by"], "you")
        self.assertEqual(card["roundtrip"], "checked: it reopens the same as it was built")

    def test_a_red_build_is_not_offered_for_export(self):
        """Refused by the console as well as the page, so a stale tab whose
        button was still lit cannot hand over a model that does not match."""
        space, blender = self.built(ok=False)
        _, url = self.launch(space, BLENDER=blender, CONTOUR_HOME=tempfile.mkdtemp())
        self.assertEqual(self.ask(url, "/export")[1]["offered"],
                         {"can": False, "why": "fix the failing checks first"})
        _, said = self.ask(url, "/export", {})
        self.assertFalse(said["exported"])
        self.assertNotIn("export", stages(space))

    def test_during_a_run_the_button_waits_for_it(self):
        """Export takes the space's hold, and a run is holding it — here, parked
        at a gate the user has not answered."""
        space, blender = self.built()
        _, url = self.driven({"call": {"tool": "Bash", "command": "git push"}},
                             space=space, BLENDER=blender)
        self.ask(url, "/run", {"prompt": "go on"})
        self.gate(url)
        self.assertEqual(self.ask(url, "/export")[1]["offered"],
                         {"can": False, "why": "finish or end the run first"})
        self.assertFalse(self.ask(url, "/export", {})[1]["exported"])
        self.assertNotIn("export", stages(space))

    def test_an_export_claude_made_in_a_run_shows_on_the_same_card(self):
        """The other way in: a `build`-category call, gated like one, and
        allowed. The card says who made it, since nobody pressed anything."""
        space, blender = self.built()
        _, url = self.driven({"call": {"tool": "Bash", "command": "contour export"},
                              "execute": True}, space=space, BLENDER=blender)
        self.assertIsNone(self.ask(url, "/export")[1]["card"])
        self.ask(url, "/run", {"prompt": "export it"})
        gate, _ = self.gate(url)
        self.ask(url, "/verdict", {"id": gate["id"], "allow": True})
        self.transcript(url, lambda ev: any(e["kind"] == "result" for e in ev))
        card = self.ask(url, "/export")[1]["card"]
        self.assertEqual(card["by"], "claude")
        self.assertEqual(card["name"], f"{space.name}.glb")

    def test_a_file_that_reopens_differently_says_what_differed(self):
        """In the verdict's own sentences (`lib/verdict.py`), so the card and
        the build panel say one thing one way."""
        space, blender = self.built(differs=True)
        _, url = self.launch(space, BLENDER=blender, CONTOUR_HOME=tempfile.mkdtemp())
        card = self.ask(url, "/export", {})[1]["card"]
        self.assertEqual(card["roundtrip"], "it reopens differently from how it was built")
        self.assertEqual(card["differs"], ["Height is 1640 mm; the spec wants 1700, give or take 5."])

    def test_a_build_after_the_export_marks_the_card_older(self):
        """The file is of the build it was exported from. Another check
        regenerates the `.blend` from zero (rule 3) — written here by hand, as
        the stub Blender writes no geometry — and the card says so."""
        space, blender = self.built()
        _, url = self.launch(space, BLENDER=blender, CONTOUR_HOME=tempfile.mkdtemp())
        self.assertFalse(self.ask(url, "/export", {})[1]["card"]["older"])
        (space / "out").mkdir(exist_ok=True)
        (space / "out" / f"{space.name}.blend").write_bytes(b"a newer build")
        self.assertTrue(self.ask(url, "/export")[1]["card"]["older"])

    def test_download_hands_over_the_file_byte_for_byte_and_finder_shows_it(self):
        """Downloaded as the page downloads it, a GET carrying the token in the
        query; revealed by `$CONTOUR_REVEAL`, which stands in for Finder the way
        `$BLENDER` stands in for Blender."""
        space, blender = self.built()
        shown = Path(tempfile.mkdtemp())
        reveal = shown / "reveal"
        reveal.write_text(f'#!/bin/sh\necho "$@" > "{shown / "args"}"\n')
        reveal.chmod(0o755)
        _, url = self.launch(space, BLENDER=blender, CONTOUR_HOME=tempfile.mkdtemp(),
                             CONTOUR_REVEAL=str(reveal))
        self.ask(url, "/export", {})
        glb = space / "exports" / f"{space.name}.glb"
        origin, token = url.split("/?")[0], url.split("t=")[1]
        with urllib.request.urlopen(f"{origin}/export.glb?t={token}", timeout=10) as r:
            self.assertEqual(r.read(), glb.read_bytes())
            self.assertEqual(r.headers["Content-Type"], "model/gltf-binary")
        self.assertTrue(self.ask(url, "/reveal", {})[1]["revealed"])
        self.assertEqual(Path((shown / "args").read_text().strip()).resolve(), glb.resolve())


class RecordTest(unittest.TestCase):
    """The record both doors write, read without a console."""

    def test_an_export_that_wrote_no_file_takes_the_old_card_down(self):
        """An export unlinks the last file before it writes (`cmd_export`), so
        one that failed leaves nothing to hand over, and a card still naming
        the last file would be offering a download of a file that is gone."""
        from lib import exported
        dot, glb = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp()) / "beaky.glb"
        blend = dot / "beaky.blend"
        glb.write_bytes(b"x" * 2048)
        exported.record(dot / exported.NAME, {"ok": True}, glb, blend)
        self.assertEqual(exported.card(dot / exported.NAME, blend)["size"], "2 KB")
        glb.unlink()
        exported.record(dot / exported.NAME, {"ok": False, "lines": ["FAIL"]}, glb, blend)
        self.assertIsNone(exported.card(dot / exported.NAME, blend))
        self.assertFalse((dot / exported.NAME).exists())


class PageTest(unittest.TestCase):
    """The page's source, as `test_always.PageTest` reads it."""

    def setUp(self):
        from lib.canvas import PAGE
        self.page = PAGE.read_text(encoding="utf-8")
        self.section = self.page.split('<section id="export"', 1)[1].split("</section>", 1)[0]

    def test_the_console_page_has_the_button_and_the_card(self):
        self.assertIn('data-needs="drive"', self.section.split(">", 1)[0])
        for words in ("Export", "Download", "Show in Finder",
                      "older than the last build — export again"):
            self.assertIn(words, self.section)

    def test_the_page_asks_offers_downloads_and_reveals(self):
        # The poll and what it draws, up to the button's own handler.
        script = self.page.split("async function refreshExport(", 1)[1] \
                          .split("async function exportIt(", 1)[0]
        self.assertIn("'/export'", script)
        self.assertIn("offered.why", script)
        self.assertIn("asset('/export.glb')", self.page)
        self.assertIn("'/reveal'", self.page)


if __name__ == "__main__":
    unittest.main()
