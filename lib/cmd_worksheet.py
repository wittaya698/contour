"""./contour worksheet: every span drawn onto its reference (ADR 0022, decision 8).

It reads the photographs, which needs bpy, and saves the image. What each span
says is `lib/worksheet.py`'s, and how it is drawn is `lib/worksheet_draw.py`'s.

The references are read and never written. The worksheet is a new file in the
space, regenerated whole from the marks and the references each time.
"""
import numpy as np

import bpy

from . import cmd_measure, marks, space, worksheet, worksheet_draw


def run(args):
    P = space.parse([])
    kept = marks.load(P.marks)
    drawn = worksheet.spans(kept) + worksheet.directions(kept)
    if not drawn:
        return {"ok": True, "lines": [
            "ok   worksheet  no spans or directions on file: nothing to draw, "
            "nothing written"]}
    pictures, missing = {}, []
    for ref in sorted({s["ref"] for s in drawn}):
        path = P.root / "refs" / ref
        if path.exists():
            # Bottom-up as Blender hands it over; the worksheet counts from the
            # top, as a mark's pixel does.
            pictures[ref] = np.flipud(cmd_measure.load(path))
        else:
            missing.append(ref)
    lines = [f"  {s['id']} is on {s['ref']}, which is not in refs/: not drawn"
             for s in drawn if s["ref"] in missing]
    if not pictures:
        return {"ok": False, "lines": ["FAIL worksheet  no reference a span is on "
                                       "is in refs/: nothing drawn", *lines]}
    image, placed = worksheet_draw.compose(pictures, kept)
    h, w = image.shape[:2]
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = np.flipud(image)
    out = bpy.data.images.new("worksheet", w, h, alpha=False)
    out.pixels.foreach_set(rgba.ravel())
    target = P.root / worksheet.NAME
    out.filepath_raw = str(target)
    out.file_format = "PNG"
    out.save()
    n = sum(1 for s in drawn if s["ref"] in placed and "lines" not in s)
    d = sum(1 for s in drawn if s["ref"] in placed and "lines" in s)
    aimed = f", {d} direction{'s' if d != 1 else ''}" if d else ""
    return {"ok": True, "lines": [
        f"ok   worksheet  {n} span{'s' if n != 1 else ''}{aimed} on {len(placed)} "
        f"reference{'s' if len(placed) != 1 else ''} -> {P.display(target)}  "
        f"{w}x{h}px", *lines]}
