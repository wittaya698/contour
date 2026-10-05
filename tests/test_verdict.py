"""Whether the model is right, in plain words (ADR 0025, decision 4; issue 66).

The verdict was already kept whole in `last-build.json` (issue 58) and read by
the agent and the connector only. These hold the sentences a page says about
it — one table, keyed by check id, because the lobby row, the export card, the
page header and the connector will all say the same ones.
"""
import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import checks, verdict


def kept(*results, built=True, lines=()):
    """A verdict as `check` keeps it, with only what these tests read."""
    return {"built": built, "ok": built and all(r["ok"] for r in results),
            "lines": list(lines), "results": list(results)}


def passed(cid, info=""):
    return {"id": cid, "ok": True, "info": info, "msg": ""}


def failed(cid, msg, info=""):
    return {"id": cid, "ok": False, "info": info, "msg": msg}


class GreenTest(unittest.TestCase):
    def test_a_green_build_is_one_quiet_line_with_the_passes_behind_it(self):
        said = verdict.say(kept(passed("spec", "spec ok"), passed("height", "200.0")))
        self.assertIs(said["ok"], True)
        self.assertEqual(said["line"], "matches the spec")
        self.assertEqual(said["failing"], [])
        self.assertEqual(said["passing"], ["spec ok", "height 200.0"],
                         "collapsed behind the line, not dropped")


def box(height_mm, width_mm=500.0, depth_mm=500.0):
    """One part, measured as `lib/measure.py` would: a world box, in metres."""
    return [{"name": "seat", "bounds": [[0.0, 0.0, 0.0],
                                        [width_mm / 1000, depth_mm / 1000,
                                         height_mm / 1000]]}]


class RedTest(unittest.TestCase):
    def test_a_failing_dimension_says_what_it_measured_and_what_was_wanted(self):
        """Read off the check's own verdict, not a message written here: when
        the check's wording moves, this is where the sentence is found broken."""
        spec = {"dimensions": {"height": {"value": 1700, "tol": 5}}}
        said = verdict.say(kept(*checks.dimensions(spec, box(1640))))
        self.assertIs(said["ok"], False)
        self.assertEqual(said["line"], "1 thing doesn't match the spec")
        self.assertEqual(said["failing"],
                         ["Height is 1640 mm; the spec wants 1700, give or take 5."])

    def test_a_check_the_table_does_not_know_arrives_as_its_report_line(self):
        """A check added to the toolkit later is visible on the day it lands,
        in the words the terminal already prints for it — never dropped."""
        spec = {"dimensions": {"height": {"value": 1700, "tol": 5}}}
        said = verdict.say(kept(*checks.dimensions(spec, box(1640)),
                                failed("wobble", "legs 3mm uneven")))
        self.assertEqual(said["line"], "2 things don't match the spec")
        self.assertEqual(said["failing"][1], "wobble  legs 3mm uneven")


def reported():
    """Every check id `lib/checks.py` can put in a verdict, read off its
    source: each literal handed to `result`, and the dimensions, which are
    handed one by name. Read rather than listed, so a check added there is a
    check this file knows about without anybody remembering to say so."""
    tree = ast.parse(Path(checks.__file__).read_text())
    ids = {node.args[0].value for node in ast.walk(tree)
           if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "result"
           and node.args and isinstance(node.args[0], ast.Constant)}
    return ids | set(checks.DIMS)


class TableTest(unittest.TestCase):
    def test_every_check_a_build_can_report_has_a_sentence(self):
        """The fallback keeps an unworded check visible; this keeps it rare.
        A new check id fails here until somebody writes what it means."""
        ids = reported()
        self.assertGreater(len(ids), 20, "the reading found the checks")
        self.assertEqual(sorted(ids - set(verdict.WORDS)), [])


    def test_the_checks_with_numbers_are_read_and_not_fallen_back_on(self):
        """A sentence that reads numbers out of a check's message falls back to
        the report line when the message changes — visible, but no longer
        plain. Each is driven red through the real check here, so a reworded
        message breaks a test instead of a sentence."""
        part = {"name": "seat", "faces": {3: 2400, 4: 0}, "nearest_pair_mm": 0.01,
                "materials": ["wood", "metal", "paint"]}
        spec = {"topology": {"tri_budget": 2000, "quads_min_pct": 90,
                             "doubles_tolerance_mm": 0.1},
                "materials": {"max_slots": 2}}
        said = verdict.say(kept(*checks.topology(spec, [part]),
                                *checks.materials(spec, [part])))
        self.assertEqual(said["failing"], [
            "It has 2,400 triangles; the spec allows 2,000.",
            "0% of its faces have four sides; the spec wants at least 90%.",
            "Some points sit closer than 0.1 mm to each other, in seat(0.010mm).",
            "It uses 3 materials; the spec allows 2."])


class DiedTest(unittest.TestCase):
    def test_a_build_that_died_before_it_was_judged_says_so(self):
        """Not *matches the spec* — there were no failures because there was no
        judging — and not a count of none. Its own sentence."""
        said = verdict.say(kept(built=False,
                                lines=["FAIL blender exit 1, no report"]))
        self.assertIs(said["ok"], False)
        self.assertEqual(said["line"],
                         "the build stopped before it could be checked")
        self.assertEqual(said["failing"], [])


if __name__ == "__main__":
    unittest.main()
