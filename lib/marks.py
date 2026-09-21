"""The mark store: a located comment, on disk (ADR 0018).

A mark is a comment that knows where it is. It carries the view it was placed
on, the pixel, one line of text, who wrote it, and whether it is still open.

The file is a flat JSON array, tracked by git — a mark is a finding about the
model, and `beaky`'s one known defect lived in the one file nothing verifies
(ADR 0016). It is not a spec: the spec guard covers `refs/` only, so writing
here needs no confirmation gate.
"""
import json
import re
from pathlib import Path

NAME = "marks.json"
_ID = re.compile(r"^m(\d+)$")


def load(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def save(path, marks):
    Path(path).write_text(json.dumps(marks, indent=2) + "\n", encoding="utf-8")


def next_id(marks):
    """One past the highest ever used, not one past the count: closed marks are
    pruned (0018-2), and a reused id would point at two different things."""
    used = [int(m.group(1)) for m in
            (_ID.match(str(k.get("id", ""))) for k in marks) if m]
    return f"m{max(used, default=0) + 1}"


def append(path, mark):
    """Store one mark, stamped with its id, author and status. Returns it."""
    marks = load(path)
    stored = {"id": next_id(marks), **mark, "author": "user", "status": "open"}
    save(path, marks + [stored])
    return stored


def phrase(n):
    """`3 marks`, `1 mark` — the count with the right noun on it."""
    return f"{n} mark{'' if n == 1 else 's'}"


def status_line(path):
    """What `contour check` says about the marks, or None when there is
    nothing to say (ADR 0018).

    Never red, and never part of the exit code: red means the build violates
    the spec, and a mark is precisely the thing the spec did not catch.
    """
    n = sum(1 for m in load(path) if m.get("status") == "open")
    return f"{phrase(n)} open" if n else None
