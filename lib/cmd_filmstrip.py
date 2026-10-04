"""./contour filmstrip [clip]: a clip as one picture (ADR 0023, issue 55).

Six frames from the side in the top row, six from the front below, evenly
through the clip, on the sheet's grid and at one scale for all twelve; one
1024² image, labelled with the clip and the build it was drawn from. Which
frames and at what scale is `lib/filmstrip.py`; this poses, renders and
paints, with the sheet's own cameras, grid and glyphs (`lib/cmd_render.py`).

A checkpoint's picture, never a build's (ADR 0005). The build takes the last
one away, so a filmstrip beside a build is always of that build.
"""
import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

from . import cmd_render as sheet
from . import ctx_override, filmstrip, measure, miniyaml, scene, space, views

ROWS = (("side", Vector((20.0, 0, 0))), ("front", Vector((0, -20.0, 0))))
"""Top row first. `side` is the sheet's `right`: a walk reads from there."""


def swept(objects, sc, start, end):
    """The corners every part passes through across the clip, so the camera is
    framed once and a part walking out of the frame cannot."""
    lo, hi = [float("inf")] * 3, [float("-inf")] * 3
    for f in range(start, end + 1):
        sc.frame_set(f)
        for a, b in measure.boxes(objects).values():
            lo = [min(x, y) for x, y in zip(lo, a)]
            hi = [max(x, y) for x, y in zip(hi, b)]
    return lo, hi


def run(args):
    asked = next((a.split("=", 1)[1] for a in args if a.startswith("--clip=")), None)
    P = space.parse([a for a in args if not a.startswith("--clip=")])
    if not P.blend.exists():
        return {"ok": False, "lines": [f"FAIL no build at {P.display(P.blend)}"
                                       f": run ./contour check first"]}
    spec = miniyaml.load(P.spec)
    name, why = filmstrip.clip(spec, asked)
    if why:
        return {"ok": False, "lines": [f"FAIL {why}"]}
    clip = spec["clips"][name]
    scene.reset()
    scene.load_collections(P.blend)
    sc = bpy.context.scene
    rig = next((o for o in sc.objects if o.type == "ARMATURE"), None)
    track = rig and rig.animation_data and rig.animation_data.nla_tracks.get(name)
    if not track:
        return {"ok": False, "lines": [f"FAIL the build has no clip {name}: "
                                       f"run ./contour check first"]}
    meshes = [o for o in sc.objects if o.type == "MESH"]
    wanted = filmstrip.frames(clip["frames"], bool(clip.get("loop")))
    w, h = filmstrip.TILE
    res = w * filmstrip.COLUMNS + (1024 - w * filmstrip.COLUMNS), 2 * h

    with measure.playing(rig, track) as (start, end):
        lo, hi = swept(meshes, sc, start, end)
        ctr = Vector([(a + b) / 2 for a, b in zip(lo, hi)])
        scale = filmstrip.scale(lo, hi)
        sheet.setup(1024)
        sc.render.resolution_x, sc.render.resolution_y = w, h
        segs = sheet.world_segments(lo, hi)
        image = np.ones((res[1], res[0], 4), dtype=np.float32)
        image[..., :3] = sheet.BG
        rows = []
        for r, (label, off) in enumerate(ROWS):
            cam = sheet.add_camera(label, ctr + off, ctr, scale)
            sc.camera = cam
            y0 = (len(ROWS) - 1 - r) * h          # Blender counts rows from the bottom
            tiles = []
            for i, f in enumerate(wanted):
                sc.frame_set(start + f)
                tmp = P.out / f"_film_{label}_{i}.png"
                sc.render.filepath = str(tmp)
                ctx_override.call("render.render", write_still=True)
                tile = sheet.read(tmp)
                tmp.unlink()
                tiles.append(tile.copy())
                bgmask = np.all(np.abs(tile[..., :3] - tile[0, 0, :3]) < 0.02, axis=-1)
                for a, b, colour, width in segs:
                    pa, pb = (world_to_camera_view(sc, cam, Vector(p)) for p in (a, b))
                    if pa.z > 0 and pb.z > 0:
                        sheet.paint(tile, bgmask, (pa.x * w, pa.y * h),
                                    (pb.x * w, pb.y * h), colour, width)
                sheet.text(tile, 6, h - 22, f"{label} f{f}" if i == 0 else f"f{f}")
                image[y0:y0 + h, i * w:(i + 1) * w] = tile
            rows.append(tiles)

    if all(np.array_equal(t, ts[0]) for ts in rows for t in ts):
        return {"ok": False, "lines": [
            f"FAIL {name} does not move in any frame drawn: the filmstrip "
            f"would show a still, and say it was a clip"]}
    image[h - 1:h + 1, :, :3] = 0.35
    for i in range(1, filmstrip.COLUMNS + 1):
        image[:, i * w - 1:i * w + 1, :3] = 0.35
    fp = views.fingerprint(P.blend)
    sheet.text(image, 8, 8, f"{name}  build {fp}  grid 1 m")

    out = bpy.data.images.new("filmstrip", res[0], res[1], alpha=False)
    out.pixels.foreach_set(image.ravel())
    out.filepath_raw = str(P.filmstrip)
    out.file_format = "PNG"
    out.save()
    kb = P.filmstrip.stat().st_size / 1024
    return {"ok": True, "lines": [
        f"{P.name} filmstrip {name} {' '.join(f'f{f}' for f in wanted)} "
        f"| build {fp} | {res[0]}x{res[1]} {kb:.0f}KB -> {P.display(P.filmstrip)}"
        "  (side / front)"]}
