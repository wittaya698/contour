"""`contour worksheet`: the spans, drawn onto the references (ADR 0022, decision 8).

The user sees every span on the canvas. The agent cannot see the canvas, so
this draws the same thing once, as one image it can look at for about what a
sheet costs. It is a new file in the space and never a write to a reference:
an annotated photograph is not the photograph (rule 1).

What each span says is worked out here, in the standard library, so the
launcher can tell there is nothing to draw without starting Blender. Where it
goes and how it is drawn is `worksheet_draw`'s; reading the photographs and
saving the image are `cmd_worksheet`'s.
"""
import hashlib
import json
import re

from . import marks, store

NAME = "worksheet.png"
"""Where it is written, in the space beside `sheet.png`, and tracked as that is:
ADR 0017 made the worksheet a picture to share."""

RECORD = "worksheet.json"
"""Which spans the worksheet was drawn from, in the space's `.contour/`. It is
of no build, so a build fingerprint would say nothing about it; what it can
fall behind is the spans (ADR 0024, decision 3). Not beside the PNG, which is
tracked: this is the launcher's note, not a picture to share."""

NUMBER = re.compile(r"(\d+) (mm|px) ±(\d+)")


def spans(all_marks):
    """Every span on a reference, in the order they were made, each as
    `{"id", "ref", "pixel", "to", "label"}` and what it is drawn as: `agent`,
    `by_eye`, `rejected`.

    Every one, closed and rejected included: the picture accounts for each
    span, and a rejected span left off it would read as never drawn.
    """
    return [{"id": m["id"], "ref": marks.reference(m), "pixel": marks.pixel(m),
             "to": marks.span_end(m), "label": label(m, all_marks),
             "agent": m.get("author") == "agent",
             "by_eye": m.get("placed") == "by eye",
             "rejected": m.get("answer") == "rejected"}
            for m in all_marks if marks.reference(m) and marks.span_end(m)]


def directions(all_marks):
    """Every direction on a reference, as `{"id", "ref", "lines", "label"}` and
    what it is drawn as, as `spans` gives a span (ADR 0032, decision 2). Apart
    from the spans: a direction has no number of its own, and its lines are
    drawn to show where they meet."""
    return [{"id": m["id"], "ref": marks.reference(m),
             "lines": [[got["from"], got["to"]] for got in marks.lines(m)],
             "by_eye": [got.get("placed") == "by eye" for got in marks.lines(m)],
             "label": [f"{m['id']} direction {m['direction']}", ", ".join(_aimed(m))],
             "agent": m.get("author") == "agent",
             "rejected": m.get("answer") == "rejected"}
            for m in all_marks if marks.reference(m) and marks.lines(m)]


def _aimed(mark):
    yield mark.get("author", "user")
    placed = [got.get("placed") for got in marks.lines(mark)]
    eyed = placed.count("by eye")
    if eyed:
        yield f"{eyed} line{'s' if eyed != 1 else ''} by eye"
    else:
        yield "snapped" if all(p == "snapped" for p in placed) else "by hand"
    if mark.get("answer"):
        yield mark["answer"]
    elif mark.get("author") == "agent":
        yield "unanswered"


def label(mark, all_marks):
    """Two lines: the id and the number; whose, how placed, and the answer."""
    return [f"{mark['id']} {number(mark, all_marks)}",
            ", ".join(_said(mark))]


def _said(mark):
    yield mark.get("author", "user")
    yield {"snapped": "snapped", "by eye": "by eye"}.get(mark.get("placed"), "by hand")
    if mark.get("answer"):
        yield mark["answer"]
    elif mark.get("author") == "agent":
        yield "unanswered"


def number(mark, all_marks):
    """The span's reading, short: `597 mm ±3`. The linked reading when there is
    one; else the latest one measured from it; else that none was."""
    found = next((m for m in all_marks if m.get("id") == mark.get("reading")), None)
    if found is None:
        found = next((m for m in reversed(all_marks)
                      if marks.text(m).startswith(f"span {mark['id']}:")), None)
    got = NUMBER.search(marks.text(found)) if found else None
    return f"{got[1]} {got[2]} ±{got[3]}" if got else "not measured"


def fingerprint(all_marks):
    """Which spans these are, as twelve hex characters — what the worksheet
    draws, so a change it would draw differently is a change here."""
    drawn = spans(all_marks)
    aimed = directions(all_marks)
    # Spans alone print as they did before directions were drawn, so no
    # worksheet on disk goes stale because the code learned something new.
    said = json.dumps({"spans": drawn, "directions": aimed} if aimed else drawn,
                      sort_keys=True).encode()
    return hashlib.sha256(said).hexdigest()[:12]


def anything(all_marks):
    """Whether there is anything to draw: a span, or a direction."""
    return bool(spans(all_marks) or directions(all_marks))


def record(dot, marks_path):
    """Say which spans the worksheet just drawn is of."""
    store.save(dot / RECORD, {"spans": fingerprint(marks.load(marks_path))})


def state(dot, marks_path):
    """What a reader is told about the worksheet on disk, in the panel's shape."""
    drawn = (store.load(dot / RECORD, None) or {}).get("spans")
    why = (None if drawn == fingerprint(marks.load(marks_path))
           else "the spans changed since it was drawn: run contour worksheet"
           if drawn else "not known which spans it was drawn from: run contour worksheet")
    return {"build": None, "current": not why, "why": why}
