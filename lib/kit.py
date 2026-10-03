"""Small helpers for build.py files. bmesh and the data API only (ADR 0004).

Units: author in millimetres, Blender stores metres. Helpers take mm.
Every builder returns a fresh bmesh centred on the origin; `add` turns it into an
object placed at `at_mm`. The arithmetic and the validation are `lib/units.py`,
where a test can reach them without Blender; `mm` and `MM` are re-exported here
because every space's build spells them `kit.mm` (issue 26).
"""
import bmesh
import bpy
from mathutils import Matrix

from .units import MM, linear, mm, size  # noqa: F401  (MM, mm: kit's own names)


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
