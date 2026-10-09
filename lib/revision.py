"""A spec may change; it may not change silently (ADR 0016).

The contract's revision number, read the one way: `contour check` asks it
whether a changed spec was bumped, and `contour rename` asks it what to bump
from, so the two cannot disagree about which line is the field.
"""
import re

from . import git
from . import space as space_lib

FIELD = re.compile(r"^revision:\s*(\d+)\s*$", re.M)
MODEL = re.compile(r"^model:[^\n]*$", re.M)


def of(text):
    """The contract's revision number. Absent means 0, so a spec written before
    ADR 0016 is revision 0 and its first correction is 1. Anchored at column 0,
    so the word inside an indented block scalar is not mistaken for the field."""
    m = FIELD.search(text or "")
    return int(m.group(1)) if m else 0


def model(text):
    """The name a spec gives its model, or None."""
    m = MODEL.search(text or "")
    return m.group(0).split(":", 1)[1].strip() if m else None


def unbumped(root):
    """`(at HEAD, now)` when the spec differs from HEAD and its revision did not
    move past HEAD's, else None — the one case where a change nobody approved
    looks different from a change that was. An untracked spec, or a space with
    no commit yet, is being created, and creation is not mutation."""
    spec = space_lib.layout(root).spec
    if not spec.exists():
        return None
    was_text = git.show(root, "HEAD", "spec.yaml")
    if was_text is None:
        return None
    now = spec.read_text(encoding="utf-8")
    if now == was_text or of(now) > of(was_text):
        return None
    return of(was_text), of(now)
