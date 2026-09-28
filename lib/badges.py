"""Where a label may go, and where it may not (ADR 0018).

*The model is never covered by a remark about it.* A **badge** points at a
**pin**, and a pin is on a part by definition, so the one place a badge can
never be drawn is where it points. This module is that rule and the two
searches that keep it: `badge_spot` pushes a badge off into the background and
gives up rather than paint over geometry, and `nearest` finds a point on a
named part for an agent's mark that has no pin at all.

Given a module of its own because it is the rule most easily broken in
passing: every other module here answers *where is this*, and only this one
answers *what may cover it*. Stdlib, and no Blender — the caller hands in a
`clear` predicate over the mask and a list of pixels, so both claims are
testable without a scene. The toolkit's own fixture cannot make the second
one, having no part that is not convex.
"""


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
    """
    mx = sum(p[0] for p in points) / len(points)
    my = sum(p[1] for p in points) / len(points)
    return min(points, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2)
