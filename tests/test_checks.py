"""The topology checks, judged against a measurement written by hand.

The tracer bullet for ADR 0020 (issue 22): if every topology check can be
expressed as arithmetic over per-part summary numbers, then this file can exist
at all — no Blender, no fixture, no rebuild. The ADR's mutants stay; they prove
the gather, the checks and the report are wired together, which nothing here
can show. These prove the judgement.

Each of ADR 0009's thirteen mutants has a counterpart here — the same defect
written as a measurement and asserted straight against the check, with no
rebuild (issue 23):

    height                the model taller than its stated height
    missing part          a part the spec wants twice and finds once
    extra object          an object the spec does not name
    flipped normals       a part with inward faces
    loose vertex          a stray vertex and a stray edge alike
    open mesh             a non-manifold edge
    doubled vertex        two vertices closer than the tolerance
    scale not applied     an unapplied scale
    rotation not applied  an unapplied rotation
    n-gon                 an n-gon reported against the part it is in
    extra material        a material the spec does not list
    origin off            a model shifted off base_center
    tri budget            a model over the triangle budget

and the rig's (ADR 0023): the tree written as a spec, the seams as contacts:

    rig with two roots    a tree whose second root is a forgotten parent
    floating part         a joint whose boxes are apart and nothing crosses
    tangent part          a joint whose boxes touch and nothing crosses
    origin off its pivot  an origin 137 mm from its seam's centre
    no pivot tolerance    a rig whose spec gives no pivot tolerance
    bone off the tree     a bone hanging from another than the tree says
    extra bone            a bone that is no part
    part not weighted     a part on no bone
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
            "flipped_faces": 0, "nearest_pair_mm": None, "bounds": None,
            "scale": (1.0, 1.0, 1.0), "rotation_rad": 0.0, "uv_layers": 0,
            "materials": (), "origin": (0.0, 0.0, 0.0), "bound_to": None, **fields}


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


class TrisTest(unittest.TestCase):
    def test_the_triangle_count_of_a_measurement_is_the_sum_of_its_parts(self):
        """The round-trip needs this number without a spec to compare it to —
        it asks whether an export kept the triangles it was given, which is a
        question about two measurements and not about a budget."""
        self.assertEqual(checks.tris([part("a", faces={3: 2, 4: 3}),
                                      part("b", faces={5: 1})]), 11)


class DimensionsTest(unittest.TestCase):
    def test_a_model_taller_than_its_stated_height_fails_by_how_much(self):
        """The bounding box the check reads is the union of the parts\' own,
        so the height of a model is the height of everything in it and not of
        whichever part was measured last."""
        spec = {"dimensions": {"height": {"value": 200, "tol": 1}}}
        got = verdicts(checks.dimensions(spec, [
            part("plinth", bounds=((0.0, 0.0, 0.0), (0.12, 0.1, 0.02))),
            part("cap", bounds=((0.0, 0.0, 0.23), (0.12, 0.1, 0.25)))]))
        self.assertFalse(got["height"]["ok"])
        self.assertIn("250.0mm", got["height"]["msg"])

    def test_a_scene_with_nothing_in_it_fails_its_stated_dimensions(self):
        """Not skipped, and not passed for want of a reading: a spec that
        states a height and a scene with no mesh in it is a build that did not
        happen, which is a failure and not an absence of one."""
        spec = {"dimensions": {"height": {"value": 200, "tol": 1}}}
        got = verdicts(checks.dimensions(spec, []))["height"]
        self.assertFalse(got["ok"])
        self.assertIn("no mesh to measure", got["msg"])


class PartsTest(unittest.TestCase):
    def test_an_object_the_spec_does_not_name_is_unexpected(self):
        """Every object in the scene, not every mesh: the thing a stray
        `Cube` empty is caught by is that it is in the scene at all."""
        spec = {"parts": [{"name": "plinth"}, {"name": "cap"}]}
        got = verdicts(checks.parts(spec, ["plinth", "cap", "Cube"]))
        self.assertFalse(got["parts"]["ok"])
        self.assertIn("unexpected: Cube", got["parts"]["msg"])

    def test_a_part_the_spec_wants_twice_and_finds_once_is_a_count_problem(self):
        """`.001` suffixes count as the part: Blender names duplicates that
        way, and a spec asking for two pillars means two pillars however
        Blender spelled the second."""
        spec = {"parts": [{"name": "pillar", "count": 2}]}
        got = verdicts(checks.parts(spec, ["pillar"]))
        self.assertIn("pillar x1, want 2", got["parts"]["msg"])
        self.assertTrue(verdicts(checks.parts(spec, ["pillar", "pillar.001"]))
                        ["parts"]["ok"])


class UVTest(unittest.TestCase):
    def test_a_part_with_no_uv_layer_fails_a_spec_that_requires_one(self):
        spec = {"uv": {"required": True}}
        got = verdicts(checks.uv(spec, [part("cap", uv_layers=1),
                                        part("plinth", uv_layers=0)]))
        self.assertFalse(got["uv"]["ok"])
        self.assertIn("no UV layer: plinth", got["uv"]["msg"])

    def test_a_uv_rule_this_verifier_cannot_enforce_fails_rather_than_skips(self):
        """Both of them: UDIM and overlap are stated in specs and enforced by
        nothing here, so a spec asking for either gets told so."""
        got = verdicts(checks.uv({"uv": {"required": True, "udim": True,
                                         "overlap_allowed": False}},
                                 [part("cap", uv_layers=1)]))["uv"]
        self.assertFalse(got["ok"])
        self.assertIn("udim not implemented", got["msg"])
        self.assertIn("uv overlap check not implemented", got["msg"])


class MaterialsTest(unittest.TestCase):
    def test_a_material_the_spec_does_not_list_is_unexpected(self):
        """Counted across the scene and not per part: two parts sharing one
        material are one slot, which is what a budget on slots means."""
        spec = {"materials": {"max_slots": 2, "names": ["stone", "brass"]}}
        got = verdicts(checks.materials(spec, [
            part("cap", materials=("brass", "rogue")),
            part("plinth", materials=("stone",))]))
        self.assertFalse(got["mat_names"]["ok"])
        self.assertIn("unexpected ['rogue']", got["mat_names"]["msg"])
        self.assertFalse(got["mat_slots"]["ok"])
        self.assertEqual(got["mat_slots"]["info"], "3/2")


class TransformTest(unittest.TestCase):
    def test_a_model_shifted_off_the_origin_fails_base_center(self):
        """`base_center` is the floor of the box, not its middle: a model
        standing on Z=0 is at its origin however tall it is."""
        spec = {"transform": {"origin": "base_center"}}
        standing = [part("plinth", bounds=((-0.06, -0.05, 0.0), (0.06, 0.05, 0.2)))]
        self.assertTrue(verdicts(checks.transform(spec, standing))["origin"]["ok"])
        shifted = [part("plinth", bounds=((-0.01, -0.05, 0.0), (0.11, 0.05, 0.2)))]
        got = verdicts(checks.transform(spec, shifted))["origin"]
        self.assertFalse(got["ok"])
        self.assertIn("(50.0, 0.0, 0.0)mm", got["msg"])

    def test_an_unapplied_scale_names_the_part_carrying_it(self):
        spec = {"transform": {"scale_applied": True, "rotation_applied": True}}
        got = verdicts(checks.transform(spec, [
            part("plinth"), part("pillar", scale=(1.5, 1.0, 1.0)),
            part("cap", rotation_rad=1.5708)]))
        self.assertFalse(got["scale"]["ok"])
        self.assertEqual(got["scale"]["msg"], "scale not applied: pillar")
        self.assertFalse(got["rotation"]["ok"])
        self.assertEqual(got["rotation"]["msg"], "rotation not applied: cap")

    def test_an_up_axis_this_build_cannot_produce_fails_rather_than_skips(self):
        """The same rule as an unimplemented normals rule: what the verifier
        cannot enforce it must not pass in silence."""
        got = verdicts(checks.transform({"transform": {"up_axis": "Y"}}, []))
        self.assertFalse(got["up_axis"]["ok"])

    def test_an_origin_rule_this_verifier_cannot_place_fails_rather_than_skips(self):
        spec = {"transform": {"origin": "centre_of_mass"}}
        got = verdicts(checks.transform(spec, [
            part("plinth", bounds=((0, 0, 0), (0.1, 0.1, 0.1)))]))
        self.assertFalse(got["origin"]["ok"])
        self.assertIn("not implemented", got["origin"]["msg"])


class SpecTest(unittest.TestCase):
    def test_a_field_the_verifier_does_not_know_is_named_back(self):
        """A misspelt constraint is a constraint nobody enforces, which is the
        quietest way for a spec to stop meaning what it says."""
        got = verdicts(checks.spec({"model": "smoke", "topology": {"tri_budjet": 100}},
                                   "smoke"))["spec"]
        self.assertFalse(got["ok"])
        self.assertIn("unknown field topology.tri_budjet", got["msg"])

    def test_a_spec_built_for_another_model_is_refused(self):
        got = verdicts(checks.spec({"model": "beaky"}, "smoke"))["spec"]
        self.assertFalse(got["ok"])
        self.assertIn("!= variant 'smoke'", got["msg"])


class RigTest(unittest.TestCase):
    """The rig tree, judged over the spec alone (ADR 0023, issue 48).

    A part names the part it hangs from with `parent:`, so part names are
    written once and the tree cannot disagree with the part list. No geometry
    is read: whether the tree is a tree is a question about the document.
    """
    TREE = [{"name": "torso"},
            {"name": "neck", "parent": "torso"},
            {"name": "head", "parent": "neck"},
            {"name": "leg_L", "parent": "torso"}]

    def judge(self, parts):
        return verdicts(checks.rig({"model": "smoke", "parts": parts}))

    def test_a_spec_with_no_parent_anywhere_has_no_rig_and_is_judged_on_nothing(self):
        """Every space written before ADR 0023 stays green with no revision."""
        self.assertEqual(checks.rig({"parts": [{"name": "plinth"}, {"name": "cap"}]}), [])
        self.assertEqual(checks.rig({"model": "smoke"}), [])

    def test_a_tree_with_one_root_passes_and_says_its_size_and_root(self):
        got = self.judge(self.TREE)["rig"]
        self.assertTrue(got["ok"], got["msg"])
        self.assertEqual(got["info"], "4 parts from torso")

    def test_two_parts_without_a_parent_are_two_roots(self):
        """A forgotten parent would otherwise make a second skeleton quietly."""
        got = self.judge(self.TREE + [{"name": "tail"}])["rig"]
        self.assertFalse(got["ok"])
        self.assertIn("2 roots: tail, torso", got["msg"])

    def test_a_parent_that_names_no_part_is_named_back(self):
        got = self.judge(self.TREE + [{"name": "hand_L", "parent": "arm_L"}])["rig"]
        self.assertFalse(got["ok"])
        self.assertIn("hand_L's parent 'arm_L' is not a part", got["msg"])

    def test_a_cycle_is_named_by_the_parts_in_it(self):
        """A cycle has no root, so the root count alone would only half say it."""
        parts = [{"name": "torso"}, {"name": "a", "parent": "b"}, {"name": "b", "parent": "a"}]
        got = self.judge(parts)["rig"]
        self.assertFalse(got["ok"])
        self.assertIn("cycle: a, b", got["msg"])

    def test_a_part_that_is_its_own_parent_is_a_cycle(self):
        got = self.judge([{"name": "torso"}, {"name": "head", "parent": "head"}])["rig"]
        self.assertFalse(got["ok"])
        self.assertIn("cycle: head", got["msg"])

    def test_a_rigged_part_counted_more_than_once_fails_rather_than_guesses(self):
        """One bone per part: four legs under one name have no one bone to be,
        and a rule this verifier cannot enforce fails rather than skips."""
        got = self.judge(self.TREE + [{"name": "toe", "count": 4, "parent": "leg_L"}])["rig"]
        self.assertFalse(got["ok"])
        self.assertIn("toe x4: one bone per part, count must be 1", got["msg"])

    def test_the_spec_check_accepts_a_parent_on_a_part(self):
        got = verdicts(checks.spec({"model": "smoke", "parts": self.TREE}, "smoke"))["spec"]
        self.assertTrue(got["ok"], got["msg"])

    def test_a_parent_that_is_not_a_name_is_refused_by_the_spec_check(self):
        got = verdicts(checks.spec({"model": "smoke",
                                    "parts": [{"name": "torso"}, {"name": "neck", "parent": 3}]},
                                   "smoke"))["spec"]
        self.assertFalse(got["ok"])
        self.assertIn("neck: parent must be a part name", got["msg"])

    def test_the_rig_is_judged_straight_after_the_spec(self):
        """A tree that is not a tree makes every later rig reading beside the
        point, as an unenforceable spec does for every reading."""
        m = {"objects": ["torso", "neck"], "parts": [part("torso"), part("neck")],
             "contacts": [], "rigs": []}
        got = checks.run({"model": "smoke", "parts": self.TREE[:2]}, "smoke", m)
        self.assertEqual([r["id"] for r in got][:3], ["spec", "rig", "parts"])


class SeamTest(unittest.TestCase):
    """Where a part turns, measured at rest (ADR 0023, issue 49).

    A joint's seam is where the two surfaces cross; the gather records, for
    each pair of parts, the points where an edge of one passes from inside the
    other to outside, and their centre. No crossing is no seam, which is what
    a part that floats or only touches gives.
    """
    SPEC = {"model": "smoke",
            "parts": [{"name": "torso"}, {"name": "neck", "parent": "torso"}],
            "transform": {"pivot_tolerance_mm": 1}}

    def judge(self, contacts, spec=SPEC, neck_box=([-.05, -.05, .45], [.05, .05, .7]),
              neck=(0, 0, .5)):
        """A torso 500 mm tall and a neck on it, origin at its seam unless
        told otherwise."""
        m = {"objects": ["torso", "neck"],
             "parts": [part("torso", bounds=([-.1, -.1, 0], [.1, .1, .5])),
                       part("neck", bounds=neck_box, origin=neck)],
             "contacts": contacts, "rigs": []}
        return verdicts(checks.run(spec, "smoke", m))

    def crossing(self, centre=(0, 0, .5), points=12):
        return [{"parts": ("neck", "torso"), "centre": centre, "points": points}]

    def test_a_joint_whose_surfaces_cross_has_a_seam(self):
        got = self.judge(self.crossing())["seams"]
        self.assertTrue(got["ok"], got["msg"])
        self.assertEqual(got["info"], "1 joint")

    def test_a_part_floating_off_its_parent_has_no_seam_and_says_how_far(self):
        got = self.judge([], neck_box=([-.05, -.05, .55], [.05, .05, .7]))["seams"]
        self.assertFalse(got["ok"])
        self.assertIn("neck has no seam with torso: floats 50.0mm off", got["msg"])

    def test_a_part_that_only_touches_its_parent_has_no_seam(self):
        """beaky's head on its neck: the bottom of one is the top of the other,
        a tangent point, and a tangent point is no seam (ADR 0023)."""
        got = self.judge([], neck_box=([-.05, -.05, .5], [.05, .05, .7]))["seams"]
        self.assertFalse(got["ok"])
        self.assertIn("neck has no seam with torso: touches at most, does not cross", got["msg"])

    def test_an_origin_on_its_seams_centre_is_on_its_pivot(self):
        got = self.judge(self.crossing(), neck=(0, 0, .5004))["pivots"]
        self.assertTrue(got["ok"], got["msg"])

    def test_an_origin_off_its_pivot_beyond_tolerance_says_by_how_much_and_where(self):
        """beaky's neck, whose origin is its sphere's centre, ~137 mm from
        where it meets the torso. Where the pivot is, so the fix in
        `build.py` has a number to move the origin to."""
        got = self.judge(self.crossing(), neck=(0, .003, .637))["pivots"]
        self.assertFalse(got["ok"])
        self.assertIn("neck origin 137.0mm off its pivot at (0.0, 0.0, 500.0)mm", got["msg"])

    def test_a_rig_with_no_pivot_tolerance_is_red_for_the_missing_field(self):
        """The tolerance is the user's (ADR 0023); a default here would be a
        number nobody chose, and lenient by accident."""
        for spec in ({**self.SPEC, "transform": {}}, {**self.SPEC, "transform": None},
                     {k: v for k, v in self.SPEC.items() if k != "transform"}):
            got = self.judge(self.crossing(), spec=spec)["pivots"]
            self.assertFalse(got["ok"])
            self.assertIn("rig needs transform.pivot_tolerance_mm", got["msg"])

    def test_the_spec_check_knows_the_pivot_tolerance(self):
        got = self.judge(self.crossing())["spec"]
        self.assertTrue(got["ok"], got["msg"])

    def test_an_unrigged_spec_is_judged_on_no_seam_and_no_pivot(self):
        got = self.judge([], spec={"model": "smoke", "parts": [{"name": "torso"}]})
        self.assertNotIn("seams", got)
        self.assertNotIn("pivots", got)


class BoneTest(unittest.TestCase):
    """The armature against the tree (ADR 0023, issue 51).

    The gather reads each armature object as a rig: its name and its bones,
    each with the bone it hangs from. Each part says which bone it is wholly
    weighted to, or None.
    """
    SPEC = {"model": "smoke",
            "parts": [{"name": "plinth", "parent": "pillar"},
                      {"name": "pillar", "parent": "cap"}, {"name": "cap"}],
            "transform": {"pivot_tolerance_mm": 1}}
    TREE = (("plinth", "pillar"), ("pillar", "cap"), ("cap", None))

    def judge(self, bones=TREE, rigs=None, bound=None, spec=SPEC):
        """The smoke fixture's three parts, each bound to its own bone unless
        told otherwise."""
        bound = {"plinth": "plinth", "pillar": "pillar", "cap": "cap", **(bound or {})}
        if rigs is None:
            rigs = [{"name": "rig", "bones": [{"name": n, "parent": p} for n, p in bones]}]
        m = {"objects": ["plinth", "pillar", "cap"],
             "parts": [part(n, bound_to=b) for n, b in bound.items()],
             "contacts": [], "rigs": rigs}
        return verdicts(checks.run(spec, "smoke", m))

    def test_bones_that_match_the_tree_pass(self):
        got = self.judge()["bones"]
        self.assertTrue(got["ok"], got["msg"])
        self.assertEqual(got["info"], "3/3")

    def test_a_part_with_no_bone_and_a_bone_with_no_part_are_named(self):
        got = self.judge(bones=self.TREE[1:] + (("stray", "cap"),))["bones"]
        self.assertFalse(got["ok"])
        self.assertIn("no bone for plinth", got["msg"])
        self.assertIn("bone stray is no part", got["msg"])

    def test_a_bone_hanging_from_another_than_the_tree_says_is_red(self):
        got = self.judge(bones=(("plinth", "cap"), ("pillar", "cap"), ("cap", None)))["bones"]
        self.assertFalse(got["ok"])
        self.assertIn("plinth's bone hangs from cap, the tree says pillar", got["msg"])

    def test_a_root_bone_given_a_parent_is_red(self):
        got = self.judge(bones=(("plinth", "pillar"), ("pillar", "cap"), ("cap", "plinth")))
        self.assertIn("cap's bone hangs from plinth, the tree says none",
                      got["bones"]["msg"])

    def test_a_part_not_wholly_on_its_own_bone_is_red(self):
        """None is what the gather says for a part with no weights, weights
        under one, or weights split between bones: whatever it is, the part
        does not move rigidly with its bone."""
        got = self.judge(bound={"plinth": None, "pillar": "cap"})["bones"]
        self.assertFalse(got["ok"])
        self.assertIn("plinth is not wholly on a bone", got["msg"])
        self.assertIn("pillar is on cap's bone, not its own", got["msg"])

    def test_a_rigged_spec_with_no_armature_says_what_build_py_lacks(self):
        got = self.judge(rigs=[])["bones"]
        self.assertFalse(got["ok"])
        self.assertIn("no armature; build.py needs kit.rig()", got["msg"])

    def test_two_armatures_are_red_rather_than_judging_one_of_them(self):
        one = {"name": "rig", "bones": [{"name": n, "parent": p} for n, p in self.TREE]}
        got = self.judge(rigs=[one, {**one, "name": "rig.001"}])["bones"]
        self.assertFalse(got["ok"])
        self.assertIn("2 armatures: rig, rig.001; one rig per model", got["msg"])

    def test_an_unrigged_spec_with_no_armature_is_judged_on_no_bones(self):
        got = self.judge(rigs=[], spec={"model": "smoke", "parts": [{"name": "cap"}]})
        self.assertNotIn("bones", got)

    def test_an_armature_the_spec_has_no_rig_for_is_red(self):
        """The gather keeps armatures out of `objects`, so `parts` cannot see
        a stray one; this is where it is seen instead."""
        got = self.judge(spec={"model": "smoke", "parts": [{"name": "cap"}]})["bones"]
        self.assertFalse(got["ok"])
        self.assertIn("armature rig, and the spec has no rig", got["msg"])


class RunTest(unittest.TestCase):
    """The whole verdict list, from a measurement written by hand.

    `verify.run` is this plus a gather, which is the shape ADR 0020 was for:
    the order the report prints in, the ids the mutant suite names, and the
    `only` filter the round-trip narrows with are all exercised here.
    """
    SPEC = {"model": "smoke", "dimensions": {"height": {"value": 200, "tol": 1}},
            "parts": [{"name": "plinth"}], "topology": {"tri_budget": 100},
            "transform": {"origin": "base_center"}}

    def measurement(self, **fields):
        return {"objects": ["plinth"],
                "parts": [part("plinth", faces={4: 6},
                               bounds=((-0.06, -0.05, 0.0), (0.06, 0.05, 0.2)),
                               **fields)],
                "contacts": [], "rigs": []}

    def test_a_measurement_that_meets_its_spec_passes_every_check(self):
        got = checks.run(self.SPEC, "smoke", self.measurement())
        self.assertTrue(all(r["ok"] for r in got), [r for r in got if not r["ok"]])
        self.assertEqual([r["id"] for r in got],
                         ["spec", "height", "parts", "tris", "origin"])

    def test_the_spec_is_judged_before_any_geometry_is(self):
        """Order is the report's, and `spec` leads it: a spec nobody can
        enforce makes every reading after it beside the point."""
        got = checks.run({**self.SPEC, "model": "beaky"}, "smoke", self.measurement())
        self.assertEqual(got[0]["id"], "spec")
        self.assertFalse(got[0]["ok"])

    def test_only_narrows_the_verdicts_to_the_checks_named(self):
        """What the export round-trip re-measures with: an importer legitimately
        re-welds and re-triangulates, so topology is not judged there."""
        got = checks.run(self.SPEC, "smoke", self.measurement(), only={"height"})
        self.assertEqual([r["id"] for r in got], ["height"])
