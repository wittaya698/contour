"""Prove verify can fail. A verifier that always passes would also pass selftest,
so each mutant breaks the fixture in one known way and must be caught by name."""
import bmesh
import bpy

from . import kit, scene
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
        failed = {r["id"] for r in verify.run(s, variant, None) if not r["ok"]}
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


def attach_roundtrip(rep, spec, P, variant):
    """Corrupt real .glb files and require file_checks (and the re-import) to object."""
    from . import cmd_roundtrip, ctx_override, glb

    doc, blob = glb.load(P["glb"])
    missed = []
    for name, trs, expect in GLB_MUTANTS:
        path = P["out"] / "_mutant.glb"
        glb.write(path, glb.wrapped(doc, **trs), blob)
        failed = {r["id"] for r in cmd_roundtrip.file_checks(spec, glb.measure(path)) if not r["ok"]}
        if not expect <= failed:
            missed.append(f"{name} (wanted {sorted(expect)}, got {sorted(failed)})")
    # renamed part: same file, spec expects a name the file does not have
    s2 = {**spec, "parts": [{"name": "plinth_x", "count": 1}, *spec["parts"][1:]]}
    failed = {r["id"] for r in cmd_roundtrip.file_checks(s2, glb.measure(P["glb"])) if not r["ok"]}
    if "gl_parts" not in failed:
        missed.append(f"renamed part (wanted gl_parts, got {sorted(failed)})")
    n = len(GLB_MUTANTS) + 1
    # the Blender re-import stage must object to a Z-up file as well
    import verify
    path = P["out"] / "_mutant.glb"
    glb.write(path, glb.wrapped(doc, rotation=[0.70710678, 0.0, 0.0, 0.70710678]), blob)
    scene.reset()
    ctx_override.call("import_scene.gltf", filepath=str(path))
    failed = {r["id"] for r in verify.run(spec, variant, None, only=cmd_roundtrip.RE_CHECKS)
              if not r["ok"]}
    n += 1
    if not ({"height", "depth", "width"} & failed):
        missed.append(f"re-import of z-up file (got {sorted(failed)})")
    path.unlink(missing_ok=True)
    rep["lines"].append(f"mutants {n - len(missed)}/{n} caught")
    for m in missed:
        rep["lines"].append(f"  FAIL not caught: {m}")
    rep["ok"] = rep["ok"] and not missed
    return rep
