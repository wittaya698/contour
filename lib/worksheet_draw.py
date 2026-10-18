"""The worksheet's pixels: references laid out, spans drawn and labelled on
them (ADR 0022, decision 8).

numpy and no bpy, so the picture is testable without a scene wherever numpy is
installed. It is in the Blender half of `lib/` all the same: numpy comes with
Blender and not with a bare clone, and the launcher has to run on one.
`lib/worksheet.py` says what each span is; this says where it goes.
"""
import numpy as np

from .worksheet import directions, spans

TILE = 720
"""How tall each reference is drawn, in pixels. Two or three side by side come
to about a sheet's area, which is what the worksheet was to cost."""

ROW = 2160
"""How wide a row of references may get before the next one starts below."""

GAP = 12
CAPTION = 28        # the band above each reference that names it

AGENT = (0.18, 0.44, 0.85)
USER = (0.85, 0.27, 0.18)
REJECTED = (0.55, 0.55, 0.55)
"""The canvas's colours for whose a span is, and grey for one whose number is
not to be used."""

INK = (0.1, 0.1, 0.12)
LINE = 3            # px, at the worksheet's own scale
DASH = 12           # a by-eye span's line is drawn this long, then left out as long


def compose(pictures, all_marks):
    """`(image, placed)`: every reference with a span, laid out, each span
    drawn and labelled on it.

    `pictures` maps a reference's name to its pixels, `(h, w, 3)` floats with
    row 0 at the top. `image` is the same; `placed` maps each reference on it
    to `(x, y, k)`, its corner and its scale. A reference with no span is not
    drawn, and a span on a reference with no picture is left to the caller to
    say.
    """
    drawn = [s for s in spans(all_marks) if s["ref"] in pictures]
    aimed = [d for d in directions(all_marks) if d["ref"] in pictures]
    refs = sorted({s["ref"] for s in drawn + aimed})
    placed, x, y, row_w = {}, GAP, GAP, 0
    for ref in refs:
        h, w = pictures[ref].shape[:2]
        k = TILE / h
        if x > GAP and x + w * k > ROW:
            x, y = GAP, y + CAPTION + TILE + GAP
        placed[ref] = (x, y + CAPTION, k)
        x += int(round(w * k)) + GAP
        row_w = max(row_w, x)
    image = np.ones((y + CAPTION + TILE + GAP, max(row_w, 2 * GAP), 3), dtype=np.float32)
    for ref in refs:
        x0, y0, k = placed[ref]
        pic = pictures[ref][..., :3]
        h, w = pic.shape[:2]
        th, tw = TILE, int(round(w * k))
        image[y0:y0 + th, x0:x0 + tw] = pic[(np.arange(th) * h // th)[:, None],
                                            (np.arange(tw) * w // tw)[None, :]]
        text(image, x0, y0 - CAPTION + 6, ref.lower())
    ends = []
    for s in drawn:
        x0, y0, k = placed[s["ref"]]
        ends.append(((x0 + s["pixel"][0] * k, y0 + s["pixel"][1] * k),
                     (x0 + s["to"][0] * k, y0 + s["to"][1] * k)))
    # A direction first, under the spans: thin, and run to the edges of its
    # reference, so the eye can follow its lines to where they meet.
    for d in aimed:
        x0, y0, k = placed[d["ref"]]
        h, w = pictures[d["ref"]].shape[:2]
        box = (x0, y0, x0 + w * k - 1, y0 + h * k - 1)
        for (p, q), eyed in zip(d["lines"], d["by_eye"]):
            a, b = (x0 + p[0] * k, y0 + p[1] * k), (x0 + q[0] * k, y0 + q[1] * k)
            far = _across(a, b, box)
            if far:
                _line(image, *far, _colour(d), width=1)
            _line(image, a, b, _colour(d), dashed=eyed)
    # Every line before any label, and each line's box an obstacle to them all:
    # a label is moved off any span, not only off the labels drawn before it.
    taken = [_around(a, b) for a, b in ends]
    for s, (a, b) in zip(drawn, ends):
        _line(image, a, b, _colour(s), dashed=s["by_eye"])
        for end in (a, b):
            _square(image, end, _colour(s))
        taken.append(_tagged(image, s["id"], min(a, b)))
    for s, (a, b) in zip(drawn, ends):
        _labelled(image, s["label"], a, b, _colour(s), taken)
    for d in aimed:
        x0, y0, k = placed[d["ref"]]
        p, q = d["lines"][0]
        _labelled(image, d["label"], (x0 + p[0] * k, y0 + p[1] * k),
                  (x0 + q[0] * k, y0 + q[1] * k), _colour(d), taken)
    return image, placed


def _across(a, b, box):
    """The line through `a` and `b` where it crosses `box`, `(x0, y0, x1,
    y1)`: its two ends on the box's edges, or None when it misses the box."""
    lo, hi = -1e9, 1e9
    for start, step, low, high in ((a[0], b[0] - a[0], box[0], box[2]),
                                   (a[1], b[1] - a[1], box[1], box[3])):
        if step == 0:
            if not low <= start <= high:
                return None
            continue
        t0, t1 = sorted(((low - start) / step, (high - start) / step))
        lo, hi = max(lo, t0), min(hi, t1)
    if lo > hi:
        return None
    return tuple((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for t in (lo, hi))


def _tagged(image, mark_id, end):
    """The span's id, just left of its left end, where no label can move it
    away from its line. Returns the box it took."""
    tw, th = len(mark_id) * 6 * SCALE + 4, 7 * SCALE + 4
    x, y = int(end[0]) - 8 - tw, int(end[1]) - th // 2
    h, w = image.shape[:2]
    x, y = max(0, min(x, w - tw)), max(0, min(y, h - th))
    image[y:y + th, x:x + tw] = 1.0
    text(image, x + 2, y + 2, mark_id.lower())
    return (x, y, tw, th)


def _around(a, b, pad=6):
    """The box a span's line and its end squares cover, as `(x, y, w, h)`."""
    x, y = min(a[0], b[0]) - pad, min(a[1], b[1]) - pad
    return (x, y, abs(b[0] - a[0]) + 2 * pad, abs(b[1] - a[1]) + 2 * pad)


def _colour(s):
    if s["rejected"]:
        return REJECTED
    return AGENT if s["agent"] else USER


def _line(image, a, b, colour, dashed=False, width=LINE):
    n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) * 2 + 2
    t = np.linspace(0.0, 1.0, n)
    if dashed:
        along = t * np.hypot(b[0] - a[0], b[1] - a[1])
        t = t[(along // DASH) % 2 == 0]
    xs, ys = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
    h, w = image.shape[:2]
    for ox in range(-(width // 2), width - width // 2):
        for oy in range(-(width // 2), width - width // 2):
            ix = np.round(xs).astype(int) + ox
            iy = np.round(ys).astype(int) + oy
            ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
            image[iy[ok], ix[ok]] = colour


def _square(image, at, colour, r=4):
    h, w = image.shape[:2]
    x, y = int(round(at[0])), int(round(at[1]))
    image[max(0, y - r):min(h, y + r + 1), max(0, x - r):min(w, x + r + 1)] = colour


SCALE = 2           # glyph scale: 14 px tall, as the sheet's badges are


def _labelled(image, lines, a, b, colour, taken):
    """The label, in a white box above the span and right of its middle,
    moved up past anything in `taken` -- every span's line, and the labels
    already placed -- rather than over it; below the span when there is no
    room above."""
    lh = 7 * SCALE + 4
    bw = max(len(s) for s in lines) * 6 * SCALE + 8
    bh = lh * len(lines) + 4
    h, w = image.shape[:2]
    x = int(min(max((a[0] + b[0]) / 2 + 8, 0), w - bw))

    def clear(y):
        return not any(x < bx + bbw and bx < x + bw and y < by + bbh and by < y + bh
                       for bx, by, bbw, bbh in taken)
    y = int(min(a[1], b[1])) - 8 - bh
    while y >= 0 and not clear(y):
        y -= 4
    if y < 0:
        y = int(max(a[1], b[1])) + 8
        while y + bh <= h and not clear(y):
            y += 4
    y = max(0, min(y, h - bh))
    taken.append((x, y, bw, bh))
    image[y:y + bh, x:x + bw] = 1.0
    image[y:y + bh, x:x + 2] = colour
    for i, s in enumerate(lines):
        text(image, x + 6, y + 4 + i * lh, s.lower())


def text(image, x, y, s, colour=INK):
    """Paint `s` with its top-left at `(x, y)`, row 0 at the top. A character
    the font lacks is drawn as a box rather than dropped."""
    h, w = image.shape[:2]
    for ch in s:
        rows = FONT.get(ch, FONT["?"]).split("|")
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                if v == "#":
                    y0, x0 = y + r * SCALE, x + c * SCALE
                    if 0 <= y0 < h - SCALE and 0 <= x0 < w - SCALE:
                        image[y0:y0 + SCALE, x0:x0 + SCALE] = colour
        x += 6 * SCALE


FONT = {
    "a": ".....|.....|.###.|....#|.####|#...#|.####", "b": "#....|#....|####.|#...#|#...#|#...#|####.",
    "c": ".....|.....|.###.|#....|#....|#...#|.###.", "d": "....#|....#|.####|#...#|#...#|#...#|.####",
    "e": ".....|.....|.###.|#...#|#####|#....|.###.", "f": "..##.|.#...|###..|.#...|.#...|.#...|.#...",
    "g": ".....|.####|#...#|#...#|.####|....#|.###.", "h": "#....|#....|####.|#...#|#...#|#...#|#...#",
    "i": "..#..|.....|.##..|..#..|..#..|..#..|.###.", "j": "...#.|.....|..##.|...#.|...#.|#..#.|.##..",
    "k": "#....|#....|#..#.|#.#..|##...|#.#..|#..#.", "l": ".##..|..#..|..#..|..#..|..#..|..#..|.###.",
    "m": ".....|.....|##.#.|#.#.#|#.#.#|#.#.#|#.#.#", "n": ".....|.....|####.|#...#|#...#|#...#|#...#",
    "o": ".....|.....|.###.|#...#|#...#|#...#|.###.", "p": ".....|.....|####.|#...#|####.|#....|#....",
    "q": ".....|.....|.####|#...#|.####|....#|....#", "r": ".....|.....|#.##.|##..#|#....|#....|#....",
    "s": ".....|.....|.####|#....|.###.|....#|####.", "t": ".#...|.#...|###..|.#...|.#...|.#..#|..##.",
    "u": ".....|.....|#...#|#...#|#...#|#..##|.##.#", "v": ".....|.....|#...#|#...#|#...#|.#.#.|..#..",
    "w": ".....|.....|#...#|#...#|#.#.#|#.#.#|.#.#.", "x": ".....|.....|#...#|.#.#.|..#..|.#.#.|#...#",
    "y": ".....|.....|#...#|#...#|.####|....#|.###.", "z": ".....|.....|#####|...#.|..#..|.#...|#####",
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.", "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####", "3": "####.|....#|....#|.###.|....#|....#|####.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.", "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": "..##.|.#...|#....|####.|#...#|#...#|.###.", "7": "#####|....#|...#.|..#..|.#...|.#...|.#...",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.", "9": ".###.|#...#|#...#|.####|....#|...#.|.##..",
    "±": "..#..|..#..|#####|..#..|..#..|.....|#####", ",": ".....|.....|.....|.....|.##..|..#..|.#...",
    ".": ".....|.....|.....|.....|.....|.##..|.##..", "-": ".....|.....|.....|#####|.....|.....|.....",
    "_": ".....|.....|.....|.....|.....|.....|#####", " ": ".....|.....|.....|.....|.....|.....|.....",
    "?": "#####|#...#|#...#|#...#|#...#|#...#|#####",
}
"""5x7 glyphs, lower case: every word a label or a reference's name needs.
Upper case is folded down by the caller, so a name is never a row of boxes."""
