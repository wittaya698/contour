"""Anchoring: where a mark really is, once a pixel is no longer good enough
(ADR 0018).

`contour render` leaves a `views.json` beside the sheet — the four tiles and
the cameras that drew them, plus a fingerprint of the build they were drawn
from. A mark is born carrying a pixel; one Blender run per canvas session
casts a ray through that pixel and writes back the surface point in the hit
part's own coordinates, and the pixel goes away. Move the part and the pin
moves with it.

Everything here is stdlib and knows nothing about Blender: the ray is cast in
`lib/cmd_resolve.py`, which is the only part that needs a scene.
"""
import hashlib
import json
from pathlib import Path

from . import marks


def aim(sheet, pixel):
    """`(view, u, v)` for a sheet pixel, or None when it is on no tile.

    A click counts from the top left, the way the browser and the mask do; a
    camera frame counts from the bottom left in 0..1. So the tile is found by
    rectangle and the row is flipped, once, here.
    """
    x, y = pixel
    for view in sheet["views"]:
        tx, ty, w, h = view["tile"]
        if tx <= x < tx + w and ty <= y < ty + h:
            return view, (x - tx + 0.5) / w, 1.0 - (y - ty + 0.5) / h
    return None


def apply(path, found):
    """Write back what the rays found: `{mark id: {"part", "local"}}`.

    The pixel is dropped as the anchor lands, so `unresolved` needs no flag to
    read and no mark ever carries two answers to the same question. Returns
    the ids that were anchored.
    """
    kept = marks.load(path)
    done = []
    for mark in kept:
        if mark.get("ref"):
            continue          # a photograph has no parts to be anchored in
        hit = found.get(mark.get("id"))
        if hit:
            mark.pop("pixel", None)
            mark["anchor"] = hit
            done.append(mark["id"])
    if done:
        marks.save(path, kept)
    return done


def unresolved(all_marks):
    """The marks still waiting on a ray: a pixel, and no anchor yet.

    A ref mark is never among them. It points into a photograph, which has no
    parts and never gets rebuilt, so its pixel is the whole answer (ADR 0018).
    """
    return [m for m in all_marks
            if m.get("pixel") and not m.get("anchor") and not m.get("ref")]


def fingerprint(blend):
    """Which build this is, as twelve hex characters — `""` when there is no
    build at all. The `.blend` is regenerated from zero on every `contour
    check` (rule 3), so its bytes are a fair stand-in for its geometry, and
    hashing them costs nothing and needs no Blender to check."""
    blend = Path(blend)
    return (hashlib.sha256(blend.read_bytes()).hexdigest()[:12]
            if blend.exists() else "")


def record(path, resolution, views, blend):
    """Leave beside the sheet what it would take to re-cast its rays: the
    tiles, their cameras, and the build they were drawn from."""
    Path(path).write_text(json.dumps(
        {"resolution": resolution, "build": fingerprint(blend), "views": views},
        indent=2) + "\n", encoding="utf-8")


def load(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def stale(sheet, blend):
    """None when the sheet still matches the build on disk, otherwise the
    sentence to refuse with.

    Marking a sheet, rebuilding, then resolving would cast every ray into a
    scene the user never looked at. The pins would land, and look deliberate,
    and be wrong. Resolution stops here instead.
    """
    now = fingerprint(blend)
    if sheet["build"] == now:
        return None
    return (f"the build moved on since this sheet was drawn "
            f"({sheet['build'] or 'no build'} -> {now or 'no build'}): "
            f"run contour render, then mark again")


def orphan(path, part_names):
    """Say, for every anchored mark, whether its part is still in the build.
    Returns the ids now orphaned.

    The flag is what the last build found, not a scar: a part that comes back
    takes its pins back with it.

    Deleting a part does not answer the question that was asked about it, so
    the pin is said to be homeless rather than re-projected against whatever
    happens to be nearest — which is the same mistake nearest-centroid makes,
    one build later.
    """
    kept = marks.load(path)
    gone, before = [], json.dumps(kept)
    for mark in kept:
        if mark.get("ref"):
            continue          # no build of ours can orphan a mark on a reference
        part = (mark.get("anchor") or {}).get("part")
        if not part:
            continue
        if part in part_names:
            mark.pop("orphaned", None)   # a rename undone, a part back in build.py
        else:
            mark["orphaned"] = True
            gone.append(mark["id"])
    if json.dumps(kept) != before:
        marks.save(path, kept)
    return gone


def _edge(at, towards, away, size):
    """One corner of the badge box: beside the pin on the side it was pushed
    to, centred on it along the axis it was not pushed along."""
    if towards > 0:
        return int(at + away)
    if towards < 0:
        return int(at - away) - size
    return int(at) - size // 2


def _overlaps(box, taken):
    x, y, w, h = box
    return any(x < bx + bw and bx < x + w and y < by + bh and by < y + h
               for bx, by, bw, bh in taken)


def badge_spot(clear, x, y, w, h, bounds, step=5, rings=40, taken=()):
    """Where to put a `w` x `h` badge for a pin at `(x, y)`, or None.

    The pin is on a part — that is the whole point of it — so its badge can
    never be drawn where it points. It spirals outwards from the pin until it
    finds somewhere `clear` says is still background and that fits inside the
    tile, and gives up rather than paint over the model: a missing badge is a
    nuisance, a badge over the geometry destroys the thing the sheet is for.
    """
    W, H = bounds
    for ring in range(rings):
        for dx, dy in ((0, -1), (1, -1), (1, 0), (1, 1),
                       (0, 1), (-1, 1), (-1, 0), (-1, -1)):
            bx = _edge(x, dx, ring * step, w)
            by = _edge(y, dy, ring * step, h)
            bx, by = max(0, min(bx, W - w)), max(0, min(by, H - h))
            if clear(bx, by, w, h) and not _overlaps((bx, by, w, h), taken):
                return bx, by
    return None


def nearest(points):
    """The point nearest the middle of them all — and one of them.

    Where an agent's badge goes, once the mask has said which pixels of a view
    belong to the part it named. The obvious answer, the mean, is not always
    one of the points: beaky's arm is an L, and the middle of its pixels falls
    in the hole beside the torso, on the background. Taking the nearest real
    pixel to that mean puts the badge on the part whatever shape the part is.

    Two answers were tried and rejected before this one, and both failed on the
    same arm: the part's origin, which `build.py` may leave anywhere, and the
    centre of its bounding box.

    Kept here, out of Blender, so the claim is testable without a scene — the
    toolkit's own fixture cannot make it, having no part that is not convex.
    """
    mx = sum(p[0] for p in points) / len(points)
    my = sum(p[1] for p in points) / len(points)
    return min(points, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2)


def place(matrix, local):
    """Where a pin is now: the part's world matrix applied to the point the
    ray stored, as 16 row-major floats and three.

    This is the whole reason an anchor is local. The part may be moved,
    turned or resized between builds, and each of those is just this matrix
    changing; the pin is carried along by it without being touched. Kept
    here, out of Blender, so the claim is testable without a scene.
    """
    x, y, z = local
    return tuple(matrix[r * 4] * x + matrix[r * 4 + 1] * y
                 + matrix[r * 4 + 2] * z + matrix[r * 4 + 3] for r in range(3))
