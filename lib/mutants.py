"""Prove verify can fail. A verifier that always passes would also pass selftest,
so each mutant breaks the fixture in one known way and must be caught by name."""
import bmesh
import bpy
from mathutils import Matrix

from . import ctx_override, kit, pose, scene
from .cmd_build import build


def _obj(name):
    return bpy.data.objects[name]


def _edit(name, fn):
    """Run fn(bm) on an object's mesh via bmesh and write it back."""
    me = _obj(name).data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    fn(bm)
    bm.to_mesh(me)
    bm.free()


def _raise_cap():
    _obj("cap").location.z += 0.030


def _delete_pillar():
    bpy.data.objects.remove(_obj("pillar"), do_unlink=True)


def _extra_object():
    o = bpy.data.objects.new("Cube", None)
    bpy.context.scene.collection.objects.link(o)


def _flip_cap():
    _edit("cap", lambda bm: bmesh.ops.reverse_faces(bm, faces=bm.faces))


def _loose_vert():
    _edit("plinth", lambda bm: bm.verts.new((0.5, 0.5, 0.5)))


def _open_plinth():
    _edit("plinth", lambda bm: bm.faces.remove(bm.faces[0]))


def _double_vert():
    _edit("pillar", lambda bm: bm.verts.new(bm.verts[0].co))


def _scale_pillar():
    _obj("pillar").scale = (1.5, 1.0, 1.0)


def _rotate_pillar():
    _obj("pillar").rotation_euler = (0.0, 0.0, 1.5708)


def _ngon_cap():
    def swap(bm):
        bm.clear()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=16,
                              radius1=0.03, radius2=0.03, depth=0.06)
    _edit("cap", swap)


def _rogue_material():
    _obj("cap").data.materials.append(kit.material("rogue", "#FF00FF"))


def _shift_all():
    for o in bpy.data.objects:
        o.location.x += 0.05


def _float_plinth():
    """10 mm down, past the 5 mm the pillar reaches into it: a gap of 5."""
    _obj("plinth").location.z -= 0.010


def _touch_plinth():
    """5 mm down, so the plinth's top meets the pillar's bottom face to face
    and nothing crosses."""
    _obj("plinth").location.z -= 0.005


def _pillar_origin_off():
    """The pillar's origin 10 mm above its seam with the cap; the mesh stays."""
    pillar = _obj("pillar")
    pillar.location.z += 0.010
    pillar.data.transform(Matrix.Translation((0.0, 0.0, -0.010)))


def _stray_bone():
    """A fourth bone, on no part, made the one way a bone can be (issue 47)."""
    rig = _obj("rig")
    bpy.context.view_layer.objects.active = rig
    ctx_override.call("object.mode_set", mode="EDIT")
    bone = rig.data.edit_bones.new("stray")
    bone.head, bone.tail = (0.0, 0.0, 0.3), (0.0, 0.0, 0.31)
    ctx_override.call("object.mode_set", mode="OBJECT")


def _unweight_plinth():
    plinth = _obj("plinth")
    plinth.vertex_groups.remove(plinth.vertex_groups["plinth"])


def _shorten_sway():
    bpy.data.actions["sway"].frame_end = 16


def _open_sway():
    """The pillar's closing key, at frame 20, turned 10 degrees off frame 0."""
    act = bpy.data.actions["sway"]
    bag = act.layers[0].strips[0].channelbag(act.slots[0])
    for fc in bag.fcurves:
        if fc.data_path == 'pose.bones["pillar"].rotation_euler' and fc.array_index == 0:
            fc.keyframe_points[-1].co.y += 0.1745
            fc.update()


def _sink_cap():
    """The cap 125 mm down, into the plinth, which is not its child."""
    _obj("cap").location.z -= 0.125


def _sweep_plinth():
    """A key at frame 5, which no spec key names, turning the plinth 90
    degrees about Y on its pivot: through the pillar it hangs from."""
    rig, act = _obj("rig"), bpy.data.actions["sway"]
    pb = rig.pose.bones["plinth"]
    pose.turn(pb, (0, 90, 0))
    turned = tuple(pb.rotation_euler)
    pose.turn(pb, (0, 0, 0))
    bag = act.layers[0].strips[0].channelbag(act.slots[0])
    for fc in bag.fcurves:
        if fc.data_path == 'pose.bones["plinth"].rotation_euler':
            fc.keyframe_points.insert(5, turned[fc.array_index])


