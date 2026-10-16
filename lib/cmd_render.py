"""./contour render <variant>: the checkpoint sheet (ADR 0005).

Front / right / top / bottom across the top row, persp as one wide strip
beneath them, in ONE Blender process (separate runs pay ~1.2s startup each). Workbench needs no lights or materials
and adds no render noise.

Workbench does not draw wire-display objects in a final render (verified
2026-09-20), so the 1 m grid, the 1 m rulers and the labels are drawn onto the
finished pixels: world points are projected through the real camera and painted
only where the render is still background, so the model occludes what is behind
it. Ruler ticks are 0.1 m, taller at 0.5 m and 1 m.
"""
import json
import math

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

from . import badges, ctx_override, mask, marks, measure, miniyaml, space, scene
from . import views as sheet_views   # `views` is a local here: the five frames

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
    # A badge prints a mark id, so the digits earn their place here too
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.", "2": ".###.|#...#|....#|...#.|..#..|.#...|#####",
    "3": "####.|....#|....#|.###.|....#|....#|####.", "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.",
    "5": "#####|#....|####.|....#|....#|#...#|.###.", "6": "..##.|.#...|#....|####.|#...#|#...#|.###.",
    "7": "#####|....#|...#.|..#..|.#...|.#...|.#...", "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.",
    "9": ".###.|#...#|#...#|.####|....#|...#.|.##..",
    # A filmstrip prints a clip's name and a build's hex, so the rest of the
    # alphabet is here too (issue 55)
    "a": ".....|.....|.###.|....#|.####|#...#|.####", "b": "#....|#....|####.|#...#|#...#|#...#|####.",
    "c": ".....|.....|.###.|#....|#....|#...#|.###.", "j": "...#.|.....|..##.|...#.|...#.|#..#.|.##..",
    "k": "#....|#....|#..#.|#.#..|##...|#.#..|#..#.", "l": ".##..|..#..|..#..|..#..|..#..|..#..|.###.",
    "q": ".....|.....|.####|#...#|.####|....#|....#", "u": ".....|.....|#...#|#...#|#...#|#..##|.##.#",
    "v": ".....|.....|#...#|#...#|#...#|.#.#.|..#..", "w": ".....|.....|#...#|#...#|#.#.#|#.#.#|.#.#.",
    "x": ".....|.....|#...#|.#.#.|..#..|.#.#.|#...#", "y": ".....|.....|#...#|#...#|.####|....#|.###.",
    "z": ".....|.....|#####|...#.|..#..|.#...|#####", "_": ".....|.....|.....|.....|.....|.....|#####",
    ".": ".....|.....|.....|.....|.....|.##..|.##..", "-": ".....|.....|.....|.###.|.....|.....|.....",
}

BADGE = 2          # glyph scale: 14 px tall on a 512 tile, and readable
GLYPH_W, GLYPH_H = 6 * BADGE, 7 * BADGE


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
    for ch in s.lower():
        for r, row in enumerate(FONT.get(ch, FONT[" "]).split("|")):
            for c, v in enumerate(row):
                if v == "#":
                    y0, x0 = y + (6 - r) * scale, x + c * scale
                    tile[y0:y0 + scale, x0:x0 + scale, :3] = colour
        x += 6 * scale


def layout(res):
    """Each view's tile on the sheet, top-down `(x, y, w, h)`, and the sheet's
    `(width, height)`.

    Four orthographic tiles across, and the perspective beneath them as one
    strip as wide as all four. The sheet keeps the pixels a `res` square has,
    so the agent's look costs what it did when the sheet was 2 x 2.
    """
    t = round(res / (2 * math.sqrt(2)))
    tiles = {label: (i * t, 0, t, t)
             for i, label in enumerate(("front", "right", "top", "bottom"))}
    tiles["persp"] = (0, t, 4 * t, t)
    return tiles, (4 * t, 2 * t)


def add_camera(name, loc, target, ortho_scale=None, turn=None):
    cam = bpy.data.cameras.new(name)
    cam.clip_start, cam.clip_end = 0.05, 200.0
    if ortho_scale:
        cam.type, cam.ortho_scale = "ORTHO", ortho_scale
    else:
        # The lens fitted to the frame's height, and not its width: the persp
        # strip is four times wider than tall, and the model is framed as it
        # was in a square tile, with room either side.
        cam.sensor_fit, cam.sensor_height = "VERTICAL", cam.sensor_width
    o = bpy.data.objects.new(name, cam)
    o.location = loc
    if turn:  # straight down or up: a track-to would be degenerate
        o.rotation_euler = turn
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
    sc.render.resolution_percentage = 100   # the size is each tile's, set per view
    return sc


