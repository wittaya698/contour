"""`@slow("why")`: a test that is slow on purpose, and says what for (issue 95).

`contour selftest` names every test over `PER_TEST_S` (in `lib/cli.py`) that
is not marked, so a test that got slow by accident is a line in the report the
day it does. A mark is for time a test cannot do without — a wait proving that
nothing happens, many subprocesses each worth having — and its reason is what
the next reader weighs before shortening it.
"""


def slow(why):
    def mark(test):
        test.slow = why
        return test
    return mark
