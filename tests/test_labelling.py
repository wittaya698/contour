"""The lobby labels the unlabelled (ADR 0030, decision 7; issue 118).

One act over every space with no topics: one agent session reads each one's
last sheet and proposes for all of them together, from one vocabulary. It is
not a run: it holds no space and builds nothing, and each proposal waits in its
space as an approval. The agent is the stand-in, scripted per test.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import one_run    # noqa: E402,F401  one suite run per machine (issue 94)

from console import approvals, labelling    # noqa: E402
from console import last_run as console_last_run    # noqa: E402
from console.run import TOPICS_TOOL    # noqa: E402
from lib import cli, lock, presence, space, survey, topics    # noqa: E402
from lib.lobby import PAGE, Lobby, granted    # noqa: E402
from test_found import function    # noqa: E402

STAND_IN = f"{Path(__file__).resolve().parent / 'agent_stand_in.py'}:drive"


def proposal(name, *words, case="what it is"):
    return {"call": {"tool": TOPICS_TOOL, "model": name, "words": list(words),
                     "case": case}}


class Taken(Exception):
    """A request got as far as starting its console: nothing refused it."""


class LabellingCase(unittest.TestCase):
    """Spaces in a temporary directory `$CONTOUR_SPACES` points at, each a git
    repository with a sheet, as a space that has built has."""

    def setUp(self):
        self.spaces = Path(tempfile.mkdtemp()).resolve()
        patched = mock.patch.dict(os.environ, {"CONTOUR_SPACES": str(self.spaces),
                                               "CONTOUR_CONSOLE_AGENT": STAND_IN})
        patched.start()
        self.addCleanup(patched.stop)

    def made(self, name, *words, sheet=True):
        root = self.spaces / name
        (root / space.MARKER).parent.mkdir(parents=True)
        (root / space.MARKER).write_text("")
        (root / "spec.yaml").write_text("revision: 1\n")
        (root / ".gitignore").write_text(".contour/*\n!.contour/project\n")
        for w in words:
            topics.add(root, w)
        if sheet:
            here = space.layout(root)
            here.sheet.parent.mkdir(parents=True, exist_ok=True)
            here.sheet.write_bytes(b"\x89PNG\r\n\x1a\n")
        git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(git[:3] + ["init", "-q"], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "first"], check=True)
        return root

    def label(self, *steps):
        with mock.patch.dict(os.environ, {"CONTOUR_AGENT_SCRIPT": json.dumps(steps)}):
            return labelling.label()


class LabelTest(LabellingCase):

    def test_each_unlabelled_space_gets_one_proposal_waiting_and_a_labelled_one_none(self):
        beaky, cube = self.made("beaky"), self.made("trail-cube")
        wolf = self.made("wolf", "creature")
        self.label(proposal("beaky", "creature", "bird"),
                   proposal("trail-cube", "prop"))
        [waiting] = approvals.load(beaky)
        self.assertEqual((waiting["category"], waiting["call"]["words"]),
                         ("topics", ["creature", "bird"]))
        self.assertEqual([a["call"]["words"] for a in approvals.load(cube)], [["prop"]])
        self.assertEqual(approvals.load(wolf), [])

    def test_the_agent_is_given_each_unlabelled_sheet_and_the_words_in_use(self):
        beaky = self.made("beaky")
        wolf = self.made("wolf", "creature")
        kept = self.spaces.parent / (self.spaces.name + "-prompt.txt")
        self.label({"keep_prompt": str(kept)})
        told = kept.read_text()
        self.assertIn(f"beaky: {space.layout(beaky).sheet}", told)
        self.assertNotIn(str(space.layout(wolf).sheet), told)
        self.assertIn("creature (wolf)", told)

    def test_a_space_it_cannot_propose_for_now_is_skipped_and_says_why(self):
        self.made("beaky")
        self.made("blank", sheet=False)
        held = self.made("held")
        record = lock.take(held, "a test run")
        self.addCleanup(lock.release, held, record)
        open_ = self.made("open")
        with presence.present(open_, "console"):
            waits = self.made("waits")
            console_last_run.amend(waits, approvals=["build it"])
            kept = self.spaces.parent / (self.spaces.name + "-prompt.txt")
            said = self.label({"keep_prompt": str(kept)})
        self.assertEqual(said["proposing"], ["beaky"])
        self.assertEqual(sorted(said["skipped"]), ["blank", "held", "open", "waits"])
        self.assertIn("no sheet", said["skipped"]["blank"])
        for name in ("blank", "held", "open", "waits"):
            self.assertNotIn(f"{name}:", kept.read_text())


class AnsweredTest(LabellingCase):
    """Every proposal on one page, each answered for its own space."""

    def setUp(self):
        super().setUp()
        self.beaky, self.cube = self.made("beaky"), self.made("trail-cube")
        self.made("wolf", "creature", "quadruped")
        self.label(proposal("beaky", "Creature", "bird"),
                   proposal("trail-cube", "creature", "prop"))

    def test_one_reading_shows_a_proposal_per_space_with_its_new_words(self):
        shown = {p["name"]: p for p in labelling.shown()}
        self.assertEqual(sorted(shown), ["beaky", "trail-cube"])
        self.assertEqual(shown["beaky"]["words"], ["creature", "bird"])
        self.assertEqual(shown["beaky"]["new"], ["bird"])
        self.assertEqual(shown["trail-cube"]["new"], ["prop"])
        self.assertEqual(shown["beaky"]["case"], "what it is")

    def test_a_word_is_kept_for_one_space_and_struck_for_another(self):
        shown = {p["name"]: p for p in labelling.shown()}
        labelling.answered(str(self.beaky), shown["beaky"]["id"], ["creature", "bird"])
        labelling.answered(str(self.cube), shown["trail-cube"]["id"], ["prop"])
        self.assertEqual(topics.load(self.beaky), {"topics": ["creature", "bird"], "struck": []})
        self.assertEqual(topics.load(self.cube), {"topics": ["prop"], "struck": ["creature"]})
        self.assertEqual(labelling.shown(), [])

    def test_it_answers_a_topic_proposal_and_nothing_else_waiting(self):
        wolf = self.made("fox")
        kept = approvals.set_aside(wolf, "r1", "spec-write", "Write",
                                   {"file_path": "spec.yaml", "content": "revision: 2\n"},
                                   {"act": "Claude wants to change the spec"}, "a case")
        said = labelling.answered(str(wolf), kept["id"], ["creature"])
        self.assertFalse(said and said.get("answered"))
        self.assertEqual([a["id"] for a in approvals.load(wolf)], [kept["id"]])
        self.assertEqual((wolf / "spec.yaml").read_text(), "revision: 1\n")

    def test_while_it_waits_its_space_takes_a_request(self):
        """It blocks nothing (ADR 0030, decision 6 as amended; issue 122)."""
        # A ceiling, and no console really started: nothing refuses it.
        with mock.patch("lib.ceiling.read", return_value=300000), \
                mock.patch("lib.enter.requested", side_effect=Taken):
            with self.assertRaises(Taken):
                cli.requested("beaky", "paint it blue", "the nightly agent")

    def test_status_and_the_lobby_still_say_it_waits(self):
        act = "Claude suggests words to find this model by"
        self.assertEqual(survey.status(self.beaky)["approvals"], [act])
        [row] = [s for s in survey.listing()["spaces"] if s["name"] == "beaky"]
        self.assertEqual(row["approvals"], [act])

    def test_any_other_approval_waiting_refuses_it_and_is_the_only_one_named(self):
        approvals.set_aside(self.beaky, "r1", "spec-write", "Write",
                            {"file_path": "spec.yaml", "content": "revision: 2\n"},
                            {"act": "Claude wants to change the spec"}, "a case")
        console_last_run.amend(self.beaky, approvals=approvals.acts(self.beaky))
        with mock.patch("lib.ceiling.read", return_value=300000), \
                mock.patch("lib.enter.requested", side_effect=Taken):
            refused = cli.requested("beaky", "paint it blue", "the nightly agent")
        self.assertIn("beaky has 1 approval waiting", refused["why"])
        self.assertEqual(refused["approvals"], ["Claude wants to change the spec"])

    def test_no_file_git_tracks_changes_before_its_proposal_is_answered(self):
        for root in (self.beaky, self.cube):
            said = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                                  capture_output=True, text=True).stdout
            self.assertEqual(said, "", root.name)


class AllowedTest(LabellingCase):
    """What the act's agent may do: read the sheets it was given, and propose
    once for each model it was given. Nothing else, and nothing in a space."""

    def setUp(self):
        super().setUp()
        self.beaky = self.made("beaky")
        self.wolf = self.made("wolf", "creature")
        self.spaces_in, _ = labelling.taken(survey.listing())

    def allowed(self, tool, **payload):
        return labelling.allowed(self.spaces_in, set(), tool, payload)

    def test_it_reads_a_sheet_it_was_given_and_nothing_else(self):
        self.assertIsNone(self.allowed("Read", file_path=str(space.layout(self.beaky).sheet)))
        self.assertIsNotNone(self.allowed("Read", file_path=str(self.beaky / "spec.yaml")))
        self.assertIsNotNone(self.allowed("Read", file_path=str(space.layout(self.wolf).sheet)))
        self.assertIsNotNone(self.allowed("Bash", command="ls"))

    def test_it_proposes_once_for_a_model_it_was_given(self):
        self.assertIsNone(self.allowed(TOPICS_TOOL, model="beaky", words=["bird"]))
        self.assertIsNotNone(self.allowed(TOPICS_TOOL, model="wolf", words=["bird"]))
        self.assertIsNotNone(labelling.allowed(self.spaces_in, {"beaky"}, TOPICS_TOOL,
                                               {"model": "beaky", "words": ["bird"]}))


class LobbyTest(LabellingCase):
    """The act as the lobby starts it and answers it: under the console's
    interpreter, which here is this one, with the stand-in for the agent."""

    def setUp(self):
        super().setUp()
        patched = mock.patch.dict(os.environ, {"CONTOUR_CONSOLE_PYTHON": sys.executable})
        patched.start()
        self.addCleanup(patched.stop)
        self.beaky, self.cube = self.made("beaky"), self.made("trail-cube")
        self.made("blank", sheet=False)
        self.lobby = Lobby(survey.listing, grace=None)

    def settled(self):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            said = self.lobby.labels({})
            if not said["labelling"]:
                return said
            time.sleep(0.05)
        self.fail("the act never ended")

    def test_started_it_says_what_it_proposes_for_and_the_page_answers_each(self):
        with mock.patch.dict(os.environ, {"CONTOUR_AGENT_SCRIPT": json.dumps([
                proposal("beaky", "creature"), proposal("trail-cube", "creature")])}):
            started = self.lobby.label({})
        self.assertEqual(started["proposing"], ["beaky", "trail-cube"])
        self.assertEqual(list(started["skipped"]), ["blank"])
        shown = {p["name"]: p for p in self.settled()["proposals"]}
        self.assertEqual(sorted(shown), ["beaky", "trail-cube"])
        said = self.lobby.labelled({"path": str(self.cube), "id": shown["trail-cube"]["id"],
                                    "words": []})
        self.assertEqual(said["outcome"], "struck")
        self.assertEqual(topics.load(self.cube)["struck"], ["creature"])
        self.assertEqual([p["name"] for p in self.lobby.labels({})["proposals"]], ["beaky"])

    def test_it_is_offered_only_where_the_console_can_run(self):
        self.assertIn("label", granted())
        with mock.patch.dict(os.environ, {"CONTOUR_CONSOLE_PYTHON": "/nowhere/python"}):
            self.assertNotIn("label", granted())


@unittest.skipUnless(shutil.which("node"), "no node")
class PageUnlabelledTest(unittest.TestCase):
    """Which spaces the page offers to label, run under node as the browser
    gets it, over rows as `/spaces` serves them."""

    def test_it_offers_the_spaces_with_no_topics(self):
        rows = [{"name": "beaky", "topics": ["bird"]}, {"name": "blank", "topics": []}]
        js = (function(PAGE.read_text(encoding="utf-8"), "unlabelled")
              + f"console.log(JSON.stringify(unlabelled({json.dumps(rows)}).map(s => s.name)));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(json.loads(out.stdout or "null"), ["blank"], out.stderr)


class PageTest(unittest.TestCase):
    """What the page draws, read from its source as the other page tests read it."""

    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")

    def test_the_act_is_offered_where_the_host_can_and_a_space_has_no_topics(self):
        render = function(self.page, "render")
        self.assertIn("can.has('label')", render)
        self.assertIn("unlabelled(spaces)", render)
        self.assertIn("'/label'", self.page)

    def test_a_card_ticks_each_word_marks_the_new_and_sends_the_ticked(self):
        card = function(self.page, "proposed")
        self.assertIn("checkbox", card)
        self.assertIn("p.new", card)
        self.assertIn("p.case", card)
        self.assertIn("'/labelled'", card)
        self.assertIn(".checked", card)


class DriverTest(unittest.TestCase):
    """The act as the real SDK is handed it, read on the console's interpreter."""

    def test_its_agent_proposes_by_model_and_has_only_read_besides(self):
        python = ROOT / ".venv" / "bin" / "python"
        if not python.exists():
            self.skipTest("no console environment")
        done = subprocess.run([str(python), "-c", (
            "from console import labelling\n"
            "[t] = labelling.tools({'creature': ['wolf']})\n"
            "print(t.name, sorted(t.input_schema['required']))\n"
            "print('creature (wolf)' in t.description)\n"
            "o = labelling.options()\n"
            "print(o['tools'], o['setting_sources'])\n")],
            cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(done.stdout.splitlines(), [
            "topics_propose ['case', 'model', 'words']", "True", "['Read'] []"],
            done.stderr)


if __name__ == "__main__":
    unittest.main()
