"""./contour render <variant>: the 4-view checkpoint sheet (ADR 0005).

Front / right / top / persp, top-left to bottom-right, in ONE Blender process
(separate runs pay ~1.2s startup each). Workbench needs no lights or materials
and adds no render noise.

Workbench does not draw wire-display objects in a final render (verified
2026-09-20), so the 1 m grid, the 1 m rulers and the labels are drawn onto the
finished pixels: world points are projected through the real camera and painted
only where the render is still background, so the model occludes what is behind
it. Ruler ticks are 0.1 m, taller at 0.5 m and 1 m.
"""
import math

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

from . import ctx_override, miniyaml, paths, scene

BG = (0.93, 0.93, 0.94)
GRID = (0.72, 0.74, 0.78)
RULER = {"x": (0.85, 0.15, 0.15), "y": (0.15, 0.6, 0.2), "z": (0.15, 0.3, 0.85)}
INK = (0.2, 0.2, 0.22)

# 5x7 glyphs for the only words the sheet prints
FONT = {
    "f": "..##.|.#...|###..|.#...|.#...|.#...|.#...", "r": ".....|.....|#.##.|##..#|#....|#....|#....",
    "o": ".....|.....|.###.|#...#|#...#|#...#|.###.", "n": ".....|.....|####.|#...#|#...#|#...#|#...#",
    "t": ".#...|.#...|###..|.#...|.#...|.#..#|..##.", "i": "..#..|.....|.##..|..#..|..#..|..#..|.###.",
    "g": ".....|.....|.####|#...#|.####|....#|.###.", "h": "#....|#....|####.|#...#|#...#|#...#|#...#",
    "p": ".....|.....|####.|#...#|####.|#....|#....", "e": ".....|.....|.###.|#...#|#####|#....|.###.",
    "s": ".....|.....|.####|#....|.###.|....#|####.", "d": "....#|....#|.####|#...#|#...#|#...#|.####",
    "m": ".....|.....|##.#.|#.#.#|#.#.#|#.#.#|#.#.#", "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    " ": ".....|.....|.....|.....|.....|.....|.....",
}


def world_segments(lo, hi):
    """[(p0, p1, colour, width_px)] for the 1 m grid (floor + two back walls) and rulers."""
    x0, x1 = math.floor(lo[0]) - 1, math.ceil(hi[0]) + 1
    y0, y1 = math.floor(lo[1]) - 1, math.ceil(hi[1]) + 1
    z1 = max(math.ceil(hi[2]), 1) + 1
    g = []
    for x in range(x0, x1 + 1):
        g += [((x, y0, 0), (x, y1, 0)), ((x, y1, 0), (x, y1, z1))]
    for y in range(y0, y1 + 1):
        g += [((x0, y, 0), (x1, y, 0)), ((x0, y, 0), (x0, y, z1))]
    for z in range(0, z1 + 1):
        g += [((x0, y1, z), (x1, y1, z)), ((x0, y0, z), (x0, y1, z))]
    segs = [(a, b, GRID, 1) for a, b in g]
    o = Vector((lo[0] - 0.2, hi[1] + 0.2, 0.0))
    dirs = {"x": Vector((1, 0, 0)), "y": Vector((0, -1, 0)), "z": Vector((0, 0, 1))}
    for k, d in dirs.items():
        segs.append((tuple(o), tuple(o + d), RULER[k], 2))
        for i in range(11):
            p, n = o + d * (i / 10), (0.06 if i % 5 == 0 else 0.03)
            for kk, perp in dirs.items():
                if kk != k:
                    segs.append((tuple(p - perp * n / 2), tuple(p + perp * n / 2), RULER[k], 1))
    return segs


def paint(tile, bgmask, p0, p1, colour, width):
    """Paint a segment given in pixel coords, only over background pixels."""
    h, w = tile.shape[:2]
    n = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))) * 2 + 2
    xs, ys = np.linspace(p0[0], p1[0], n), np.linspace(p0[1], p1[1], n)
    for ox in range(width):
        for oy in range(width):
            ix, iy = np.round(xs + ox - 0.5).astype(int), np.round(ys + oy - 0.5).astype(int)
            ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
            ix, iy = ix[ok], iy[ok]
            keep = bgmask[iy, ix]
            tile[iy[keep], ix[keep], :3] = colour


def text(tile, x, y, s, scale=2, colour=INK):
    """Paint `s` with its bottom-left at pixel (x, y)."""
    for ch in s:
        for r, row in enumerate(FONT[ch].split("|")):
            for c, v in enumerate(row):
                if v == "#":
                    y0, x0 = y + (6 - r) * scale, x + c * scale
                    tile[y0:y0 + scale, x0:x0 + scale, :3] = colour
        x += 6 * scale


