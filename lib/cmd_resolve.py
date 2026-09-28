"""./contour resolve: one ray per unresolved mark, at the last moment before
geometry can change (ADR 0018, and its trigger amended by ADR 0019).

Run by whoever knows that moment. `contour canvas` runs it when the page says
done, because that host owns no build and so cannot know of one coming; the
console runs it the instant it approves a build, which is strictly better — it
owns the build, so it knows exactly when the geometry under these rays is about
to be replaced. Either way it is one Blender startup per batch of pins, not one
per click. It rebuilds each sheet camera from what `views.json` recorded, casts
a ray through the pixel the user clicked, and stores where it landed in the hit
part's own coordinates.

It refuses outright if the build has moved on since the sheet was drawn. The
ray would still land somewhere; it would just be somewhere the user never saw.
"""
import bpy
from mathutils import Matrix, Vector

from . import anchor, marks, space, scene, store

PULLBACK = 100.0   # metres to back an orthographic ray off before it starts


def camera_from(view):
    """The camera that drew this tile, rebuilt from its parameters."""
    d = bpy.data.cameras.new(view["label"])
    d.type = view["type"]
    d.lens, d.ortho_scale = view["lens"], view["ortho_scale"]
    d.sensor_fit = view["sensor_fit"]
    d.sensor_width, d.sensor_height = view["sensor_width"], view["sensor_height"]
    d.shift_x, d.shift_y = view["shift_x"], view["shift_y"]
    d.clip_start, d.clip_end = view["clip"]
    o = bpy.data.objects.new(view["label"], d)
    m = view["matrix"]
    o.matrix_world = Matrix([m[r * 4:(r + 1) * 4] for r in range(4)])
    bpy.context.scene.collection.objects.link(o)
    return o


def ray(sc, cam, view, u, v):
    """`(origin, direction)` through a point in this camera's frame.

    `view_frame` gives the four corners of what the camera sees, in its own
    space, so the ray is built from the same projection that put the pixel on
    the sheet rather than from a re-derivation of it. It answers in the render
    aspect of *this* scene, though, which starts out 16:9 — so the tile's own
    square is set first, or every ray sits low by the difference.

    A perspective ray starts at the lens; a parallel one has no lens to start
    at, so it is backed off along its own direction until it begins outside
    anything it might otherwise have begun inside.
    """
    _x, _y, w, h = view["tile"]
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    tr, br, bl, tl = cam.data.view_frame(scene=sc)
    point = cam.matrix_world @ (bl + (br - bl) * u + (tl - bl) * v)
    if cam.data.type == "PERSP":
        origin = cam.matrix_world.translation
        return origin, (point - origin).normalized()
    forward = (cam.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
    return point - forward * PULLBACK, forward


def run(args):
    P = space.parse(args)
    variant = P.name
    sheet = store.load(P.views, None)
    if sheet is None:
        return {"ok": True, "lines": [f"{variant} resolve no views.json: "
                                      "this sheet predates anchoring"]}
    drift = anchor.stale(sheet, P.blend)
    if drift:
        return {"ok": False, "lines": [f"FAIL resolve {drift}"]}
    todo = marks.unresolved(marks.load(P.marks))
    if not todo:
        return {"ok": True, "lines": [f"{variant} resolve nothing to anchor"]}

    scene.reset()
    scene.load_collections(P.blend)
    sc = bpy.context.scene
    cams = {v["label"]: camera_from(v) for v in sheet["views"]}
    dg = bpy.context.evaluated_depsgraph_get()
    found, missed = {}, 0
    for mark in todo:
        aimed = anchor.aim(sheet, marks.pixel(mark))
        cam = cams.get(marks.view(mark)) if aimed else None
        if cam is None or aimed[0]["label"] != marks.view(mark):
            missed += 1                       # a pixel on no tile, or on another view
            continue
        origin, direction = ray(sc, cam, aimed[0], aimed[1], aimed[2])
        hit, location, _n, _i, obj, matrix = sc.ray_cast(dg, origin, direction)
        if not hit:
            missed += 1                       # background: a remark about the gap
            continue
        local = matrix.inverted() @ location
        found[mark["id"]] = {"part": obj.name,
                             "local": [round(c, 6) for c in local]}
    marks.anchor(P.marks, found)
    line = f"{variant} resolve {marks.phrase(len(found))} anchored"
    if missed:
        line += f", {missed} on background"
    return {"ok": True, "lines": [line]}
