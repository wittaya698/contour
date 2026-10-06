"""A gate says the act and what changes (ADR 0025, decision 6; issue 68).

A gate used to read as its category and the raw call: *SPEC-WRITE*, then a
heredoc. These hold what it says instead — what Claude wants to do, in plain
words from one table keyed by category, and for a spec write each field that
moves — with the raw call kept, one click away.
"""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import gate, marks    # noqa: E402
from lib.canvas import PAGE    # noqa: E402
from test_console import ConsoleCase    # noqa: E402


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
        bump every confirmed write carries is the bookkeeping, not the change."""
        space = self.space()
        (space / "spec.yaml").write_text(SPEC)
        said = self.said({"call": {"tool": "Edit", "file_path": str(space / "spec.yaml"),
                                   "old_string": "revision: 2\ndimensions:\n"
                                                 "  height: { value: 820, tol: 5 }\n"
                                                 "  seat_depth: { value: 600, tol: 20 }",
                                   "new_string": "revision: 3\ndimensions:\n"
                                                 "  height: { value: 820, tol: 5 }\n"
                                                 "  seat_depth: { value: 640, tol: 3 }"}},
                         space=space)
        self.assertEqual(said["act"], "Claude wants to change the spec")
        self.assertEqual(said["changes"], ["seat depth 600 → 640 mm",
                                           "seat depth tolerance 20 → 3 mm"])

    def test_a_spec_write_names_the_span_its_proposal_measured_on(self):
        """The proposal is the agent's prose before the write (rule 1), so the
        span is read from what it last said — and only a span this space holds
        is named, so a plain mark the prose mentions is not taken for one."""
        space = self.space()
        (space / "spec.yaml").write_text(SPEC)
        held = space / marks.NAME
        marks.on_reference(held, "side.png", [10, 40], "where the back starts")
        marks.on_reference(held, "side.png", [10, 50], "seat depth", to=[300, 50])
        said = self.said({"say": "Seat depth reads 640 mm ±3 on span m2, against "
                                 "600 ±20; m1 is where the back starts. Shall I?"},
                         {"call": {"tool": "Write", "file_path": str(space / "spec.yaml"),
                                   "content": SPEC.replace("value: 600", "value: 640")}},
                         space=space)
        self.assertEqual(said["spans"], ["m2"])
        self.assertEqual(said["changes"], ["seat depth 600 → 640 mm"])


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


SPEC = """model: chair
revision: 2
dimensions:
  height: { value: 820, tol: 5 }
  seat_depth: { value: 600, tol: 20 }
topology:
  tri_budget: 2000
"""


if __name__ == "__main__":
    unittest.main()