def _key(frame, bone, angles):
    return lambda s: s["clips"]["sway"]["keys"][frame].update({bone: angles})


# name, mutate, spec edit, check ids that must fail
MUTANTS = [
    ("height", _raise_cap, None, {"height"}),
    ("missing part", _delete_pillar, None, {"parts"}),
    ("extra object", _extra_object, None, {"parts"}),
    ("flipped normals", _flip_cap, None, {"normals"}),
    ("loose vertex", _loose_vert, None, {"loose"}),
    ("open mesh", _open_plinth, None, {"manifold"}),
    ("doubled vertex", _double_vert, None, {"doubles"}),
    ("scale not applied", _scale_pillar, None, {"scale"}),
    ("rotation not applied", _rotate_pillar, None, {"rotation"}),
    ("n-gon", _ngon_cap, None, {"ngons"}),
    ("extra material", _rogue_material, None, {"mat_names", "mat_slots"}),
    ("origin off", _shift_all, None, {"origin"}),
    ("tri budget", lambda: None, lambda s: s["topology"].update(tri_budget=100), {"tris"}),
    ("rig with two roots", lambda: None, lambda s: s["parts"][1].pop("parent"), {"rig"}),
    ("floating part", _float_plinth, None, {"seams"}),
    ("tangent part", _touch_plinth, None, {"seams"}),
    ("origin off its pivot", _pillar_origin_off, None, {"pivots"}),
    ("no pivot tolerance", lambda: None,
     lambda s: s["transform"].pop("pivot_tolerance_mm"), {"pivots"}),
    ("bone off the tree", lambda: None, lambda s: s["parts"][0].update(parent="cap"),
     {"bones"}),
    ("extra bone", _stray_bone, None, {"bones"}),
    ("part not weighted", _unweight_plinth, None, {"bones"}),
    ("clip too short", _shorten_sway, None, {"clips"}),
    ("loop left open", _open_sway, None, {"clips"}),
    ("key on the wrong axis", lambda: None, _key(0, "plinth", [8, 0, 0]), {"clips"}),
    ("part enters another", _sink_cap, None, {"clips"}),
    ("seam swept through its parent", _sweep_plinth, None, {"clips"}),
]


def attach(rep, spec, P, variant):
    """Run every mutant; a mutant verify does not flag fails the whole selftest."""
    import copy
    import verify

    missed = []
    for name, mutate, edit_spec, expect in MUTANTS:
        build(P, variant)
        mutate()
        s = copy.deepcopy(spec)
        if edit_spec:
            edit_spec(s)
        failed = {r["id"] for r in verify.run(s, variant) if not r["ok"]}
        # mat_names and mat_slots are alternatives: either one flags the mutant
        if name == "extra material":
            caught = bool(failed & expect)
        else:
            caught = expect <= failed
        if not caught:
            missed.append(f"{name} (wanted {sorted(expect)}, got {sorted(failed)})")
    n = len(MUTANTS)
    rep["lines"].append(f"mutants {n - len(missed)}/{n} caught")
    for m in missed:
        rep["lines"].append(f"  FAIL not caught: {m}")
    rep["ok"] = rep["ok"] and not missed
    return rep


# name, wrap transform applied to every root of the real export, check ids that must fail
GLB_MUTANTS = [
    ("mirrored x", {"scale": [-1.0, 1.0, 1.0]}, {"gl_handed"}),
    ("z-up file", {"rotation": [0.70710678, 0.0, 0.0, 0.70710678]}, {"gl_height", "gl_depth"}),
    ("millimetre units", {"scale": [1000.0, 1000.0, 1000.0]}, {"gl_height", "gl_width"}),
    ("origin shifted", {"translation": [0.05, 0.0, 0.0]}, {"gl_origin"}),
]


