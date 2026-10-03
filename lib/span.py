"""A span: two pins on a reference, and the distance the user meant (ADR 0018).

A ref mark says *here is what I meant*. Two ends on one mark say *this
distance, right here* — which is the only way a picture can be asked about a
separation at all, because a scanline finds runs and cannot know which two of
them the question was about.

The arithmetic lives here, out of Blender, for the reason `views.place` does:
the image reading is what needs bpy, and the number that comes out of it is
what needs to be checkable without a scene.
"""
import math
from pathlib import Path

from . import agent, marks, miniyaml


def reading(a, b, k):
    """`{"px", "mm", "tol"}` — the line between two pixels, and what it is worth.

    The length, not the horizontal extent: two pins are rarely level, and a
    user pointing at what separates the legs clicks the outer edges wherever
    they actually are.

    `tol` is one pixel at each end, in millimetres. That is the finest thing
    the image can say, and saying it is the point: a bare `126 mm` off a
    1080px photograph reads as a precision the picture does not have.
    """
    px = math.dist(a, b)
    return {"px": px, "mm": px * k, "tol": 2 * k}


def line(got):
    """One reading, as a human reads it: the number, the bar, the evidence."""
    return (f"{got['mm']:.0f} mm \u00b1{got['tol']:.0f} mm"
            f"  ({got['px']:.0f} px at {got['mm'] / got['px']:.3f} mm/px)")


def anchor_mm(spec):
    """The one real dimension the space has stated, or None.

    `dimensions.height` and not a second number of its own: the user already
    gave the object's height, and a reference is a picture of that same
    object. A second anchor would be a second thing to keep in step, and the
    day the two disagreed nothing would say which was meant.

    None when there is no spec, or none of this in it. None is a refusal, not
    a default — a picture carries proportion and never scale (ADR 0017), and a
    guessed anchor is wrong in every millimetre it reports.
    """
    spec = Path(spec) if spec else None
    if not spec or not spec.exists():
        return None
    doc = miniyaml.load(spec) or {}
    height = (doc.get("dimensions") or {}).get("height") or {}
    value = height.get("value") if isinstance(height, dict) else height
    return float(value) if isinstance(value, (int, float)) else None


def marked(path, mark_id):
    """The mark on file with this id, or None."""
    return next((m for m in marks.load(path) if m.get("id") == mark_id), None)


def midpoint(a, b):
    """Where the answer is pinned: between the two pins that asked."""
    return [round((a[0] + b[0]) / 2), round((a[1] + b[1]) / 2)]


def aim(path, mark_id, named=None):
    """Which reference a span is asking about: the one it is pinned to.

    So `contour measure --span m9` takes no reference argument. The mark is
    already the one place that records which picture the two pins are on, and
    a second place to say it is a second place to say it wrong -- which is
    exactly how the first real drag on `beaky-solo` failed.
    """
    found = marked(path, mark_id)
    if found is None:
        return {"ok": False, "lines": [f"FAIL measure  no mark {mark_id} on file"]}
    ref = marks.reference(found)
    if not ref:
        return {"ok": False, "lines": [
            f"FAIL measure  {mark_id} is not on a reference: it is pinned to "
            f"the render sheet, which is a picture of the model and not of "
            f"the thing, so there is nothing here to measure against"]}
    if named and Path(named).name != ref:
        return {"ok": False, "lines": [
            f"FAIL measure  {mark_id} is on {ref}, not {named}: a span is "
            f"pinned to one reference, so name that one or name none"]}
    return {"ok": True, "ref": ref}


def measure(path, mark_id, k):
    """Read one span and pin the answer beside it. Returns a report.

    The answer is an agent mark, on the same reference, open like any other:
    a measurement is a finding the user may act on — it may well say the build
    is wrong — and not a receipt the toolkit files away. Only the user closes
    it (ADR 0018).
    """
    found = marked(path, mark_id)
    if found is None:
        return {"ok": False, "lines": [f"FAIL measure  no mark {mark_id} on file"]}
    if not (marks.span_end(found) and marks.reference(found)):
        return {"ok": False, "lines": [
            f"FAIL measure  {mark_id} is not a span: a span is a mark on a "
            f"reference with two ends, made by dragging on the canvas"]}
    if marks.pixel(found) == marks.span_end(found):
        return {"ok": False, "lines": [
            f"FAIL measure  {mark_id} has no length: both ends are the same "
            f"pixel, so there is no distance to read"]}
    if k is None:
        return {"ok": False, "lines": [
            "FAIL measure  no anchor: this space states no dimensions.height, "
            "so the picture gives proportion and not millimetres"]}
    got = reading(marks.pixel(found), marks.span_end(found), k)
    said = agent.write(path, f"span {mark_id}: {line(got)}",
                       ref=marks.reference(found),
                       pixel=midpoint(marks.pixel(found), marks.span_end(found)))
    return {"ok": True, "lines": [f"ok   measure {said['id']} "
                                  f"{marks.reference(found)}  "
                                  f"{marks.text(found)}  {line(got)}"]}


