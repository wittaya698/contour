"""The sheet's four camera frames, and the build they were drawn from
(ADR 0018).

`contour render` leaves a `views.json` beside the sheet — the tiles, the
cameras that drew them, and a fingerprint of the build. That record is what
makes a pixel answerable later: a mark is born carrying one, and one Blender
run per canvas session casts a ray through it and writes back the surface
point in the hit part's own coordinates. Move the part and the **pin** moves
with it, which is what `place` is for.

Everything here is stdlib and knows nothing about Blender: the ray is cast in
`lib/cmd_resolve.py`, which is the only part that needs a scene. It knows
nothing about the mark record either — writing back what the rays found, and
orphaning a pin whose part went, are transitions the record owns, in
`lib/marks.py` (slice 18). Where a **badge** may be drawn is `lib/badges.py`
(slice 20); this module says where things are, not what may cover them.
"""
import hashlib
from pathlib import Path

from . import store


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


def fingerprint(blend):
    """Which build this is, as twelve hex characters — `""` when there is no
    build at all. The `.blend` is regenerated from zero on every `contour
    check` (rule 3), so its bytes are a fair stand-in for its geometry, and
    hashing them costs nothing and needs no Blender to check.

    It lives beside the sheet's record because that is what the sheet's header
    holds, and everyone else asking *which build is this* — a mark being
    stamped addressed, a veto being promoted — is asking the sheet's question
    and must get the sheet's answer, or the two numbers would drift.
    """
    blend = Path(blend)
    return (hashlib.sha256(blend.read_bytes()).hexdigest()[:12]
            if blend.exists() else "")


def record(path, resolution, views, blend):
    """Leave beside the sheet what it would take to re-cast its rays: the
    tiles, their cameras, and the build they were drawn from."""
    store.save(path, {"resolution": resolution, "build": fingerprint(blend),
                      "views": views})


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


def place(matrix, local):
    """Where a pin is now: the part's world matrix applied to the point the
    ray stored, as 16 row-major floats and three.

    This is the whole reason a pin is local. The part may be moved, turned or
    resized between builds, and each of those is just this matrix changing;
    the pin is carried along by it without being touched. Kept here, out of
    Blender, so the claim is testable without a scene.
    """
    x, y, z = local
    return tuple(matrix[r * 4] * x + matrix[r * 4 + 1] * y
                 + matrix[r * 4 + 2] * z + matrix[r * 4 + 3] for r in range(3))
