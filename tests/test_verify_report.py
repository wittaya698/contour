"""What a build prints, and what it costs to print it (ADR 0005, ADR 0020).

`verify.py` had no test file at all: every check iterated live `bmesh` handles,
so nothing could import it without Blender, and `report()` and `stats()` — pure
string formatting, the whole of ADR 0005's token budget — were untested for a
reason that had nothing to do with them. ADR 0020 moved the judgement out and
the gather out; what is left imports on a bare clone, so the budget stops being
an intention and becomes a number a test can hold to.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import verify

# The smoke fixture's own green verdicts, which is what the budget is a budget
# for: a real report, not a contrived short one.
GREEN = {"spec": "spec ok", "height": "200.0", "width": "120.0", "depth": "100.0",
         "parts": "3/3", "tris": "1,496/2,000", "quads": "92%", "ngons": "0",
         "manifold": "ok", "loose": "0", "normals": "outward", "doubles": "0",
         "uv": "ok", "mat_slots": "2/2", "mat_names": "ok", "origin": "base_center",
         "scale": "1"}


def results(info=None, failures=()):
    """Verdicts as the checks leave them: every id green unless named."""
    out = [{"id": k, "ok": True, "info": v, "msg": ""}
           for k, v in (GREEN if info is None else info).items()]
    for cid, msg in failures:
        for r in out:
            if r["id"] == cid:
                r.update(ok=False, msg=msg)
    return out


class ReportTest(unittest.TestCase):
    def test_a_green_build_reports_in_two_lines_inside_the_token_budget(self):
        """ADR 0005 budgets ~50 tokens for the thing that prints on *every*
        build, which is the only tier with no rate limit on it. Characters over
        four is the proxy — no tokenizer ships with a bare clone, and the ratio
        is close enough that a report which doubled would be caught and one
        that gained a word would not.
        """
        lines = verify.report("smoke", results())
        self.assertEqual(len(lines), 2)
        self.assertLessEqual(sum(len(l) for l in lines) / 4, 50)

    def test_a_green_build_leads_with_the_readings_a_human_scans_for(self):
        """Seventeen checks passed is not news. How big it came out and what it
        cost in triangles is, so those are on the first line and the rest is
        one line under it."""
        first, rest = verify.report("smoke", results())
        self.assertEqual(first, "smoke PASS  verify 17/17 | tris 1,496 | height 200mm")
        self.assertEqual(rest, "  width 120.0 | depth 100.0 | quads 92% | parts 3/3 "
                               "| mat_slots 2/2 | origin base_center")

    def test_a_red_build_says_which_checks_failed_and_why(self):
        """The failure detail, and only the failures: a red report is read to
        find out what to fix, and the passing readings are noise in it."""
        lines = verify.report("smoke", results(failures=[
            ("height", "height 250.0mm, want 200±1"),
            ("manifold", "non-manifold edges in plinth(4)")]))
        self.assertEqual(lines[0], "smoke FAIL 15/17")
        self.assertEqual(lines[1:], ["  FAIL height    height 250.0mm, want 200±1",
                                     "  FAIL manifold  non-manifold edges in plinth(4)"])

    def test_a_red_build_prints_no_green_stamp(self):
        """The stamp is what gets pasted into a commit message. A build that
        failed must not hand one over."""
        lines = verify.report("smoke", results(failures=[("height", "too tall")]))
        self.assertFalse(any("PASS" in l for l in lines))

    def test_a_reading_the_checks_did_not_produce_is_left_out(self):
        """A spec that states no dimensions gets no dimension line, rather than
        a line of blanks: the report says what was measured."""
        lines = verify.report("smoke", results({"spec": "spec ok", "parts": "3/3"}))
        self.assertEqual(lines, ["smoke PASS  verify 2/2", "  parts 3/3"])


class StatsTest(unittest.TestCase):
    def test_the_stamp_is_every_reading_by_the_check_that_took_it(self):
        """What a commit message records, so the readings have to survive
        without the verdicts around them."""
        got = verify.stats({}, results())
        self.assertEqual(got["tris"], "1,496/2,000")
        self.assertEqual(got["origin"], "base_center")
        self.assertEqual(len(got), len(GREEN))


if __name__ == "__main__":
    unittest.main()
