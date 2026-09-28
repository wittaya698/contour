"""Gather a measurement: summary numbers per part, no live geometry (ADR 0020).

`verify.measure()` gathers an instrument — `bmesh` handles the checks then read
in place — which is why no check can run outside Blender and why the caller is
left holding a lifetime. This gathers the reading instead. What comes back is a
list of plain records: ints, floats, strings, and nothing that has to be freed.

Every `bmesh` built here is freed here, so there is no `release()` to forget
(ADR 0020, decision 2).

The fields, per part:

    name                one part's object name
    faces               face degree -> how many faces have it; triangles are 3,
                        quads 4, n-gons above that. `tris`, `quads` and `ngons`
                        are all arithmetic over this one histogram
    verts, edges        how many of each
    non_manifold_edges  edges with other than two faces
    loose_verts         vertices attached to no edge
    loose_edges         edges attached to no face
    flipped_faces       faces that disagree with a recomputed outward normal
    nearest_pair_mm     how close the closest two vertices came, in mm, or None
                        for a part with fewer than two vertices

`verts` and `edges` are gathered and no check reads them, which ADR 0020 says
to expect and to list: a gather edited for every new check is a gather that
will be edited constantly, so a few unread numbers is the cheaper mistake.

`nearest_pair_mm` is not the duplicate-vertex *count* the ADR drafted. A count
of duplicates is a count at some tolerance, and the tolerance is in the spec,
which a gather does not read. The distance answers the same question for any
tolerance and says how close rather than how many (issue 22).
"""
import bmesh
import bpy
from mathutils import kdtree


def _degrees(bm):
    """The face-degree histogram: how many faces have each vertex count."""
    out = {}
    for face in bm.faces:
        n = len(face.verts)
        out[n] = out.get(n, 0) + 1
    return out


def _flipped(bm):
    """Faces pointing the other way from a recomputed outward normal.

    Decided against a copy, because deciding it at all needs real geometry —
    which is the work this module exists to do once, so that the check reading
    the answer needs none.
    """
    ref = bm.copy()
    bmesh.ops.recalc_face_normals(ref, faces=ref.faces)
    ref.normal_update()
    bm.faces.ensure_lookup_table()
    ref.faces.ensure_lookup_table()
    n = sum(1 for a, b in zip(bm.faces, ref.faces) if a.normal.dot(b.normal) < 0)
    ref.free()
    return n


def _nearest_pair(bm):
    """Millimetres between the closest two vertices, or None if there is no
    pair. A tree rather than every pair against every other: a part with ten
    thousand vertices is fifty million comparisons done the obvious way."""
    verts = bm.verts
    if len(verts) < 2:
        return None
    tree = kdtree.KDTree(len(verts))
    for i, v in enumerate(verts):
        tree.insert(v.co, i)
    tree.balance()
    # The nearest neighbour of a vertex is itself, at zero, so the pair is the
    # second answer. The smallest over every vertex is the closest pair.
    return 1000.0 * min(tree.find_n(v.co, 2)[1][2] for v in verts)


def part(obj, bm):
    """One part's record, from a mesh already built."""
    return {"name": obj.name,
            "faces": _degrees(bm),
            "verts": len(bm.verts),
            "edges": len(bm.edges),
            "non_manifold_edges": sum(1 for e in bm.edges if not e.is_manifold),
            "loose_verts": sum(1 for v in bm.verts if not v.link_edges),
            "loose_edges": sum(1 for e in bm.edges if not e.link_faces),
            "flipped_faces": _flipped(bm),
            "nearest_pair_mm": _nearest_pair(bm)}


def parts(objects=None):
    """A measurement of the evaluated scene: one record per mesh part.

    Evaluated, like `verify.measure()`, so a part is judged as it will be
    exported and not as it was authored.
    """
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for obj in (bpy.context.scene.objects if objects is None else objects):
        if obj.type != "MESH":
            continue
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(me)
        ev.to_mesh_clear()
        bm.normal_update()
        try:
            out.append(part(obj, bm))
        finally:
            bm.free()
    return out
