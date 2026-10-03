"""./contour measure <ref> [queries]: real pixel geometry from a reference image.

ADR 0017. `contour api` exists because a recalled signature is a guess; this
exists because a recalled pixel count is a guess for the same reason. The agent
supplies semantics -- which blob is a hand, which way the face points -- and
this supplies arithmetic.

It is an instrument the agent aims, not a segmenter. The references show why:
their toon outlines are not uniform (head, neck and torso carry none), so colour
gives material regions, not parts, and nothing at all separates torso from leg.
A scanline across the legs still finds their two centres without needing to know
what a leg is.

Rows are indexed from the bottom of the image, so a height reads the way the
model frame does: millimetres above the ground.

    --span ID          read the distance between the two ends of one span mark
                       and pin the answer back on the same reference (ADR 0018).
                       Needs no <ref>: the mark names the picture it is on
    --scanline V --runs A,B --between centres|gap|extent "what it is"
                       draw an agent span between two runs of one scanline, by
                       their numbers in its report, and pin the answer back
                       (ADR 0022). Its ends are placed on what was measured;
                       there is no spelling of this that takes a pixel
    --silhouette|--region HEX --extent across|up "what it is"
                       draw an agent span across or up that extent, on the
                       edges this reports for it, and pin the answer back
    --again ID         ask a snapped span's stored question again, and say
                       whether it still places the same ends. Writes nothing
    --anchor MM        the silhouette's height is MM; everything reports in mm
    --silhouette       bounding box of everything that is not background
    --region HEX       bounding box + centroid of one palette colour
    --scanline V[,V]   runs across the figure at one or more heights
    --of HEX           restrict a scanline to one colour
    --profile HEX      half-width and centre per band, up a colour's own extent
    --bands N          how many bands a profile reports (default 12)
    --tol F            chromaticity match tolerance (default 0.05)
    --bg-tol F         how far from the sampled paper colour counts as figure
                       (default 0.10; raise it when the paper is not flat)
    --min-run PX       ignore runs narrower than this (default 3; kills antialias
                       specks, which otherwise read as parts that are not there)
"""
from pathlib import Path

import numpy as np

import bpy

from . import marks, space, span

BG_TOL = 0.10     # distance from the sampled background colour
DARK = 0.22       # below this mean brightness a pixel is toon outline, not colour


def load(path):
    """(h, w, 3) float RGB, row 0 at the BOTTOM, in whatever the file stores.

    Colorspace is forced to Raw: the default sRGB transform would hand back
    linear values, and the palette the spec quotes is sRGB hex.
    """
    img = bpy.data.images.load(str(path))
    try:
        img.colorspace_settings.name = "Raw"
    except Exception:
        pass
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    return buf.reshape(h, w, 4)[..., :3]


