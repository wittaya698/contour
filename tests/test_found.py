"""Spaces are found by topic (ADR 0030, decision 8; issue 115).

Wherever spaces are listed they can be filtered on a topic, and the answer is
the names and their approved topics and nothing else, so an agent in one space
reads the vocabulary without reading another model. Spaces here are a marker
and a `topics.json` under a temporary directory `$CONTOUR_SPACES` points at.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import space, survey, topics    # noqa: E402
from lib.lobby import PAGE    # noqa: E402


class Spaces(unittest.TestCase):
    """Spaces made in a temporary directory, labelled as the user labels them."""

    def setUp(self):
        self.spaces = Path(tempfile.mkdtemp()).resolve()
        patched = mock.patch.dict(os.environ, {"CONTOUR_SPACES": str(self.spaces)})
        patched.start()
        self.addCleanup(patched.stop)

    def made(self, name, *words):
        root = self.spaces / name
        (root / space.MARKER).parent.mkdir(parents=True)
        (root / space.MARKER).write_text("")
        for w in words:
            topics.add(root, w)
        return root


class FoundTest(Spaces):

    def test_a_topic_finds_the_spaces_carrying_it_by_name_and_topics(self):
        self.made("beaky", "creature", "bird")
        self.made("crate", "prop")
        self.made("wolf", "creature")
        self.assertEqual(survey.found("creature"),
                         [{"name": "beaky", "topics": ["creature", "bird"]},
                          {"name": "wolf", "topics": ["creature"]}])

    def test_a_space_with_no_topics_is_listed_and_missed_by_every_filter(self):
        self.made("beaky", "creature")
        self.made("blank")
        self.assertEqual([s["name"] for s in survey.found("creature")], ["beaky"])
        self.assertEqual(survey.found(""), [])
        rows = {s["name"]: s["topics"] for s in survey.listing()["spaces"]}
        self.assertEqual(rows, {"beaky": ["creature"], "blank": []})

    def test_the_spelling_asked_is_the_spelling_kept(self):
        """A filter is normalised as a topic is, and matches a whole word."""
        self.made("beaky", "creature")
        self.assertEqual([s["name"] for s in survey.found("  Creature ")], ["beaky"])
        self.assertEqual(survey.found("crea"), [])

    def test_a_word_in_a_spec_or_a_reference_is_not_a_topic(self):
        """Only the approved words answer: a spec that says *creature* or a
        reference called it does not make the model one."""
        root = self.made("beaky")
        (root / "spec.yaml").write_text("name: beaky\ntopics: [creature]\n")
        (root / "refs").mkdir()
        (root / "refs" / "creature.png").write_bytes(b"\x89PNG")
        self.assertEqual(survey.found("creature"), [])


class VocabularyTest(Spaces):
    """Every word in use and who carries it, as a proposal is given it
    (ADR 0030, decision 3; issue 116)."""

    def test_each_word_in_use_names_the_spaces_carrying_it(self):
        self.made("beaky", "creature", "bird")
        self.made("wolf", "creature")
        root = self.made("crate")
        (root / "spec.yaml").write_text("name: crate\ntopics: [prop]\n")
        self.assertEqual(survey.vocabulary(),
                         {"creature": ["beaky", "wolf"], "bird": ["beaky"]})


class SpacesCommandTest(Spaces):
    """`contour spaces` as a person or an agent in another space runs it."""

    def contour(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "contour"), *args],
                              cwd=str(self.spaces), env=dict(os.environ),
                              capture_output=True, text=True, timeout=60)

    def test_each_row_shows_its_topics(self):
        self.made("beaky", "creature", "bird")
        self.made("blank")
        said = self.contour("spaces").stdout
        self.assertIn("topics creature, bird", said)
        self.assertEqual(said.count("topics"), 1, said)

    def test_a_topic_lists_the_names_carrying_it_and_their_topics(self):
        self.made("beaky", "creature", "bird")
        self.made("crate", "prop")
        r = self.contour("spaces", "--topic", "Creature")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.split(), ["beaky", "creature,", "bird"])

    def test_a_topic_nobody_carries_says_so(self):
        self.made("beaky", "creature")
        r = self.contour("spaces", "--topic", "vehicle")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("no model is labelled vehicle", r.stdout)


class ConnectorTest(Spaces):
    """`contour mcp` as Desktop runs it: *which models are creature?*"""

    def asked(self, **arguments):
        r = subprocess.run(
            [sys.executable, str(ROOT / "contour"), "mcp"], cwd=str(self.spaces),
            input="".join(json.dumps(m) + "\n" for m in (
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                 "params": {"name": "spaces", "arguments": arguments}})),
            env=dict(os.environ), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        _, called = [json.loads(l) for l in r.stdout.splitlines()]
        self.assertFalse(called["result"]["isError"], called)
        return json.loads(called["result"]["content"][0]["text"])

    def test_a_topic_is_answered_with_names_and_topics_only(self):
        root = self.made("beaky", "creature", "bird")
        (root / "spec.yaml").write_text("name: beaky\n")
        self.made("crate", "prop")
        self.assertEqual(self.asked(topic="creature"),
                         {"spaces": [{"name": "beaky", "topics": ["creature", "bird"]}]})

    def test_without_a_topic_it_is_the_listing_with_topics_in_each_row(self):
        self.made("beaky", "creature")
        said = self.asked()
        self.assertEqual([(s["name"], s["topics"]) for s in said["spaces"]],
                         [("beaky", ["creature"])])
        self.assertIn("roots", said, "unfiltered, it is `contour spaces --json`")


def function(page, name):
    """One top-level function of the page's script, to its closing brace."""
    return f"function {name}(" + page.split(f"function {name}(")[1].split("\n}\n")[0] + "\n}\n"


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class LobbyFilterTest(unittest.TestCase):
    """The lobby's filter, its two functions run under node as the browser
    gets them, over rows as `/spaces` serves them."""

    ROWS = [{"name": "beaky", "topics": ["creature", "bird"]},
            {"name": "blank", "topics": []},
            {"name": "wolf", "topics": ["creature"]}]

    def run_page(self, expression):
        page = PAGE.read_text(encoding="utf-8")
        js = (function(page, "inUse") + function(page, "labelled")
              + f"const rows = {json.dumps(self.ROWS)};\n"
              + f"console.log(JSON.stringify({expression}));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_the_picker_offers_every_topic_in_use_once(self):
        self.assertEqual(self.run_page("inUse(rows)"), ["bird", "creature"])

    def test_a_topic_shows_the_rows_carrying_it(self):
        self.assertEqual(self.run_page("labelled(rows, 'creature').map(s => s.name)"),
                         ["beaky", "wolf"])
        self.assertEqual(self.run_page("labelled(rows, 'crea')"), [],
                         "a whole word, as the picker offers it")

    def test_no_topic_shows_every_row_and_one_without_topics_only_then(self):
        self.assertEqual(self.run_page("labelled(rows, '').map(s => s.name)"),
                         ["beaky", "blank", "wolf"])
        self.assertEqual(self.run_page("labelled(rows, 'bird').map(s => s.name)"),
                         ["beaky"])


class LobbyPageTest(unittest.TestCase):
    """What the page draws from the filter, read from its source as the other
    lobby page tests read it."""

    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")

    def test_a_row_shows_its_topics(self):
        self.assertIn("s.topics", function(self.page, "row"))

    def test_the_list_is_drawn_through_the_filter(self):
        listed = self.page.split('id="list"')[1].split("</table>")[0]
        self.assertIn('id="topic"', listed)
        render = function(self.page, "render")
        self.assertIn("inUse(spaces)", render)
        self.assertIn("labelled(spaces, ", render)


if __name__ == "__main__":
    unittest.main()