# name, how the build is exported wrong, check ids that must fail (issue 54)
RIG_EXPORTS = [
    ("exported at rest", {"posed": False}, {"re_motion"}),
    ("exported at another rate", {"fps": 30}, {"gl_rig"}),
]
# name, wrap transform on the real export, read back: every part moved
RIG_WRAPS = [
    ("mirrored x, read back", {"scale": [-1.0, 1.0, 1.0]}),
    ("millimetre units, read back", {"scale": [1000.0, 1000.0, 1000.0]}),
]


def _carried(spec, built, path, heuristic="BLENDER"):
    """The rig checks' failures on the file at `path`, read back."""
    from . import checks, cmd_roundtrip, glb, measure

    cmd_roundtrip.reimport(path, cmd_roundtrip.rate(built), heuristic)
    return {r["id"] for r in checks.carried(spec, built, measure.rigs(), glb.measure(path))
            if not r["ok"]}


def _rig_mutants(spec, P, built, doc, blob):
    """-> (how many, what was missed). A rig exported wrong, or a file that
    moved every part, is red; the real file read back with its bones
    re-oriented is not — position, not angle, is what is compared."""
    from . import cmd_export, glb

    missed, path = [], P.out / "_mutant.glb"
    for name, how, expect in RIG_EXPORTS:
        scene.reset()
        scene.load_collections(P.blend)
        why = cmd_export.write(path, **how)
        failed = {why} if why else _carried(spec, built, path)
        if not expect <= failed:
            missed.append(f"{name} (wanted {sorted(expect)}, got {sorted(failed)})")
    for name, trs in RIG_WRAPS:
        glb.write(path, glb.wrapped(doc, **trs), blob)
        failed = _carried(spec, built, path)
        if "re_motion" not in failed:
            missed.append(f"{name} (wanted ['re_motion'], got {sorted(failed)})")
    failed = _carried(spec, built, P.glb, heuristic="TEMPERANCE")
    if failed:
        missed.append(f"bones re-oriented on import (wanted none, got {sorted(failed)})")
    path.unlink(missing_ok=True)
    return len(RIG_EXPORTS) + len(RIG_WRAPS) + 1, missed


def attach_roundtrip(rep, spec, P, variant, built=None):
    """Corrupt real .glb files and require file_checks (and the re-import) to object.
    With a rig, `built` is the build's, which the rig mutants are read against."""
    from . import cmd_roundtrip, glb

    doc, blob = glb.load(P.glb)
    missed = []
    for name, trs, expect in GLB_MUTANTS:
        path = P.out / "_mutant.glb"
        glb.write(path, glb.wrapped(doc, **trs), blob)
        failed = {r["id"] for r in cmd_roundtrip.file_checks(spec, glb.measure(path)) if not r["ok"]}
        if not expect <= failed:
            missed.append(f"{name} (wanted {sorted(expect)}, got {sorted(failed)})")
    # renamed part: same file, spec expects a name the file does not have
    s2 = {**spec, "parts": [{"name": "plinth_x", "count": 1}, *spec["parts"][1:]]}
    failed = {r["id"] for r in cmd_roundtrip.file_checks(s2, glb.measure(P.glb)) if not r["ok"]}
    if "gl_parts" not in failed:
        missed.append(f"renamed part (wanted gl_parts, got {sorted(failed)})")
    n = len(GLB_MUTANTS) + 1
    # the Blender re-import stage must object to a Z-up file as well
    import verify
    path = P.out / "_mutant.glb"
    glb.write(path, glb.wrapped(doc, rotation=[0.70710678, 0.0, 0.0, 0.70710678]), blob)
    cmd_roundtrip.reimport(path)
    failed = {r["id"] for r in verify.run(spec, variant, only=cmd_roundtrip.RE_CHECKS)
              if not r["ok"]}
    n += 1
    if not ({"height", "depth", "width"} & failed):
        missed.append(f"re-import of z-up file (got {sorted(failed)})")
    path.unlink(missing_ok=True)
    if built:
        k, lost = _rig_mutants(spec, P, built, doc, blob)
        n, missed = n + k, missed + lost
    rep["lines"].append(f"mutants {n - len(missed)}/{n} caught")
    for m in missed:
        rep["lines"].append(f"  FAIL not caught: {m}")
    rep["ok"] = rep["ok"] and not missed
    return rep
