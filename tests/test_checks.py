"""The topology checks, judged against a measurement written by hand.

The tracer bullet for ADR 0020 (issue 22): if every topology check can be
expressed as arithmetic over per-part summary numbers, then this file can exist
at all — no Blender, no fixture, no rebuild. The ADR's mutants stay; they prove
the gather, the checks and the report are wired together, which nothing here
can show. These prove the judgement.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import checks


def part(name="plinth", **fields):
    """One part as the gather leaves it: every count zero unless named.

    Zero rather than absent, because the gather always produces every field —
    a check reading one the gather forgot should be a `KeyError` here and not
    a quiet pass (ADR 0020).
    """
    return {"name": name, "faces": {}, "verts": 0, "edges": 0,
            "non_manifold_edges": 0, "loose_verts": 0, "loose_edges": 0,
            "flipped_faces": 0, "nearest_pair_mm": None, **fields}


def verdicts(results):
    """The results by check id, which is how a test asks about one of them."""
    return {r["id"]: r for r in results}


class TopologyTest(unittest.TestCase):
    def test_a_model_over_the_triangle_budget_fails_the_budget_check(self):
        """A quad is two triangles and an n-gon is its degree less two, which
        is the arithmetic the budget was always counting — here over a face
        histogram rather than over live faces."""
        spec = {"topology": {"tri_budget": 100}}
        over = verdicts(checks.topology(spec, [part(faces={3: 60, 4: 30})]))
        self.assertFalse(over["tris"]["ok"])
        self.assertIn("120", over["tris"]["msg"])
        under = verdicts(checks.topology(spec, [part(faces={4: 40})]))
        self.assertTrue(under["tris"]["ok"])

    def test_the_quad_percentage_is_counted_over_every_part_at_once(self):
        """One figure for the model and not one per part: the spec states a
        proportion of the whole, and a part that is honestly all triangles is
        not a failure on its own."""
        spec = {"topology": {"quads_min_pct": 90}}
        mixed = [part("plinth", faces={4: 8}), part("cap", faces={3: 4, 4: 8})]
        low = verdicts(checks.topology(spec, mixed))          # 16 of 20
        self.assertFalse(low["quads"]["ok"])
        self.assertIn("80", low["quads"]["msg"])
        high = verdicts(checks.topology(spec, [part(faces={3: 1, 4: 19})]))
        self.assertTrue(high["quads"]["ok"])

    def test_an_ngon_is_reported_against_the_part_it_is_in(self):
        """Counts aggregate, blame does not. A person fixing this needs the
        part's name, which is why the record carries one."""
        spec = {"topology": {"ngons_allowed": False}}
        got = verdicts(checks.topology(spec, [part("plinth", faces={4: 6}),
                                              part("cap", faces={4: 1, 5: 2})]))
        self.assertFalse(got["ngons"]["ok"])
        self.assertIn("cap(2)", got["ngons"]["msg"])
        self.assertNotIn("plinth", got["ngons"]["msg"])
        clean = verdicts(checks.topology(spec, [part(faces={3: 2, 4: 6})]))
        self.assertTrue(clean["ngons"]["ok"])

    def test_a_non_manifold_edge_fails_the_required_manifold_check(self):
        """An edge with one face or three: the count is what the gather can
        reduce an open or self-intersecting mesh to."""
        spec = {"topology": {"manifold": "required"}}
        got = verdicts(checks.topology(spec, [part("plinth", non_manifold_edges=4)]))
        self.assertFalse(got["manifold"]["ok"])
        self.assertIn("plinth(4)", got["manifold"]["msg"])
        self.assertTrue(verdicts(checks.topology(spec, [part()]))["manifold"]["ok"])

    def test_loose_geometry_counts_a_stray_vertex_and_a_stray_edge_alike(self):
        """Two ways to leave something behind, one verdict: the spec forbids
        geometry attached to nothing, and which kind it was does not change
        the answer."""
        spec = {"topology": {"loose_geometry": "forbidden"}}
        got = verdicts(checks.topology(spec, [part("plinth", loose_verts=1),
                                              part("cap", loose_edges=2)]))
        self.assertFalse(got["loose"]["ok"])
        self.assertIn("plinth(1)", got["loose"]["msg"])
        self.assertIn("cap(2)", got["loose"]["msg"])
        self.assertTrue(verdicts(checks.topology(spec, [part()]))["loose"]["ok"])

    def test_a_part_with_inward_faces_fails_the_outward_normals_check(self):
        """Whether a face points outward is decided against a recomputed copy,
        which is geometry — so the gather decides it and reduces it to how
        many disagreed. The check reads the count."""
        spec = {"topology": {"normals": "outward"}}
        got = verdicts(checks.topology(spec, [part("cap", flipped_faces=6)]))
        self.assertFalse(got["normals"]["ok"])
        self.assertIn("cap(6)", got["normals"]["msg"])
        self.assertTrue(verdicts(checks.topology(spec, [part()]))["normals"]["ok"])

    def test_a_normals_rule_this_verifier_cannot_enforce_fails_rather_than_skips(self):
        """`verify.py`'s first rule, and it survives the move: a spec field
        nothing can enforce is a failure and never a silence, because a
        constraint quietly ignored is the same defect as one weakened."""
        spec = {"topology": {"normals": "inward"}}
        got = verdicts(checks.topology(spec, [part()]))
        self.assertFalse(got["normals"]["ok"])
        self.assertIn("not implemented", got["normals"]["msg"])

    def test_two_vertices_closer_than_the_tolerance_fail_the_doubles_check(self):
        """The one check the ADR could not reduce to a count. How many
        duplicates a part has is a question about a tolerance the gather does
        not know, so the gather answers the question it can — how close the
        closest two vertices came — and the tolerance is applied here."""
        spec = {"topology": {"doubles_tolerance_mm": 0.01}}
        got = verdicts(checks.topology(spec, [part("pillar", nearest_pair_mm=0.0),
                                              part("cap", nearest_pair_mm=3.5)]))
        self.assertFalse(got["doubles"]["ok"])
        self.assertIn("pillar", got["doubles"]["msg"])
        self.assertNotIn("cap", got["doubles"]["msg"])
        clear = verdicts(checks.topology(spec, [part(nearest_pair_mm=0.02)]))
        self.assertTrue(clear["doubles"]["ok"])

    def test_a_pair_exactly_at_the_tolerance_counts_as_within_it(self):
        """`within 0.01mm` includes 0.01mm, which is what the `find_doubles`
        call this replaced meant by its distance. The boundary is stated
        because it was chosen, not because a float will ever land on it."""
        spec = {"topology": {"doubles_tolerance_mm": 0.01}}
        got = verdicts(checks.topology(spec, [part(nearest_pair_mm=0.01)]))
        self.assertFalse(got["doubles"]["ok"])

    def test_a_part_with_no_closest_pair_cannot_fail_the_doubles_check(self):
        """One vertex, or none: there is no pair to be too close, and the
        gather says so with `None` rather than with a number that would read
        as a distance of zero — which is the answer that fails."""
        spec = {"topology": {"doubles_tolerance_mm": 0.01}}
        got = verdicts(checks.topology(spec, [part("empty", nearest_pair_mm=None)]))
        self.assertTrue(got["doubles"]["ok"])

    def test_a_scene_with_no_faces_at_all_is_not_a_division_by_zero(self):
        """Nothing built, or everything deleted. The percentage is zero and
        the check fails on it, which is the honest answer — no model meets a
        quad proportion."""
        spec = {"topology": {"quads_min_pct": 90}}
        got = verdicts(checks.topology(spec, []))
        self.assertFalse(got["quads"]["ok"])

    def test_a_spec_with_no_topology_section_is_judged_on_nothing(self):
        """Silence in the spec is not a constraint. It is the one thing that
        is skipped rather than failed, because the user never asked."""
        self.assertEqual(checks.topology({}, [part(faces={5: 9})]), [])


if __name__ == "__main__":
    unittest.main()
