"""What only the fixture's own render can say (ADR 0009, ADR 0018).

The identity mask, the ray behind an anchor and the badge an agent mark gets
are decided by geometry, so they are checked against the one build whose
geometry is known: `fixtures/smoke`, a plinth, a pillar and a cap that is a
sphere of radius 30 mm centred on its own origin. These used to be assertions
inside the launcher, where nothing could import or read them (issue 25).

Whatever needs Blender skips without `$BLENDER`, saying so. `contour selftest`
sets it and runs `FixtureTest` after its own stages, so one command still
proves all of this (ADR 0009). The class builds and renders the fixture for
itself, which costs a few seconds and means it can be run alone.
"""
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
STACK = ["cap", "pillar", "plinth"]


def centre_column(table, w, h, data):
    """The parts the front view's centre column names, top to bottom, one
    entry per run. The front view is the sheet's top-left quadrant."""
    x, seen = w // 4, []
    for y in range(h // 2):
        name = table.get(str(data[y * w + x]))
        if name and (not seen or seen[-1] != name):
            seen.append(name)
    return seen


def mask_faults(table, w, h, data):
    """What is wrong with a mask of the fixture, as sentences; empty when right.

    The cap overhangs the pillar, so the centre column is a real occlusion
    test: each pixel must name its nearest owner and nothing else.
    """
    if sorted(table.values()) != STACK:
        return [f"parts table is {sorted(table.values())}"]
    faults = []
    if data[0] != 0:
        faults.append(f"corner pixel is {data[0]}, not background")
    seen = centre_column(table, w, h, data)
    if seen != STACK:
        faults.append(f"centre column reads {seen}, not cap over pillar over plinth")
    return faults


def painted(column, corner=0):
    """A 16 x 16 mask whose front view's centre column holds `column` from the
    top, part indices as the fixture's table numbers them."""
    w = h = 16
    data = [0] * (w * h)
    for y, index in enumerate(column):
        data[y * w + w // 4] = index
    data[0] = corner
    return w, h, data


TABLE = {"1": "plinth", "2": "pillar", "3": "cap"}


class MaskFaultTest(unittest.TestCase):
    """The mask's claims have teeth, shown on masks painted by hand, so this
    much of the fixture's check runs with no Blender at all."""

    def test_cap_over_pillar_over_plinth_is_a_right_mask(self):
        self.assertEqual(mask_faults(TABLE, *painted([0, 3, 3, 2, 2, 1, 1, 0])), [])

    def test_a_pillar_drawn_over_the_cap_is_caught(self):
        """The occlusion the column exists to test: the cap is nearer."""
        faults = mask_faults(TABLE, *painted([0, 2, 3, 2, 1, 0]))
        self.assertEqual(len(faults), 1)
        self.assertIn("centre column reads ['pillar', 'cap', 'pillar', 'plinth']", faults[0])

    def test_a_part_missing_from_the_column_is_caught(self):
        self.assertTrue(mask_faults(TABLE, *painted([0, 3, 1, 1, 0])))

    def test_a_background_that_names_a_part_is_caught(self):
        faults = mask_faults(TABLE, *painted([0, 3, 2, 1, 0], corner=1))
        self.assertEqual(faults, ["corner pixel is 1, not background"])

    def test_a_table_that_is_not_the_fixtures_parts_is_caught(self):
        table = dict(TABLE, **{"3": "lid"})
        self.assertEqual(mask_faults(table, *painted([0, 3, 2, 1, 0])),
                         ["parts table is ['lid', 'pillar', 'plinth']"])


class SelftestTest(unittest.TestCase):
    """What runs here is only worth anything if `contour selftest` goes red
    when it does. Blender and the unit suite are stubbed, since they are the
    two processes the selftest spawns; what is left is its own arithmetic."""

    def selftest(self, fixture):
        from unittest import mock
        from lib import cli
        passed = {"ok": True, "lines": ["stubbed"]}
        with mock.patch.object(cli, "unit_tests", lambda: passed), \
                mock.patch.object(cli, "stage", lambda args, first=True: passed), \
                mock.patch.object(cli, "fixture_tests", lambda: fixture):
            return cli.stage_selftest()

    def test_a_claim_that_fails_against_the_render_fails_the_selftest(self):
        rep = self.selftest({"ok": False, "lines": ["the anchor sits 171.5 mm out"]})
        self.assertFalse(rep["ok"])
        self.assertTrue(rep["lines"][0].startswith("selftest FAIL"))
        self.assertIn("FAIL fixture   the anchor sits 171.5 mm out", rep["lines"])

    def test_and_every_claim_holding_is_one_line(self):
        rep = self.selftest({"ok": True, "lines": ["6/6 held against its render"]})
        self.assertTrue(rep["ok"])
        self.assertEqual([l for l in rep["lines"] if "fixture" in l],
                         ["ok   fixture   6/6 held against its render"])


BLENDER = os.environ.get("BLENDER")


@unittest.skipUnless(BLENDER, "needs $BLENDER: the fixture is built and rendered by Blender")
class FixtureTest(unittest.TestCase):
    """Against the fixture's render: its mask, its views, and two marks and a
    finding pinned to it, resolved and rendered back."""

    @classmethod
    def setUpClass(cls):
        from lib import cli, mask, marks, space, store, views
        F = cls.F = space.fixture("smoke", ROOT)
        cls.must(cli.stage(["build", "smoke", "--fixture"], first=False))
        cls.must(cli.stage(["render", "smoke", "--fixture"], first=False))
        cls.table = store.load(F.parts, {})
        cls.w, cls.h, cls.data = mask.read(F.mask)
        cls.sheet = store.load(F.views, None)
        cls.fingerprint = views.fingerprint(F.blend)

        # Two clicks the mask picks out — one on the cap down the front view's
        # centre column, one on the background beside it — and one finding
        # that names the cap and no point on it. Written here rather than
        # clicked, because what is checked is the ray, not the page.
        cap = next(int(i) for i, name in cls.table.items() if name == "cap")
        x = cls.w // 4
        rows = [y for y in range(cls.h // 2) if cls.data[y * cls.w + x] == cap]
        cls.clicked = [x, rows[len(rows) // 2]]
        F.marks.unlink(missing_ok=True)
        cls.hit = marks.on_sheet(F.marks, "front", cls.clicked, "is the cap too round")["id"]
        cls.miss = marks.on_sheet(F.marks, "front", [4, 4], "nothing out here")["id"]
        cls.agent = marks.on_part(F.marks, "cap", "is the cap too round")["id"]
        try:
            cls.must(cli.stage(["resolve", "smoke", "--fixture"], first=False))
            cls.marks = {m["id"]: m for m in marks.load(F.marks)}
            # Render again: an anchor is only worth anything if it comes back to
            # the pixel it came from, and a badge is how the user sees it did.
            cls.drawn = " | ".join(cls.must(cli.stage(["render", "smoke", "--fixture"],
                                                      first=False))["lines"])
        finally:
            F.marks.unlink(missing_ok=True)     # the fixture keeps no marks

    @staticmethod
    def must(rep):
        if not rep["ok"]:
            raise AssertionError(" | ".join(rep["lines"]))
        return rep

    def badge(self, mark_id):
        seen = re.search(rf"{mark_id} front (\d+),(\d+)", self.drawn)
        self.assertTrue(seen, f"no badge drawn for {mark_id}: {self.drawn}")
        return [int(seen.group(1)), int(seen.group(2))]

    def test_each_pixel_of_the_mask_names_its_nearest_part(self):
        self.assertEqual(mask_faults(self.table, self.w, self.h, self.data), [])

    def test_the_views_are_the_four_the_sheet_draws_of_the_build_it_drew(self):
        self.assertEqual([v["label"] for v in self.sheet["views"]],
                         ["front", "right", "top", "persp"])
        self.assertEqual(self.sheet["build"], self.fingerprint)

    def test_a_click_on_the_cap_anchors_on_the_caps_own_surface(self):
        """The whole claim of anchoring: the mark is stored where it is on the
        part, not where it happened to be on a sheet."""
        from lib import marks
        mark = self.marks[self.hit]
        self.assertEqual(marks.part(mark), "cap")
        self.assertFalse(marks.pixel(mark), "a resolved mark still carries its pixel")
        r = sum(c * c for c in marks.pin(mark)) ** 0.5
        self.assertTrue(0.0280 <= r <= 0.0302,       # 30 mm sphere, faceted 32 x 24
                        f"the anchor sits {r * 1000:.1f} mm from the cap's origin")

    def test_a_click_on_the_background_anchors_to_nothing(self):
        from lib import marks
        self.assertFalse(marks.pin(self.marks[self.miss]))

    def test_an_anchor_comes_back_to_the_pixel_it_was_clicked_at(self):
        back = self.badge(self.hit)
        off = max(abs(a - b) for a, b in zip(back, self.clicked))
        self.assertLessEqual(off, 3, f"clicked at {self.clicked}, re-projects to {back}")

    def test_an_agent_finding_is_drawn_on_the_part_it_names(self):
        """Nobody clicked, so where the badge goes is decided against the mask.
        That it lands on the part is all the fixture can witness: every part
        here is convex and centred on its origin. Which pixel of the part is
        claimed in `tests/test_agent_marks.py`, on an L (ADR 0018)."""
        x, y = self.badge(self.agent)
        self.assertEqual(self.table.get(str(self.data[y * self.w + x])), "cap")


if __name__ == "__main__":
    unittest.main()
