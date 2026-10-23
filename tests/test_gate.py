"""A gate says the act and what changes (ADR 0025, decision 6; issue 68).

A gate used to read as its category and the raw call: *SPEC-WRITE*, then a
heredoc. These hold what it says instead — what Claude wants to do, in plain
words from one table keyed by category, and for a spec write each field that
moves — with the raw call kept, one click away.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from console.run import SPEC_TOOL    # noqa: E402
from lib import gate, marks    # noqa: E402
from lib.canvas import PAGE    # noqa: E402
from test_console import ConsoleCase    # noqa: E402
from test_found import function    # noqa: E402


class NamedAsWrittenTest(unittest.TestCase):
    """A case names a number the way a person writes it (issue 155).

    A new space's first spec write was refused for not naming 8000, in a case
    that said *About 8,000 triangles*: the way *Speaking to the user* tells the
    agent to say a triangle budget.
    """

    def unargued(self, case):
        spec = Path(self.enterContext(tempfile.TemporaryDirectory())) / "spec.yaml"
        call = {"file_path": str(spec),
                "content": "revision: 1\ntopology:\n  tri_budget: 8000\n"}
        return gate.unargued(spec, "Write", call, case)

    def test_a_number_with_its_thousands_marked_is_that_number(self):
        for case in ("About 8,000 triangles.", "8 000 triangles", "8000 triangles"):
            with self.subTest(case=case):
                self.assertEqual(self.unargued(case), [])

    def test_a_list_of_numbers_is_still_each_number(self):
        """*10, 000* is not ten thousand, and *1,024* is."""
        self.assertEqual(self.unargued("sizes 80, 00 and 8,00"), ["8000"])


class WordsTest(unittest.TestCase):

    def test_every_category_the_launcher_prints_has_a_plain_sentence(self):
        """Read off `contour intents`, the list an ask-list is audited against,
        so a category the toolkit gains fails here until somebody says what it
        means in words."""
        printed = subprocess.run([sys.executable, str(ROOT / "contour"), "intents"],
                                 capture_output=True, text=True, timeout=30)
        categories = printed.stdout.split()
        self.assertIn("spec-write", categories, "the launcher printed them")
        self.assertEqual(sorted(set(categories) - set(gate.WORDS)), [])

    def test_a_category_the_table_does_not_know_shows_its_own_name(self):
        said = gate.say("paint-write", "/nowhere", "Bash", {"command": "x"})
        self.assertEqual((said["act"], said["allow"], said["deny"]),
                         ("paint-write", "Allow", "Deny"))


class ChangesTest(unittest.TestCase):
    """A spec write read ahead of running it, against the spec on disk."""

    def setUp(self):
        import tempfile
        self.spec = Path(tempfile.mkdtemp()) / "spec.yaml"
        self.spec.write_text(SPEC)

    def test_a_whole_new_spec_is_read_field_by_field(self):
        will = SPEC.replace("seat_depth: { value: 600, tol: 20 }",
                            "seat_depth: { value: 600, tol: 20, part: seat }")
        will = will.replace("tri_budget: 2000", "tri_budget: 2400\n  doubles_tolerance_mm: 0.1")
        self.assertEqual(gate.changes(self.spec, "Write", {"content": will}),
                         ["seat depth part none → seat",
                          "topology tri budget 2000 → 2400",
                          "topology doubles tolerance none → 0.1 mm"])

    def test_a_moved_note_is_shown_as_itself_and_no_other(self):
        """A list's items have no names, so it moved as one value and was shown
        whole, nine notes before and nine after (issue 111)."""
        self.spec.write_text(SPEC + NOTES)
        will = SPEC + NOTES.replace("~170 proud", "~191 proud")
        self.assertEqual(gate.changes(self.spec, "Write", {"content": will}),
                         ["notes 2: … diameter, ~170 → ~191 proud …"])

    def test_a_note_added_or_removed_says_which(self):
        self.spec.write_text(SPEC + NOTES)
        removed = NOTES.replace('  - "Faces -Y (Blender front)."\n', "")
        added = removed + '  - "Seams are not modelled."\n'
        self.assertEqual(gate.changes(self.spec, "Write", {"content": SPEC + added}),
                         ["notes 1 removed: Faces -Y (Blender front).",
                          "notes 3 added: Seams are not modelled."])

    def test_the_revision_it_moves_is_listed_with_the_fields(self):
        """Left out, a bumped write read as an unbumped one, and was denied for
        it (issue 126)."""
        will = SPEC.replace("revision: 2", "revision: 3").replace("value: 600", "value: 640")
        self.assertEqual(gate.changes(self.spec, "Write", {"content": will}),
                         ["revision 2 → 3", "seat depth 600 → 640 mm"])

    def test_the_revision_alone_is_listed_and_still_part_of_a_change(self):
        """Listing it changes what a gate shows, not what reaches one: a write
        of the bump alone is refused before any gate (issue 104)."""
        call = {"content": SPEC.replace("revision: 2", "revision: 3")}
        self.assertEqual(gate.changes(self.spec, "Write", call), ["revision 2 → 3"])
        self.assertTrue(gate.partial(self.spec, "Write", call))

    def test_a_shell_call_cannot_be_read_ahead_and_lists_nothing(self):
        """The raw call is what is left to read, as it was before."""
        self.assertEqual(gate.changes(self.spec, "Bash",
                                      {"command": "sed -i s/600/640/ spec.yaml"}), [])


class SaysTest(ConsoleCase):
    """What the console's gate carries to the page, raised by a scripted agent
    as `test_console.RunTest` raises one."""

    def said(self, *script, **env):
        _, url = self.driven(*script, **env)
        self.ask(url, "/run", {"prompt": "go on"})
        return self.gate(url)[0]["said"]

    def test_a_commit_gate_asks_to_save_this_version(self):
        said = self.said({"call": {"tool": "Bash", "command": "git commit -m seat"}})
        self.assertEqual((said["act"], said["allow"], said["deny"]),
                         ("Save this version?", "Save", "Not yet"))


    def test_a_spec_write_lists_each_field_that_moves_old_to_new(self):
        """In millimetres where it is one, and only what moves: the revision
        bump among them, since a gate that hid it showed a bumped write as an
        unbumped one (issue 126)."""
        space = self.space()
        (space / "spec.yaml").write_text(SPEC)
        said = self.said({"call": {"tool": SPEC_TOOL,
                                   "content": SPEC.replace("value: 600, tol: 20",
                                                           "value: 640, tol: 3")
                                                  .replace("revision: 2", "revision: 3"),
                                   "case": "Seat depth reads 640 mm ±3 on span m2, "
                                           "against 600 ±20."}},
                         space=space)
        self.assertEqual(said["act"], "Claude wants to change the spec")
        self.assertEqual(said["changes"], ["revision 2 → 3",
                                           "seat depth 600 → 640 mm",
                                           "seat depth tolerance 20 → 3 mm"])

    def test_a_spec_write_names_the_span_its_case_measured_on(self):
        """The case is what the write carries (ADR 0029), so the span is read
        from it — and only a span this space holds is named, so a plain mark
        the case mentions is not taken for one."""
        space = self.space()
        (space / "spec.yaml").write_text(SPEC)
        held = space / marks.NAME
        marks.on_reference(held, "side.png", [10, 40], "where the back starts")
        marks.on_reference(held, "side.png", [10, 50], "seat depth", to=[300, 50])
        said = self.said({"call": {"tool": SPEC_TOOL,
                                   "content": SPEC.replace("value: 600", "value: 640")
                                                  .replace("revision: 2", "revision: 3"),
                                   "case": "Seat depth reads 640 mm ±3 on span m2, "
                                           "against 600 ±20; m1 is where the back "
                                           "starts."}},
                         space=space)
        self.assertEqual(said["spans"], ["m2"])
        self.assertEqual(said["changes"], ["revision 2 → 3", "seat depth 600 → 640 mm"])


class GatePageTest(unittest.TestCase):
    """The page's source, because there is no browser here: what a gate is
    built from, as `test_canvas` reads the template it is cloned from."""

    def setUp(self):
        page = PAGE.read_text(encoding="utf-8")
        self.template = page.split('<template id="gate">', 1)[1].split("</template>", 1)[0]
        self.script = page.split("function gate(", 1)[1].split("\n}\n", 1)[0]

    def test_the_gate_reads_as_the_act_and_what_changes(self):
        for part in ('class="act"', 'class="changes"', 'class="spans"'):
            self.assertIn(part, self.template)
        for read in ("said.act", "said.changes", "said.spans", "said.allow", "said.deny"):
            self.assertIn(read, self.script)

    def test_the_raw_call_is_one_click_away_and_not_shown_by_default(self):
        raw = self.template.split("<details", 1)[1].split("</details>", 1)[0]
        self.assertIn('class="call"', raw)
        self.assertNotIn("open", raw.split(">", 1)[0], "closed until clicked")
        self.assertEqual(self.template.count('class="call"'), 1)

    def test_the_category_word_is_no_longer_the_heading(self):
        """*SPEC-WRITE* is the term; the page names the act (ADR 0025, 1)."""
        self.assertNotIn('class="category"', self.template)

    def test_a_verdict_closes_the_gate_it_answers(self):
        """The transcript's verdict names its gate, and the page closes that
        gate on it — not on the click. A reloaded tab replays the gate and the
        verdict and never clicked anything; drawn from the click, it would offer
        Allow on a call that already ran."""
        page = PAGE.read_text(encoding="utf-8")
        turn = page.split("function turn(", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("event.kind === 'verdict'", turn)
        self.assertIn("li.dataset.gate = event.id", self.script)
        # Declared once: a page script's later function of the same name wins.
        self.assertEqual(page.count("function closeGate("), 1)
        answered = page.split("function closeGate(", 1)[1].split("\n}\n", 1)[0]
        self.assertIn('[data-gate="${event.id}"]', answered)
        self.assertIn("said.allow", answered)
        self.assertIn("said.deny", answered)


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class ExactCallTest(unittest.TestCase):
    """The raw call as the page writes it, run under node as the browser gets it."""

    def called(self, tool, call):
        js = (function(PAGE.read_text(encoding="utf-8"), "called")
              + f"console.log(JSON.stringify(called({json.dumps({'tool': tool, 'call': call})})));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        return json.loads(out.stdout or "null") or self.fail(out.stderr)

    def test_an_edit_shows_the_text_it_replaces_and_the_text_it_writes(self):
        """`Edit <path>` alone hid what the write did, so a bump it carried
        could not be read off it (issue 126)."""
        shown = self.called("Edit", {"file_path": "/s/spec.yaml",
                                     "old_string": "revision: 1\ndepth: 600",
                                     "new_string": "revision: 2\ndepth: 640"})
        self.assertIn("/s/spec.yaml", shown)
        self.assertIn("revision: 1\ndepth: 600", shown)
        self.assertIn("revision: 2\ndepth: 640", shown)
        self.assertLess(shown.index("depth: 600"), shown.index("depth: 640"))

    def test_a_shell_call_is_still_its_command(self):
        self.assertEqual(self.called("Bash", {"command": "contour check"}),
                         "Bash  contour check")


SPEC = """model: chair
revision: 2
dimensions:
  height: { value: 820, tol: 5 }
  seat_depth: { value: 600, tol: 20 }
topology:
  tri_budget: 2000
"""

NOTES = """notes:
  - "Faces -Y (Blender front)."
  - "Beak: cylinder with hemispherical tip, ~100 diameter, ~170 proud of the head."
  - "Matte flat colours."
"""


if __name__ == "__main__":
    unittest.main()