BETWEEN = ("centres", "gap", "extent")
"""The distances a span can ask for between two runs: centre to centre, the gap
between them, and the outer extent across them."""


def snap(runs, picked, between, row, height):
    """Two ends, placed on what a scanline measured (ADR 0022, decision 2).

    `runs` are the scanline's, as inclusive pixel columns; `picked` names two
    of them by their number in the scanline's report, counting from 1. The
    agent answers *which*, and this answers *where*: there is no argument here
    for a pixel, so no end can be one the agent chose.

    `row` counts from the bottom of the image, as every height in `contour
    measure` does; the ends come back counted from the top, as a mark's pixel
    is, so the canvas draws them where they were measured.
    """
    (a0, a1), (b0, b1) = (runs[n - 1] for n in picked)
    y = height - 1 - row
    x = {"centres": ((a0 + a1) / 2, (b0 + b1) / 2),
         # Pixel edges, half a pixel out from the last one in a run: a run's
         # columns are inclusive, so this is what its width already counts.
         "gap": (a1 + 0.5, b0 - 0.5),
         "extent": (a0 - 0.5, b1 + 0.5)}[between]
    return [x[0], y], [x[1], y]


EXTENTS = ("across", "up")
"""The two ways a span can run over an extent: side to side, or bottom to top."""


def edges(box, extent, height):
    """Two ends on the edges of an extent `contour measure` reported (ADR
    0022, decision 2; issue 41).

    `box` is `x0, x1, y0, y1` as `cmd_measure.bbox` gives it, rows counted
    from the bottom, specks already ignored — the extent the report prints,
    so a span reads the report's own number and never a second one. Across
    runs at the middle of its height, up through the middle of its width; the
    ends sit on pixel edges, half a pixel out, as `snap`'s gap and extent do.
    """
    x0, x1, y0, y1 = box
    if extent == "across":
        y = height - 1 - (y0 + y1) / 2
        return [x0 - 0.5, y], [x1 + 0.5, y]
    x = (x0 + x1) / 2
    return [x, height - 1 - y1 - 0.5], [x, height - 1 - y0 + 0.5]


def found_runs(runs):
    """A scanline's runs as its report numbers them, for a refusal to hand
    back: the agent picks from these, so these are what it is shown."""
    return ", ".join(f"run {n} x {a}..{b}px" for n, (a, b) in enumerate(runs, 1))


def draw(path, ref, question, runs, row, height, k, text):
    """An agent span, snapped to what a scanline found (ADR 0022, decisions 2
    and 4). Returns a report.

    `question` is what the agent asked, in full, and is stored with the span:
    it is the re-runnable basis ADR 0017 asked for. `runs` is what the
    scanline found asking it, and `k` the scale, or None with no anchor.
    """
    picked = question["runs"]
    if (len(picked) != 2 or len(set(picked)) != 2
            or not all(1 <= n <= len(runs) for n in picked)):
        return {"ok": False, "lines": [
            f"FAIL measure  pick two different runs of the {len(runs)} the "
            f"scanline found: {found_runs(runs) or 'none'}"]}
    a, b = snap(runs, picked, question["between"], row, height)
    return pinned(path, ref, question, (a, b), k, text)


def draw_extent(path, ref, question, box, height, k, text):
    """An agent span across an extent, snapped to its edges (issue 41).
    Returns a report.

    `box` is the extent the question found, or None when its colour is not in
    the picture at that tolerance: then there are no edges, and nothing is
    drawn. `question` names the extent and the colour, None for the
    silhouette, and is stored with the span as `draw`'s is.
    """
    if box is None:
        return {"ok": False, "lines": [
            f"FAIL measure  {question['of']} is not in {ref} at --tol "
            f"{question['tol']:g}: there is no extent to draw a span across, "
            f"so nothing was drawn"]}
    return pinned(path, ref, question, edges(box, question["extent"], height),
                  k, text)


def pinned(path, ref, question, ends, k, text):
    """A snapped span on file, and its answer pinned between its ends: the
    one record every query that places one makes."""
    a, b = ends
    return _drawn(path, {"ref": ref, "pixel": a, "to": b, "text": text,
                         "placed": "snapped", "question": question, "scale": k},
                  reads(a, b, k))


def by_eye(path, ref, ends, k, text):
    """An agent span with free ends, where nothing would snap (ADR 0022,
    decision 3; issue 44). Returns a report.

    There was no question, so none is stored and `--again` has nothing to ask.
    What it keeps instead is the fact: `placed: by eye`.
    """
    a, b = ends
    if list(a) == list(b):
        return {"ok": False, "lines": [
            "FAIL measure  a span needs two different ends: both are the same "
            "pixel, so there is no distance to read"]}
    return _drawn(path, {"ref": ref, "pixel": list(a), "to": list(b), "text": text,
                         "placed": "by eye", "scale": k},
                  f"{reads(a, b, k)}  {BY_EYE}")


BY_EYE = ("by eye: the bar covers the arithmetic between the ends, not the "
          "placing of them")
"""What a by-eye span's answer says beside its number. The bar is a pixel at
each end; left unsaid, it would read as covering where the agent put them."""


