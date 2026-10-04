"""Small helpers for build.py files. bmesh and the data API only (ADR 0004).

Units: author in millimetres, Blender stores metres. Helpers take mm.
Every builder returns a fresh bmesh centred on the origin; `add` turns it into an
object placed at `at_mm`. The arithmetic and the validation are `lib/units.py`,
where a test can reach them without Blender; `mm` and `MM` are re-exported here
because every space's build spells them `kit.mm` (issue 26).
"""
import bmesh
import bpy
from mathutils import Matrix, Vector

from . import ctx_override
from .units import MM, linear, mm, size  # noqa: F401  (MM, mm: kit's own names)

# The spec being built, handed over by `lib/cmd_build.py` before `build.py`
# runs, so that `rig()` reads the tree from where the user wrote it and a
# space's build declares nothing the spec already says (ADR 0023).
_spec = None


def material(name, hex_colour, roughness=0.9):
    """A matte material. The viewport colour drives Workbench renders; the
    Principled base colour is what the glTF exporter reads."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    lin = linear(hex_colour)
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*lin, 1.0)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    return m


def box_bm(size_mm):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size(size_mm), verts=bm.verts)
    return bm


def sphere_bm(radius_mm, segments=32, rings=24):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=mm(radius_mm))
    return bm


def cylinder_bm(radius_mm, depth_mm, segments=32, cap_tris=False):
    """Axis along Z. cap_tris=False leaves n-gon caps; True fans them into triangles."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=cap_tris, segments=segments,
                          radius1=mm(radius_mm), radius2=mm(radius_mm), depth=mm(depth_mm))
    return bm


def add(name, bm, at_mm=(0, 0, 0), mat=None, smooth=False, pivot_mm=None):
    """bmesh -> linked object named `name`. Frees the bmesh.

    The mesh is centred on `at_mm`. The origin is there too, unless `pivot_mm`
    puts it at the joint the part turns about — which a rigged part's must be,
    on the centre of its seam (ADR 0023).
    """
    if pivot_mm is not None:
        bmesh.ops.translate(bm, vec=mm(*(a - p for a, p in zip(at_mm, pivot_mm))),
                            verts=bm.verts)
        at_mm = pivot_mm
    for f in bm.faces:
        f.smooth = smooth
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if mat:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    obj.location = mm(*at_mm)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def bake_transform(obj):
    """Fold obj.matrix_world into its vertices and reset it: scale and rotation
    applied without an operator."""
    me, m = obj.data, obj.matrix_world.copy()
    loc = Matrix.Translation(m.to_translation())
    linear = loc.inverted() @ m
    me.transform(linear)
    obj.matrix_world = loc
    return obj


def rig():
    """The armature the spec's tree describes, bound rigidly (ADR 0023).

    One bone per part, named after it, its head on the part's origin — the
    pivot, which `pivots` checks — and hanging from its parent's bone. Every
    bone points up +Z with no roll, so every bone's frame at rest is the
    world's, and a pose in degrees reads the same way on any bone.

    Each part's every vertex is weighted 1 to its own bone, and an armature
    modifier binds it, all through the data API. Parts are not parented to the
    rig as objects, so every origin and transform reads as it did before. Only
    the bones need edit mode, entered and left by the whitelisted
    `object.mode_set` (issue 47). Call it last, once every part exists.
    """
    tree = {p["name"]: p.get("parent") for p in (_spec or {}).get("parts") or []}
    if not any(tree.values()):
        raise ValueError("kit.rig(): the spec has no rig; give its parts a parent:")
    parts = {name: bpy.data.objects[name] for name in tree}
    arm = bpy.data.armatures.new("rig")
    obj = bpy.data.objects.new("rig", arm)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    ctx_override.call("object.mode_set", mode="EDIT")
    try:
        for name, part in parts.items():
            bone = arm.edit_bones.new(name)
            bone.head = part.matrix_world.translation
            bone.tail = bone.head + Vector((0.0, 0.0, max(part.dimensions.z / 2, mm(10))))
        for name, parent in tree.items():
            if parent:
                arm.edit_bones[name].parent = arm.edit_bones[parent]
    finally:
        ctx_override.call("object.mode_set", mode="OBJECT")
    for name, part in parts.items():
        group = part.vertex_groups.new(name=name)
        group.add(range(len(part.data.vertices)), 1.0, "REPLACE")
        part.modifiers.new("rig", "ARMATURE").object = obj
    return obj