def index_parts(sc):
    """One index per mesh object, 1..n, in a stable order. The index is written
    into the object colour as i/255 in all three channels, so the rendered pixel
    carries it literally and comes back as the integer it went in as.

    Names are sorted so a rebuild that adds a part does not renumber the rest
    for no reason. 255 is the ceiling, and a build past it is told so rather
    than quietly wrapping onto another part's index.
    """
    parts = sorted((o for o in sc.objects if o.type == "MESH"), key=lambda o: o.name)
    if len(parts) > 255:
        raise ValueError(f"{len(parts)} parts: the identity mask holds 255")
    for i, o in enumerate(parts, start=1):
        o.color = (i / 255, i / 255, i / 255, 1.0)
    return {str(i): o.name for i, o in enumerate(parts, start=1)}


def mask_setup(sc):
    """Turn the sheet pass into an identity pass.

    Everything that makes a render readable makes it lie about identity:
    antialiasing averages two indices into a third part's number, cavity and
    outline darken pixels a part does own, and a view transform bends the value
    away from the index. All four go off. Background is black, which is index 0
    and owns nothing.
    """
    sh = sc.display.shading
    sh.light, sh.color_type = "FLAT", "OBJECT"
    sh.show_cavity = sh.show_object_outline = False
    sc.display.render_aa = "OFF"
    sc.view_settings.view_transform = "Raw"
    sc.world.color = (0, 0, 0)


def pins(path, sc):
    """`[(id, world point)]` for every open mark that knows where it is.

    A mark that has never been resolved has nothing to draw — it is still just
    a pixel on a sheet that no longer exists. A mark whose part has gone is
    said to be orphaned, here, where the build is in front of us, and is not
    drawn anywhere: a badge somewhere plausible would be a lie with a leader
    line attached.

    This is the user's half: a mark whose anchor carries a point in its part's
    own space, from the ray that resolved their click. The agent never clicked
    anything, so its marks name a part and no point on it and are placed from
    the identity mask instead, in `aimless` below.
    """
    here = {o.name: o for o in sc.objects if o.type == "MESH"}
    marks.orphan(path, set(here))
    out = []
    for mark in marks.load(path):
        local = marks.pin(mark)
        if not local or not marks.is_open(mark):
            continue
        live = here.get(marks.part(mark))
        if live:
            m = [c for row in live.matrix_world for c in row]
            out.append((mark["id"], Vector(sheet_views.place(m, local))))
    return out


def aimless(path):
    """`[(id, part)]` for every open mark that names a part and no point on it.

    The agent's marks. It has no pixel to offer, because it never clicked, and
    no point in the part's own space, because it never cast a ray — it knows
    *which part* it has a question about and nothing finer. Where on that part
    the badge goes is decided per view, against the identity mask, in `on_part`.

    A user's mark that is still carrying a pixel is not among them, whatever the
    mask read under it: it is waiting on a ray, and badging it here would put a
    leader line on a pin nobody has cast yet.
    """
    return [(m["id"], marks.part(m)) for m in marks.load(path)
            if marks.is_open(m) and marks.part(m)
            and not marks.pin(m) and not marks.pixel(m)]


def on_part(idtile, number):
    """A point on this part as this view actually sees it, or None.

    The mean of a part's pixels is not always one of them — beaky's arm is an
    L, and the middle of its bounding box falls in the hole beside the torso,
    on the background. So the mean is taken and then the nearest pixel that
    really belongs to the part is returned, which puts the badge on the part
    for any shape at all.

    None when this view cannot see the part: no badge is better than a badge
    pointing at whatever is in front of it.
    """
    ys, xs = np.nonzero(idtile == number)
    if not len(xs):
        return None
    return badges.nearest(list(zip(xs.tolist(), ys.tolist())))



