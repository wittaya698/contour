"""A clip as one picture: what is decided before anything is drawn (ADR 0023).

Six frames from the side in one row, six from the front in the row below, on
the sheet's grid, one image labelled with the build it came from — the cost of
one sheet for a whole cycle. Which frames, at what scale and of which clip is
arithmetic on the spec and the measurement, so it lives here, stdlib only; the
drawing is `lib/cmd_filmstrip.py`.

Rendered at a checkpoint and never on a build (ADR 0005): the clip's numbers
are checked every build, and the filmstrip is for what numbers miss.
"""

from . import store, views

RECORD = "filmstrip.json"
"""Which build the filmstrip in `out/` is of, beside it. The build is drawn into
the picture's own pixels, which nothing below Blender can read, so the launcher
writes it down as a filmstrip succeeds (ADR 0024, decision 3)."""


def record(out, blend):
    """Say which build the filmstrip just drawn is of, in the shape `views.json`
    says it, so the panel's one comparison answers for both pictures."""
    out.mkdir(parents=True, exist_ok=True)
    store.save(out / RECORD, {"build": views.fingerprint(blend)})


COLUMNS = 6
TILE = (1024 // COLUMNS, 512)
"""One frame's tile in pixels, wide by tall: a sixth of the image across, half
of it down. Its camera's scale spans the tall side, as a sheet tile's does."""


def frames(n, loop):
    """The six frames of an `n`-frame clip, evenly through it, from 0.

    A loop's frame `n` is its frame 0 again, so a loop is cut into six and its
    last frame is never drawn; a clip that does not loop runs 0..n with both
    ends, because where it stops is half of what it is.
    """
    parts = COLUMNS if loop else COLUMNS - 1
    return [round(i * n / parts) for i in range(COLUMNS)]


def scale(lo, hi):
    """The metres every tile spans top to bottom, given the corners the whole
    clip sweeps through.

    The sheet's scale, so a part reads the same size on both, unless the
    widest view would not fit a tile a third as wide as a sheet's; then only
    as much further out as it takes, with the sheet's margin. Never a scale per
    frame or per row: one scale is what lets the eye compare the twelve.
    """
    w, h = TILE
    widest = max(hi[0] - lo[0], hi[1] - lo[1])
    return max(views.sheet_scale(lo, hi), 1.12 * widest * h / w)


def clip(spec, asked):
    """`(name, "")` for the clip to draw, or `(None, why)`.

    Nobody need name the clip of a spec that has one; a spec with several is
    asked which rather than having one drawn at random, and a name it does not
    have is answered with the names it does.
    """
    have = sorted(spec.get("clips") or {})
    if not have:
        return None, "no clips in the spec: nothing moves to draw"
    if asked is None:
        if len(have) > 1:
            return None, f"which clip? the spec has {', '.join(have)}"
        return have[0], ""
    if asked not in have:
        return None, f"no clip {asked} in the spec: it has {', '.join(have)}"
    return asked, ""