def hex_rgb(s):
    s = s.lstrip("#")
    return np.array([int(s[i:i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)


def chroma(a):
    """Direction in RGB, brightness divided out. Diffuse shading scales all three
    channels together, so a lit and a shadowed patch of one material land in the
    same place here and an exact-match test would miss half the sphere."""
    return a / np.maximum(a.sum(-1, keepdims=True), 1e-6)


def background(px):
    """The paper. Sampled from the border, which the figure does not touch."""
    edge = np.concatenate([px[0], px[-1], px[:, 0], px[:, -1]])
    return np.median(edge, axis=0)


def masks(px, bg_tol):
    bg = background(px)
    fg = np.linalg.norm(px - bg, axis=-1) > bg_tol
    return bg, fg


def colour_mask(px, fg, hexval, tol):
    """Pixels of one material: foreground, bright enough not to be an outline,
    and pointing the same way in RGB as the target."""
    want = chroma(hex_rgb(hexval)[None, None, :])[0, 0]
    d = np.linalg.norm(chroma(px) - want, axis=-1)
    return fg & (d < tol) & (px.mean(-1) > DARK)


def bbox(mask, min_px=3):
    """Extent of `mask`, ignoring rows and columns holding fewer than `min_px`.

    A plain min/max bounding box is decided by its single most extreme pixel, so
    on a JPEG a few compression specks move it by hundreds of millimetres --
    measured on refs/side.jpg, where 0.1% of the pixels swung the box 700 mm and
    the depth read 1300 instead of 597. Requiring a few pixels in a line costs
    at most a pixel of true extent and removes that entirely.
    """
    cols = np.nonzero(mask.sum(0) >= min_px)[0]
    rows = np.nonzero(mask.sum(1) >= min_px)[0]
    if len(cols) == 0 or len(rows) == 0:
        return None
    return int(cols[0]), int(cols[-1]), int(rows[0]), int(rows[-1])


def runs(row):
    """Contiguous True spans in a 1-D bool row -> [(x0, x1), ...]."""
    idx = np.nonzero(np.diff(np.concatenate(([0], row.view(np.int8), [0]))))[0]
    return list(zip(idx[0::2], idx[1::2] - 1))


def scan(px, fg, S, v, of, tol, minrun):
    """One scanline: the image row a height crosses, and the runs on it, or
    None for the row when it falls outside the image. The runs are numbered
    from 1 in every report, which is how a span picks them."""
    m = colour_mask(px, fg, of, tol) if of else fg
    row = S.row_for(v)
    if not (0 <= row < px.shape[0]):
        return row, None
    return row, [(int(a), int(b)) for a, b in runs(m[row]) if b - a + 1 >= minrun]


SPAN_FLAGS = ("--scanline", "--of", "--runs", "--between", "--anchor", "--tol",
              "--bg-tol", "--min-run")
"""Every flag the span form takes, each with a value. Anything else is refused,
not ignored: an end given as a pixel would otherwise be dropped silently, and
the agent would believe it had placed one (ADR 0022, decision 2)."""

EXTENT_FLAGS = ("--region", "--extent", "--anchor", "--tol", "--bg-tol")
"""The same, for a span across an extent (issue 41); `--silhouette` is its one
flag with no value."""


def span_form(rest, takes, bare=(), e_g=""):
    """`(text, refusal)` for a span form's arguments: the one line it is asked
    to carry, or why the command as typed is not one. `takes` are its flags
    with a value, `bare` those without; any other flag is refused."""
    text, i = [], 0
    while i < len(rest):
        if rest[i].startswith("--"):
            if rest[i] not in takes + bare:
                return None, (f"FAIL measure  {rest[i]} is not part of a span: the "
                              f"agent names what was measured, and code places "
                              f"the ends, so no end is ever given as a pixel")
            i += 1 if rest[i] in bare else 2
            continue
        text.append(rest[i])
        i += 1
    if len(text) != 1:
        return None, f"FAIL measure  say in one line what the distance is, e.g. {e_g}"
    return text[0], None


def scanline_form(rest):
    """`(text, refusal)` for a span between two runs of one scanline."""
    text, refused = span_form(rest, SPAN_FLAGS,
                              e_g='--runs 1,2 --between centres "the legs, centre to centre"')
    if refused:
        return None, refused
    if "," in flag(rest, "--scanline", str, ""):
        return None, "FAIL measure  a span is drawn on one scanline: give one height"
    if flag(rest, "--between") not in span.BETWEEN:
        return None, f"FAIL measure  --between takes one of: {', '.join(span.BETWEEN)}"
    return text, None


def extent_form(rest):
    """`(text, refusal)` for a span across the silhouette or one colour."""
    text, refused = span_form(rest, EXTENT_FLAGS, bare=("--silhouette",),
                              e_g='--silhouette --extent across "the body, side to side"')
    if refused:
        return None, refused
    if ("--silhouette" in rest) == ("--region" in rest):
        return None, ("FAIL measure  a span runs over one extent: give --silhouette "
                      "or --region HEX, and not both")
    if flag(rest, "--extent") not in span.EXTENTS:
        return None, f"FAIL measure  --extent takes one of: {', '.join(span.EXTENTS)}"
    return text, None


def extent(px, fg, of, tol):
    """The extent a report prints for the silhouette (`of` None) or one
    colour: the box a span across it snaps to, or None for no such colour."""
    return bbox(colour_mask(px, fg, of, tol) if of else fg)


class Scale:
    """mm per pixel, from the one real dimension the user stated (ADR 0016)."""

    def __init__(self, anchor_mm, sil):
        self.sil = sil
        self.k = None if anchor_mm is None else anchor_mm / (sil[3] - sil[2] + 1)

    def mm(self, px):
        return None if self.k is None else px * self.k

    def row_for(self, v):
        """A query height -> an image row. mm above the silhouette base when an
        anchor is set, else a fraction of the silhouette's height."""
        x0, x1, y0, y1 = self.sil
        return int(round(y0 + (v / self.k if self.k else v * (y1 - y0))))

    def fmt(self, px, unit=True):
        if self.k is None:
            return f"{px:.0f}px"
        return f"{px * self.k:.0f}mm" if unit else f"{px * self.k:.0f}"


def flag(args, name, cast=str, default=None):
    if name not in args:
        return default
    i = args.index(name)
    if i + 1 >= len(args):
        raise SystemExit(f"{name} needs a value")
    return cast(args[i + 1])


def run(args):
    named = None if not args or args[0].startswith("--") else args[0]
    rest = args if named is None else args[1:]
    # The space this was typed in, and nothing to fall back to: `PROJECT or
    # ROOT` used to answer here, which let the toolkit's own directory pass for
    # a model space.
    P = space.parse([])
    store = P.marks

    # A span is already pinned to a reference, so it names its own: asking for
    # the picture again means saying it twice, in two spellings -- the path
    # this resolves and the bare name a mark records -- and getting the second
    # one right. Every other query still has to be aimed by hand.
    again = flag(rest, "--again")
    if again:
        return asked_again(P, store, again)
    if "--runs" in rest:
        if "--scanline" not in rest:
            return {"ok": False, "lines": [
                "FAIL measure  --runs picks from a scanline: give --scanline too"]}
        text, refused = scanline_form(rest)
        if refused:
            return {"ok": False, "lines": [refused]}
        rest = [a for a in rest if a != text]
    elif "--extent" in rest:
        text, refused = extent_form(rest)
        if refused:
            return {"ok": False, "lines": [refused]}
        rest = [a for a in rest if a != text]
    asked = flag(rest, "--span")
    if asked:
        aimed = span.aim(store, asked, named)
        if not aimed["ok"]:
            return aimed
        # The mark's own name, never the one on the command line: a reference
        # lives in `refs/` by its bare filename, and a name that got this far
        # has already been checked against the mark rather than resolved.
        name = f"refs/{aimed['ref']}"
    elif named is None:
        return {"ok": False, "lines": ["FAIL measure: name a reference image first",
                                       "  e.g. contour measure refs/front.jpg --anchor 1700 --silhouette"]}
    else:
        name = named
    path = next((p for p in (P.root / name, P.toolkit / name) if p.exists()), None)
    if path is None:
        return {"ok": False, "lines": [f"FAIL measure: no such reference {name}"]}

    tol = flag(rest, "--tol", float, 0.05)
    bg_tol = flag(rest, "--bg-tol", float, BG_TOL)
    # A span reports in millimetres or not at all, so it falls back to the one
    # real dimension the space has already stated rather than making the user
    # retype it -- and to nothing else. Every other query keeps its old
    # behaviour of measuring in pixels until an anchor is given.
    anchor = flag(rest, "--anchor", float)
    if (asked or "--runs" in rest or "--extent" in rest) and anchor is None:
        anchor = span.anchor_mm(P.spec)
    px = load(path)
    h, w = px.shape[:2]
    bg, fg = masks(px, bg_tol)
    sil = bbox(fg)
    if sil is None:
        return {"ok": False, "lines": [f"FAIL measure: {name} is entirely background"]}
    S = Scale(anchor, sil)
    x0, x1, y0, y1 = sil
    lines = [f"{name} {w}x{h}px  bg #{''.join('%02x' % int(c * 255) for c in bg)}"
             + f"  fg {100 * fg.mean():.1f}%"
             + (f"  scale {S.k:.4f}mm/px" if S.k else "  no anchor: px only")]

    if asked:
        # The scale is the only thing the image is asked for here: where the
        # span runs was decided by the user, on the picture, with a mouse.
        got = span.measure(store, asked, S.k)
        return {**got, "lines": lines + got["lines"]}

    if "--runs" in rest:
        q = {"scanline": flag(rest, "--scanline", float),
             "of": flag(rest, "--of"),
             "runs": [int(n) for n in flag(rest, "--runs").split(",")],
             "between": flag(rest, "--between"), "anchor": anchor,
             "tol": tol, "bg_tol": bg_tol, "min_run": flag(rest, "--min-run", int, 3)}
        row, rr = scan(px, fg, S, q["scanline"], q["of"], tol, q["min_run"])
        if rr is None:
            return {"ok": False, "lines": lines + [
                f"FAIL measure  scanline {q['scanline']:g} is row {row}, outside the image"]}
        got = span.draw(store, Path(name).name, q, rr, row=row, height=h, k=S.k, text=text)
        return {**got, "lines": lines + got["lines"]}

    if "--extent" in rest:
        q = {"extent": flag(rest, "--extent"), "of": flag(rest, "--region"),
             "anchor": anchor, "tol": tol, "bg_tol": bg_tol}
        got = span.draw_extent(store, Path(name).name, q,
                               extent(px, fg, q["of"], tol), height=h, k=S.k, text=text)
        return {**got, "lines": lines + got["lines"]}

    if "--silhouette" in rest or not any(f in rest for f in ("--region", "--scanline", "--profile")):
        lines.append(f"  silhouette  w {S.fmt(x1 - x0 + 1)}  h {S.fmt(y1 - y0 + 1)}"
                     f"  [x {x0}..{x1}  y {y0}..{y1} px]")

    hexv = flag(rest, "--region")
    if hexv:
        m = colour_mask(px, fg, hexv, tol)
        b = bbox(m)
        if b is None:
            lines.append(f"  region {hexv}  NO MATCH (try --tol above {tol})")
        else:
            ys, xs = np.nonzero(m)
            cx, cy = xs.mean(), ys.mean()
            lines.append(f"  region {hexv}  w {S.fmt(b[1] - b[0] + 1)}  h {S.fmt(b[3] - b[2] + 1)}"
                         f"  centroid x {S.fmt(cx - (x0 + x1) / 2)} of centre,"
                         f" y {S.fmt(cy - y0)} up  [{m.sum()}px]")

    vs = flag(rest, "--scanline")
    if vs is not None:
        of = flag(rest, "--of")
        minrun = flag(rest, "--min-run", int, 3)
        mid = (x0 + x1) / 2
        for v in [float(t) for t in vs.split(",")]:
            row, rr = scan(px, fg, S, v, of, tol, minrun)
            if rr is None:
                lines.append(f"  scanline {v:g}  SKIP row {row} outside the image")
                continue
            tag = f"{of} " if of else ""
            lines.append(f"  scanline {v:g} {tag}row {row}  {len(rr)} run(s)")
            for n, (a, b) in enumerate(rr, 1):
                lines.append(f"    run {n}  x {a}..{b}px  width {S.fmt(b - a + 1)}"
                             f"  centre {S.fmt((a + b) / 2 - mid)} from silhouette centre")
            if len(rr) == 2:
                c0, c1 = (rr[0][0] + rr[0][1]) / 2, (rr[1][0] + rr[1][1]) / 2
                lines.append(f"    centre-to-centre {S.fmt(c1 - c0)}"
                             f"   inner gap {S.fmt(rr[1][0] - rr[0][1] - 1)}")

    hexv = flag(rest, "--profile")
    if hexv:
        n = flag(rest, "--bands", int, 12)
        m = colour_mask(px, fg, hexv, tol)
        b = bbox(m)
        if b is None:
            lines.append(f"  profile {hexv}  NO MATCH")
        else:
            lines.append(f"  profile {hexv}  {n} bands up its own extent"
                         f" (y {b[2]}..{b[3]}px)")
            for i in range(n):
                row = int(round(b[2] + (b[3] - b[2]) * i / (n - 1)))
                rr = runs(m[row])
                if not rr:
                    continue
                a, z = rr[0][0], rr[-1][1]
                lines.append(f"    h {S.fmt(row - b[2], False):>6}  half-w"
                             f" {S.fmt((z - a + 1) / 2):>7}  centre"
                             f" {S.fmt((a + z) / 2 - (x0 + x1) / 2):>7}")
    return {"ok": True, "lines": lines}


def asked_again(P, store, mark_id):
    """`--again ID`: the stored question, asked of the reference as it is now,
    under the anchor and tolerances it was first asked with, so that the same
    picture can only place the same ends."""
    q = span.asked(store, mark_id)
    if not q["ok"]:
        return q
    name, q = f"refs/{q['ref']}", q["question"]
    path = P.root / name
    if not path.exists():
        return {"ok": False, "lines": [f"FAIL measure  {mark_id}: no such reference {name}"]}
    px = load(path)
    _, fg = masks(px, q["bg_tol"])
    sil = bbox(fg)
    if sil is None:
        return {"ok": False, "lines": [f"FAIL measure  {name} is entirely background"]}
    if "extent" in q:
        return span.again_extent(store, mark_id, extent(px, fg, q["of"], q["tol"]),
                                 height=px.shape[0])
    row, rr = scan(px, fg, Scale(q["anchor"], sil), q["scanline"], q["of"],
                   q["tol"], q["min_run"])
    return span.again(store, mark_id, rr or [], row=row, height=px.shape[0])