def badge(tile, bgmask, label, at, bounds, taken):
    """Draw one badge near a pin, leashed to it. Returns its pixel, or None
    when the tile is too crowded to place it without covering geometry.

    The pin itself is always *on* a part, so nothing is ever drawn there; the
    leader line is painted the same way the grid is, which makes it disappear
    behind the model exactly where it should.
    """
    x, y = at
    w, h = GLYPH_W * len(label), GLYPH_H
    spot = badges.badge_spot(
        lambda bx, by, bw, bh: bool(bgmask[by:by + bh, bx:bx + bw].all()),
        x, y, w, h, bounds, taken=taken)
    if spot is None:
        return None
    bx, by = spot
    taken.append((bx, by, w, h))
    paint(tile, bgmask, (x, y), (bx + w / 2, by + h / 2), INK, 1)
    text(tile, bx, by, label, scale=BADGE)
    return bx, by


def view_record(label, tile, cam):
    """What it takes to cast this view's rays again, in about 200 bytes: the
    tile it occupies on the sheet, and the camera that drew it.

    The camera is stored as its parameters rather than as a ray table, because
    a ray per pixel is a position buffer by another name (ADR 0018) — and
    because rebuilding the camera is the only way to be sure the ray matches
    the projection that put the pixel there.
    """
    d = cam.data
    return {"label": label, "tile": list(tile),
            "matrix": [c for row in cam.matrix_world for c in row],
            "type": d.type, "lens": d.lens, "ortho_scale": d.ortho_scale,
            "sensor_fit": d.sensor_fit, "sensor_width": d.sensor_width,
            "sensor_height": d.sensor_height,
            "shift_x": d.shift_x, "shift_y": d.shift_y,
            "clip": [d.clip_start, d.clip_end]}


def read(path, raw=False):
    img = bpy.data.images.load(str(path))
    if raw:  # the mask is data, not a picture: no sRGB on the way back in
        img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    return buf.reshape(h, w, 4)


def badge_line(variant, placed):
    """What the sheet now shows, in one line and never more — the first view
    each pin landed in, three of them, then a count. A badge is there to be
    looked at, not read out."""
    if not placed:
        return []
    shown = [f"{mid} {label} {x},{y}" for mid, (label, x, y) in list(placed.items())[:3]]
    if len(placed) > 3:
        shown.append(f"+{len(placed) - 3} more")
    n = len(placed)
    return [f"{variant} {n} badge{'' if n == 1 else 's'}  " + "  ".join(shown)]