def add_camera(name, loc, target, ortho_scale=None, look_down=False):
    cam = bpy.data.cameras.new(name)
    cam.clip_start, cam.clip_end = 0.05, 200.0
    if ortho_scale:
        cam.type, cam.ortho_scale = "ORTHO", ortho_scale
    o = bpy.data.objects.new(name, cam)
    o.location = loc
    if look_down:  # straight down, +Y up the frame (a track-to would be degenerate)
        o.rotation_euler = (0.0, 0.0, 0.0)
    else:
        o.rotation_euler = (Vector(target) - Vector(loc)).normalized() \
            .to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(o)
    return o


def setup(res):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light, sh.color_type = "STUDIO", "MATERIAL"
    sh.show_cavity, sh.show_object_outline = True, True
    sc.world = bpy.data.worlds.new("sheet")
    sc.world.color = BG
    sc.view_settings.view_transform = "Standard"
    sc.render.dither_intensity = 0.0  # noise only bloats the PNG
    sc.render.image_settings.file_format = "PNG"
    sc.render.resolution_x = sc.render.resolution_y = res // 2
    sc.render.resolution_percentage = 100
    return sc


def read(path):
    img = bpy.data.images.load(str(path))
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    return buf.reshape(h, w, 4)


def run(args):
    import verify

    variant, fixture = paths.parse(args)
    P = paths.resolve(variant, fixture)
    if not P["blend"].exists():
        return {"ok": False, "lines": [f"FAIL no build at {paths.display(P['blend'])}"
                                       f": run ./contour check {variant} first"]}
    spec = miniyaml.load(P["spec"])
    res = int((spec.get("render") or {}).get("sheet_resolution", 1024))
    scene.reset()
    scene.load_collections(P["blend"])
    m = verify.measure()
    lo, hi = list(m["lo"]), list(m["hi"])
    verify.release(m)

    ext = [h - l for l, h in zip(lo, hi)]
    ctr = Vector([(l + h) / 2 for l, h in zip(lo, hi)])
    scale = max(1.12 * max(ext) + 0.6, 1.5)  # the 1 m ruler must fit the frame
    d = 1.2 * (math.sqrt(sum(e * e for e in ext)) / 2) / math.sin(math.atan(18 / 50))
    far = 20.0
    views = [  # sheet order: top-left, top-right, bottom-left, bottom-right
        ("front", ctr + Vector((0, -far, 0)), scale, False),
        ("right", ctr + Vector((far, 0, 0)), scale, False),
        ("top", ctr + Vector((0, 0, far)), scale, True),
        ("persp", ctr + Vector((0.75, -1.0, 0.6)).normalized() * d, None, False),
    ]
    sc = setup(res)
    segs = world_segments(lo, hi)
    t = res // 2
    P["out"].mkdir(parents=True, exist_ok=True)
    tiles = []
    for label, loc, orth, down in views:
        cam = add_camera(label, loc, ctr, orth, down)
        sc.camera = cam
        tmp = P["out"] / f"_view_{label}.png"
        sc.render.filepath = str(tmp)
        ctx_override.call("render.render", write_still=True)
        tile = read(tmp)
        tmp.unlink()
        bgmask = np.all(np.abs(tile[..., :3] - tile[0, 0, :3]) < 0.02, axis=-1)
        for a, b, colour, width in segs:
            pa, pb = (world_to_camera_view(sc, cam, Vector(p)) for p in (a, b))
            if pa.z <= 0 or pb.z <= 0:  # behind the camera
                continue
            paint(tile, bgmask, (pa.x * t, pa.y * t), (pb.x * t, pb.y * t), colour, width)
        text(tile, 8, t - 22, f"{label}   grid 1 m")
        tiles.append(tile)

    sheet = np.ones((res, res, 4), dtype=np.float32)
    for (row, col), tile in zip([(1, 0), (1, 1), (0, 0), (0, 1)], tiles):
        sheet[row * t:(row + 1) * t, col * t:(col + 1) * t] = tile
    sheet[t - 1:t + 1, :, :3] = 0.35
    sheet[:, t - 1:t + 1, :3] = 0.35
    out = bpy.data.images.new("sheet", res, res, alpha=False)
    out.pixels.foreach_set(sheet.ravel())
    P["sheet"].parent.mkdir(parents=True, exist_ok=True)
    out.filepath_raw = str(P["sheet"])
    out.file_format = "PNG"
    out.save()
    kb = P["sheet"].stat().st_size / 1024
    return {"ok": True, "lines": [f"{variant} sheet {res}x{res} {kb:.0f}KB -> "
                                  f"{paths.display(P['sheet'])}"
                                  "  (front|right / top|persp)"]}
