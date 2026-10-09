"""The survey writes nothing (issue 84).

That is what lets the connector import it directly and still reach no write
(ADR 0024, decision 1). Read from the source, function bodies and all, and
followed through every sibling it leans on: an import inside a function never
runs when the module is imported, so a probe that imports it would see nothing.
What the survey reads of a row lives where it can be reached without them.
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_lib_split import leans_on    # noqa: E402

WRITERS = {"rename", "delete", "restore", "enter", "lobby"}
"""The modules that change a space or make one; `update` writes too, and is
reached for how a copy stands, so it is its writes that are named below."""


def reached(name):
    """Every sibling in `lib/` that `name` leans on, however far down."""
    seen, todo = set(), [name]
    while todo:
        here = todo.pop()
        if here in seen:
            continue
        seen.add(here)
        todo += [n for n in leans_on(ROOT / "lib" / f"{here}.py")
                 if (ROOT / "lib" / f"{n}.py").is_file()]
    return seen - {name}


class WritesNothingTest(unittest.TestCase):

    def test_the_survey_reaches_no_module_that_writes_a_space(self):
        self.assertEqual(sorted(reached("survey") & WRITERS), [])

    def test_the_survey_calls_no_write_of_updates(self):
        """`update.perform` is the write; `standing`, `recorded` and
        `uncommitted` are readings, and are all the survey asks of it."""
        tree = ast.parse((ROOT / "lib" / "survey.py").read_text())
        asked = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                 and isinstance(n.value, ast.Name) and n.value.id == "update"}
        self.assertEqual(asked, {"standing", "recorded", "uncommitted"})

    def test_the_connector_reaches_no_module_that_writes_a_space(self):
        """It imports the survey, and through it nothing that writes: its two
        acts, open and create, are handed it by the launcher (ADR 0024)."""
        self.assertEqual(sorted(reached("connector") & WRITERS), [])


if __name__ == "__main__":
    unittest.main()
