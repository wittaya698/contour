"""Selftest says when the suite gets slow, before the limit does (issue 95).

The suite went from fine to 333 s without anybody being told, and the answer
then was to raise the limit. A budget well under the limit, and a per-test one
that names the test, make the drift a line in the report while it is small.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import cli  # noqa: E402

MODULE = '''
from budget import slow


class WaitTest:
    @slow("three idle timeouts' worth")
    def test_waits(self):
        pass

    def test_fast(self):
        pass
'''


def output(total, *durations):
    lines = ["Slowest test durations", "-" * 70]
    lines += [f"{s:.3f}s     {name.rsplit('.', 1)[1]} ({name})" for s, name in durations]
    lines += ["", "-" * 70, f"Ran 3 tests in {total:.3f}s", "", "OK"]
    return "\n".join(lines)


class BudgetTest(unittest.TestCase):
    def setUp(self):
        self.tests = Path(tempfile.mkdtemp())
        (self.tests / "test_mod.py").write_text(MODULE)

    def warned(self, text):
        return cli.budget_warnings(text, self.tests)

    def test_a_suite_within_budget_says_nothing(self):
        self.assertEqual(self.warned(output(100.0, (1.0, "test_mod.WaitTest.test_fast"))), [])

    def test_a_suite_over_budget_says_by_how_much(self):
        [line] = self.warned(output(cli.UNITS_BUDGET_S + 12, (0.1, "test_mod.WaitTest.test_fast")))
        self.assertIn(f"{cli.UNITS_BUDGET_S + 12:.0f}s", line)
        self.assertIn(f"{cli.UNITS_BUDGET_S}s budget", line)

    def test_a_slow_test_is_named(self):
        [line] = self.warned(output(100.0, (cli.PER_TEST_S + 1, "test_mod.WaitTest.test_fast")))
        self.assertIn("test_mod.WaitTest.test_fast", line)
        self.assertIn("@slow", line)

    def test_a_test_marked_slow_says_why_and_is_not_named(self):
        self.assertEqual(self.warned(output(100.0, (8.0, "test_mod.WaitTest.test_waits"))), [])

    def test_a_test_it_cannot_find_is_named_rather_than_excused(self):
        """A module or method the check cannot read is not a reason to stay
        quiet; it is the check not knowing, which is worth a line."""
        [line] = self.warned(output(100.0, (9.0, "test_gone.SomeTest.test_x")))
        self.assertIn("test_gone.SomeTest.test_x", line)

    def test_the_marks_in_the_suite_are_on_tests_that_exist(self):
        """Every `@slow` in the real suite says why, so the reason is the
        point of the mark and not a formality."""
        import ast
        here = Path(__file__).resolve().parent
        for f in here.glob("test_*.py"):
            for node in ast.walk(ast.parse(f.read_text())):
                for d in getattr(node, "decorator_list", []):
                    if isinstance(d, ast.Call) and getattr(d.func, "id", None) == "slow":
                        with self.subTest(test=f"{f.stem}.{node.name}"):
                            self.assertTrue(d.args and isinstance(d.args[0], ast.Constant)
                                            and d.args[0].value.strip())


if __name__ == "__main__":
    unittest.main()