def _drawn(path, mark, answer):
    """An agent span on file, and its answer pinned between its ends. One
    record for every way one is placed, so nothing that reads a span needs to
    know which did."""
    drawn, said = marks.spanned(path, mark, answer, midpoint(mark["pixel"], mark["to"]))
    return {"ok": True, "lines": [f"ok   measure {drawn['id']} {mark['ref']}  "
                                  f"{mark['text']}  {answer}  (answer {said['id']})"]}


def reads(a, b, k):
    """What a span between these ends reads: millimetres at scale `k`, the
    mm per pixel it was drawn at, or pixels when there is none."""
    return line(reading(a, b, k)) if k else unscaled(a, b)


NO_ANCHOR = ("no anchor: this space states no dimensions.height, so the "
             "picture gives proportion and not millimetres")


def unscaled(a, b, why=NO_ANCHOR):
    """A span's answer with no scale: pixels, and why they are not mm. Where
    the ends landed is still an answer; a millimetre figure would be a guess
    at the scale (ADR 0016), so none is given."""
    return f"{math.dist(a, b):.0f} px \u00b12 px  ({why})"


def standing(path, mark_id):
    """Whether this span's number may go into a proposal, and as whose (ADR
    0022, decision 6). Writes nothing.

    `proposable` says it for code; the line says it for the agent, with the
    number beside it, so the reading that may be proposed and the reading
    proposed are the same one.
    """
    found = marked(path, mark_id)
    if found is None:
        return {"ok": False, "lines": [f"FAIL measure  no mark {mark_id} on file"]}
    if not (marks.reference(found) and marks.span_end(found)):
        return {"ok": False, "lines": [
            f"FAIL measure  {mark_id} is not a span: only a span on a reference "
            f"has a number to propose"]}
    said = found.get("answer")
    if said == "rejected":
        may, why = False, (f"rejected by the user ({found.get('why')}): its number "
                           f"may not be proposed")
    elif said or found.get("author") == "user":
        may, why = True, (f"the user's span ({said or 'drawn by the user'}): its "
                          f"number may be proposed, naming {mark_id}")
    elif found.get("placed") == "by eye":
        may, why = False, ("by eye, and the user has not answered it: its number "
                           "may not be proposed until they do")
    else:
        may, why = True, (f"snapped, and the user has not answered it: its number "
                          f"may be proposed as the agent's own reading, naming "
                          f"{mark_id}")
    number = marked(path, found.get("reading"))
    number = marks.text(number) if number else "no reading on file"
    return {"ok": True, "proposable": may,
            "lines": [f"ok   measure {mark_id} {why}", f"  {number}"]}


def asked(path, mark_id):
    """The reference a snapped span is on and the question that placed it, or
    a refusal. What `contour measure --again` runs before it can compare."""
    found = marked(path, mark_id)
    if found is None:
        return {"ok": False, "lines": [f"FAIL measure  no mark {mark_id} on file"]}
    if found.get("placed") != "snapped":
        how = "by eye" if found.get("placed") == "by eye" else "by hand"
        return {"ok": False, "lines": [
            f"FAIL measure  {mark_id} is not a snapped span: its ends were "
            f"placed {how}, so there is no question to ask again"]}
    return {"ok": True, "ref": marks.reference(found), "question": found["question"]}


def again(path, mark_id, runs, row, height):
    """Compare what a snapped span's question finds now with the ends it was
    drawn on. Writes nothing: the ends are what the span was answered on, and
    moving them would change what an answer meant after it was given."""
    found = marked(path, mark_id)
    q = found["question"]
    picked = q["runs"]
    if not all(1 <= n <= len(runs) for n in picked):
        return {"ok": False, "lines": [
            f"FAIL measure  {mark_id}: the reference no longer gives these ends; "
            f"runs {picked[0]} and {picked[1]} were asked for, and the scanline "
            f"now finds {found_runs(runs) or 'none'}"]}
    return same(found, mark_id, snap(runs, picked, q["between"], row, height))


def again_extent(path, mark_id, box, height):
    """`again`, for a span drawn across an extent: `box` is what its question
    finds now, or None when the colour no longer matches. Writes nothing."""
    found = marked(path, mark_id)
    q = found["question"]
    if box is None:
        return {"ok": False, "lines": [
            f"FAIL measure  {mark_id}: the reference no longer gives these ends; "
            f"{q['of']} is not in it at --tol {q['tol']:g}"]}
    return same(found, mark_id, edges(box, q["extent"], height))


def same(found, mark_id, ends):
    """Whether a snapped span's question still places the ends it was drawn
    on, said either way."""
    a, b = ends
    if [a, b] != [marks.pixel(found), marks.span_end(found)]:
        return {"ok": False, "lines": [
            f"FAIL measure  {mark_id}: the reference no longer gives these ends; "
            f"drawn at {marks.pixel(found)} to {marks.span_end(found)}, the same "
            f"question now places {a} to {b}"]}
    return {"ok": True, "lines": [f"ok   measure {mark_id} same ends: "
                                  f"{a} to {b}"]}