def run(args):
    P = space.parse(args)
    variant = P.name
    if not P.blend.exists():
        return {"ok": False, "lines": [f"FAIL no build at {P.display(P.blend)}"
                                       f": run ./contour check {variant} first"]}
    spec = miniyaml.load(P.spec)
    res = int((spec.get("render") or {}).get("sheet_resolution", 1024))
    scene.reset()
    scene.load_collections(P.blend)
    # Two corners to frame on, and nothing built to get them (ADR 0020).
    lo, hi = measure.bounds()

    ext = [h - l for l, h in zip(lo, hi)]
    ctr = Vector([(l + h) / 2 for l, h in zip(lo, hi)])
    scale = sheet_views.sheet_scale(lo, hi)
    d = 1.2 * (math.sqrt(sum(e * e for e in ext)) / 2) / math.sin(math.atan(18 / 50))
    far = 20.0
    views = [  # sheet order: the top row left to right, then the strip
        ("front", ctr + Vector((0, -far, 0)), scale, None),
        ("right", ctr + Vector((far, 0, 0)), scale, None),
        ("top", ctr + Vector((0, 0, far)), scale, (0.0, 0.0, 0.0)),    # +Y up the frame
        ("bottom", ctr + Vector((0, 0, -far)), scale, (math.pi, 0.0, 0.0)),  # front up
        ("persp", ctr + Vector((0.75, -1.0, 0.6)).normalized() * d, None, None),
    ]
    sc = setup(res)
    segs = world_segments(lo, hi)
    # Top-down tile rects, the way a click counts.
    rects, (W, H) = layout(res)
    P.out.mkdir(parents=True, exist_ok=True)
    pinned, placed = pins(P.marks, sc), {}
    noted = aimless(P.marks)
    tiles, cams, spare = [], [], []
    for label, loc, orth, turn in views:
        cam = add_camera(label, loc, ctr, orth, turn)
        cams.append((label, cam))
        sc.camera = cam
        cx, cy, w, h = rects[label]
        sc.render.resolution_x, sc.render.resolution_y = w, h
        tmp = P.out / f"_view_{label}.png"
        sc.render.filepath = str(tmp)
        ctx_override.call("render.render", write_still=True)
        tile = read(tmp)
        tmp.unlink()
        bgmask = np.all(np.abs(tile[..., :3] - tile[0, 0, :3]) < 0.02, axis=-1)
        for a, b, colour, width in segs:
            pa, pb = (world_to_camera_view(sc, cam, Vector(p)) for p in (a, b))
            if pa.z <= 0 or pb.z <= 0:  # behind the camera
                continue
            paint(tile, bgmask, (pa.x * w, pa.y * h), (pb.x * w, pb.y * h), colour, width)
        text(tile, 8, h - 22, f"{label}   grid 1 m")
        taken = []
        for mid, world in pinned:
            at = world_to_camera_view(sc, cam, world)
            if at.z <= 0 or not (0 <= at.x <= 1 and 0 <= at.y <= 1):
                continue                       # behind this camera, or off its frame
            if badge(tile, bgmask, mid, (at.x * w, at.y * h), (w, h), taken) \
                    and mid not in placed:
                placed[mid] = (label, int(cx + at.x * w), int(cy + h - at.y * h))
        tiles.append(tile)
        spare.append((bgmask, taken))    # the agent's badges go on after the mask

    # Second pass, same cameras, same process: a pixel is a part number.
    parts = index_parts(sc)
    mask_setup(sc)
    mtiles = []
    for label, cam in cams:
        sc.camera = cam
        _x, _y, w, h = rects[label]
        sc.render.resolution_x, sc.render.resolution_y = w, h
        tmp = P.out / f"_mask_{label}.png"
        sc.render.filepath = str(tmp)
        ctx_override.call("render.render", write_still=True)
        mtiles.append(np.round(read(tmp, raw=True)[..., 0] * 255).astype(np.uint8))
        tmp.unlink()
    # Third pass, no render: the agent's marks name a part and no point on it,
    # so the mask that was just made is what says where on the part they go.
    number = {name: int(i) for i, name in parts.items()}
    for (label, _cam), tile, (bgmask, taken), idtile in zip(cams, tiles, spare,
                                                            mtiles):
        for mid, part in noted:
            spot = on_part(idtile, number.get(part, -1))
            cx, cy, w, h = rects[label]
            if spot and badge(tile, bgmask, mid, spot, (w, h), taken) \
                    and mid not in placed:
                placed[mid] = (label, int(cx + spot[0]), int(cy + h - spot[1]))

    def bottom_up(label):
        """A tile's rows and columns in Blender's pixel order, which counts
        rows from the bottom where a click counts them from the top."""
        x, y, w, h = rects[label]
        return slice(H - y - h, H - y), slice(x, x + w)

    idx = np.zeros((H, W), dtype=np.uint8)
    for (label, _cam), tile in zip(cams, mtiles):
        idx[bottom_up(label)] = tile
    mask.write(P.mask, np.flipud(idx))   # Blender reads bottom-up, PNG top-down
    P.parts.write_text(json.dumps(parts, indent=2) + "\n", encoding="utf-8")

    sheet_views.record(P.views, res,
                       [view_record(label, rects[label], cam)
                        for label, cam in cams], P.blend)

    sheet = np.ones((H, W, 4), dtype=np.float32)
    for (label, _cam), tile in zip(cams, tiles):
        rows, cols = bottom_up(label)
        sheet[rows, cols] = tile
        if cols.start:                       # a rule down its left edge
            sheet[rows, cols.start - 1:cols.start + 1, :3] = 0.35
        if rows.start:                       # and along its foot
            sheet[rows.start - 1:rows.start + 1, cols, :3] = 0.35
    out = bpy.data.images.new("sheet", W, H, alpha=False)
    out.pixels.foreach_set(sheet.ravel())
    P.sheet.parent.mkdir(parents=True, exist_ok=True)
    out.filepath_raw = str(P.sheet)
    out.file_format = "PNG"
    out.save()
    kb = P.sheet.stat().st_size / 1024
    return {"ok": True, "lines": [f"{variant} sheet {W}x{H} {kb:.0f}KB -> "
                                  f"{P.display(P.sheet)}"
                                  "  (front|right|top|bottom / persp)",
                                  f"{variant} mask {len(parts)} parts -> "
                                  f"{P.display(P.mask)}",
                                  *badge_line(variant, placed)]}
