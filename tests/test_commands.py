"""The launcher's commands as a table (issue 24).

What each command needs before it may run — a model space, the hold on it —
used to be re-derived in every arm of an if-chain, and open question 11's
decision that `canvas` and `mark` take nothing existed only as two absences
somebody had to notice. Now each is a column, so it can be asserted without
starting a process, and a choice reads as a choice.
"""
import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import cli, commands


def names(**column):
    """The commands whose columns say so, in table order."""
    return [c.name for c in commands.TABLE
            if all(getattr(c, k) == v for k, v in column.items())]


class HoldTest(unittest.TestCase):
    def test_the_commands_that_write_out_or_read_the_build_hold_the_space(self):
        """Open question 11: a second run may not join a build, and `resolve`
        casts rays into the build another terminal may be replacing. `run` is
        the unit the hold is scoped to, so it takes it too."""
        self.assertEqual(names(holds=True),
                         ["check", "render", "export", "filmstrip", "resolve", "run"])

    def test_the_canvas_and_the_agents_mark_deliberately_take_nothing(self):
        """Both only append to `marks.json`, and a canvas session is a person
        at a page — a hold nobody is watching (open question 11)."""
        held = {c.name: c.holds for c in commands.TABLE}
        self.assertIs(held["canvas"], False)
        self.assertIs(held["mark"], False)

    def test_nothing_holds_a_space_it_does_not_need(self):
        """The hold is taken on a space; a command that runs without one has
        nothing to hold."""
        self.assertEqual([c.name for c in commands.TABLE if c.holds and not c.space], [])


class SpaceTest(unittest.TestCase):
    def test_the_commands_about_a_model_need_to_be_standing_in_one(self):
        """ADR 0015: a model is never named on the command line, so a command
        about one has nowhere else to find it — and falling back to the
        toolkit's own directory would build something nobody asked for."""
        self.assertEqual(names(space=True),
                         ["check", "render", "export", "filmstrip", "measure",
                          "worksheet", "canvas",
                          "resolve", "mark", "run", "doctor", "migrate-marks",
                          "rename", "delete"])


class ArityTest(unittest.TestCase):
    def call(self, argv):
        """`main`, with what it says caught. The usage is asserted whole, so a
        call refused for anything else — no space, no Blender — fails here, and
        fails on the table's first row: nothing further down is ever run."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = cli.main(argv)
        return code, err.getvalue()

    def test_a_word_too_many_is_answered_with_the_usage(self):
        for c in commands.TABLE:
            least, most = c.arity
            if most is None:
                continue
            code, said = self.call([c.name, *["x"] * (most + 1)])
            self.assertEqual(code, 2, c.name)
            self.assertEqual(said, cli.usage() + "\n", c.name)

    def test_a_word_too_few_is_answered_with_the_usage(self):
        for c in commands.TABLE:
            least, most = c.arity
            if least == 0:
                continue
            code, said = self.call([c.name, *["x"] * (least - 1)])
            self.assertEqual(code, 2, c.name)
            self.assertEqual(said, cli.usage() + "\n", c.name)

    def test_a_command_nobody_wrote_is_answered_with_the_usage(self):
        code, said = self.call(["bake"])
        self.assertEqual(code, 2)
        self.assertEqual(said, cli.usage() + "\n")


class UsageTest(unittest.TestCase):
    def documented(self):
        return [line.split()[1] for line in cli.usage().splitlines()
                if line.startswith("    contour ")]

    def test_the_help_lists_every_command_in_the_table_in_its_order(self):
        """Rendered from the usage column, so a new command cannot be left
        undocumented and a removed one cannot linger in the help."""
        self.assertEqual(self.documented(),
                         [c.name for c in commands.TABLE for _ in c.usage])

    def test_the_help_still_says_where_blenders_output_goes(self):
        """The prose is kept: the list is generated, the warning is not."""
        self.assertIn("last-build.log", cli.usage())

    def test_contour_help_prints_what_the_table_renders(self):
        """The one process in this file: the shim is what a person types, and
        the claim is about what they see."""
        r = subprocess.run([sys.executable, str(ROOT / "contour"), "--help"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, cli.usage() + "\n")


if __name__ == "__main__":
    unittest.main()
