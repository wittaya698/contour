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
    found = next((m for m in marks.load(path) if m.get("id") == mark_id), None)
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
    found = next((m for m in marks.load(path) if m.get("id") == mark_id), None)
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
