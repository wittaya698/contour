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
    bounds              the world box this part occupies, `(lo, hi)` in metres,
                        or None for a part with no vertices
    scale               the object's own scale, three floats
    rotation_rad        the largest angle the object is turned by, in radians
    uv_layers           how many UV layers it carries
    materials           the material names in its slots, in slot order
    origin              where the object's origin stands in the world, metres

The measurement `scene()` returns holds those records under `parts`, and under
`objects` the name of every object in the scene, mesh or not. A stray empty is
a part list that does not match, and a check reading only meshes would not see
it — so the two are gathered together and each check says which it reads.

Under `contacts` it holds one record per pair of parts whose surfaces cross —
a seam, wherever one exists, whether or not the spec calls it a joint (ADR
0023). The gather reads no spec, so it cannot know which pairs are joints; the
checks pick those out. Each record is

    parts               the two part names, sorted
    centre              the mean of the crossing points, metres: the pivot
    points              how many crossing points there were

A crossing point is where an edge of one part passes from strictly inside the
other to strictly outside. A vertex within `ON_SURFACE` of the other surface
is neither, so a part that sits flush on its parent or meets it at a tangent
point has no crossing and no seam — which is the point (issue 49).

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
from mathutils import Vector, kdtree
from mathutils.bvhtree import BVHTree

# Metres. Closer than this to a surface is on it: neither inside nor out.
ON_SURFACE = 1e-6
# Any direction serves to ask whether a point is inside a closed surface; an
# untidy one keeps the ray off the edges and corners an axis-aligned part has.
RAY = Vector((0.5741, 0.3112, 0.7573)).normalized()


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


def _box(obj, bm):
    """The world box this part occupies, or None for a part with no vertices.

    World and not local, because what a spec states is how big the model is
    where it stands. The scene's box is the union of these, taken in
    `lib/checks.py` — a min over minima is the same number as a min over
    everything, and doing it there keeps the gather free of the aggregate.
    """
    mw = obj.matrix_world
    corners = [mw @ v.co for v in bm.verts]
    if not corners:
        return None
    return ([min(c[i] for c in corners) for i in range(3)],
            [max(c[i] for c in corners) for i in range(3)])


def _rotation(obj):
    """The largest angle this object is turned by, in radians.

    Euler and quaternion in one number, because the question a spec asks is
    `rotation_applied` — whether the object carries any rotation at all — and
    which of Blender's two spellings holds it is not the spec's business.
    """
    worst = max(abs(a) for a in obj.rotation_euler)
    if obj.rotation_mode == "QUATERNION":
        worst = max(worst, abs(obj.rotation_quaternion.angle))
    return worst


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
            "nearest_pair_mm": _nearest_pair(bm),
            "bounds": _box(obj, bm),
            "scale": tuple(obj.scale),
            "rotation_rad": _rotation(obj),
            "uv_layers": len(obj.data.uv_layers),
            "materials": tuple(s.material.name for s in obj.material_slots
                               if s.material),
            "origin": tuple(obj.matrix_world.translation)}


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


def _side(tree, co):
    """1 inside the surface `tree` holds, -1 outside, 0 on it.

    Inside is decided by the first face a ray meets: leaving a closed surface,
    a ray goes out through a face that points the way it is going.
    """
    if tree.find_nearest(co)[3] <= ON_SURFACE:
        return 0
    hit, normal = tree.ray_cast(co, RAY)[:2]
    return 1 if hit is not None and normal.dot(RAY) > 0 else -1


def _crossings(bm, tree):
    """Where the edges of `bm` pass from inside `tree`'s surface to outside."""
    side = {v: _side(tree, v.co) for v in bm.verts}
    out = []
    for e in bm.edges:
        a, b = e.verts
        if side[a] * side[b] != -1:
            continue
        if side[a] < 0:
            a, b = b, a
        step = b.co - a.co
        hit = tree.ray_cast(a.co, step, step.length)[0]
        if hit is not None:
            out.append(hit)
    return out


def _world(obj, dg):
    """The evaluated mesh as a world-space bmesh, its BVH and its box."""
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    ev.to_mesh_clear()
    bm.transform(obj.matrix_world)
    box = _box_of(bm)
    return bm, BVHTree.FromBMesh(bm), box


def _box_of(bm):
    if not bm.verts:
        return None
    return ([min(v.co[i] for v in bm.verts) for i in range(3)],
            [max(v.co[i] for v in bm.verts) for i in range(3)])


def _apart(a, b):
    return any(b[0][i] > a[1][i] + ON_SURFACE or a[0][i] > b[1][i] + ON_SURFACE
               for i in range(3))


def contacts(objects=None):
    """Every pair of parts whose surfaces cross, with the centre of the seam.

    Every pair and not just the joints, because the gather reads no spec;
    pairs whose boxes are apart are skipped, which is most of them.
    """
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    meshes = [o for o in (bpy.context.scene.objects if objects is None else objects)
              if o.type == "MESH"]
    worlds = {o.name: _world(o, dg) for o in meshes}
    out = []
    try:
        names = sorted(worlds)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                (bm_a, tree_a, box_a), (bm_b, tree_b, box_b) = worlds[a], worlds[b]
                if box_a is None or box_b is None or _apart(box_a, box_b):
                    continue
                points = _crossings(bm_a, tree_b) + _crossings(bm_b, tree_a)
                if points:
                    centre = sum(points, Vector()) / len(points)
                    out.append({"parts": (a, b), "centre": tuple(centre),
                                "points": len(points)})
    finally:
        for bm, _, _ in worlds.values():
            bm.free()
    return out


def scene(objects=None):
    """The whole measurement: `{"objects": [name...], "parts": [record...],
    "contacts": [record...]}`.

    What `verify.run` judges, and the only thing it judges. Nothing that has to
    be freed comes back, so there is no `release()` and no ordering obligation
    on the caller (ADR 0020, decision 2).
    """
    objs = list(bpy.context.scene.objects if objects is None else objects)
    return {"objects": [o.name for o in objs], "parts": parts(objs),
            "contacts": contacts(objs)}


def bounds(objects=None):
    """The world box the scene occupies, as `(lo, hi)` — `(None, None)` when
    there is no mesh to measure.

    Its own call, and a cheap one: the sheet wants two corners to frame on and
    used to pay a `bmesh` of every mesh to get them (ADR 0020, decision 5).
    This walks the evaluated vertices and builds nothing.
    """
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = None, None
    for obj in (bpy.context.scene.objects if objects is None else objects):
        if obj.type != "MESH":
            continue
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
        mw = obj.matrix_world
        for v in me.vertices:
            w = mw @ v.co
            if lo is None:
                lo, hi = list(w), list(w)
            else:
                for i in range(3):
                    lo[i], hi[i] = min(lo[i], w[i]), max(hi[i], w[i])
        ev.to_mesh_clear()
    return lo, hi
