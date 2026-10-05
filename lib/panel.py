"""What the sheet panel says about the picture it is showing (ADR 0019, 13/27).

The sheet changes only when a build finishes, so a page that showed it without
saying which build it is of would be authoritative about whichever one happened
to be on screen. `views.json` already carries a fingerprint of the build its
cameras drew, and `lib/views.py` already hashes the build on disk the same way,
so the label is a comparison of two numbers that exist — no new source of truth
and nothing for a second reader to disagree with.

Stdlib, and Blender-free: the launcher serves this and so does the console, and
the console may never import a `bpy`-bound module (ADR 0019, decision 32).
"""
from datetime import datetime
from pathlib import Path

from . import marks as marks_store
from . import store
from . import verdict as words
from . import views as sheet_views
"""Aliased because `state` takes a `views` argument — the path to the file —
and the module that reads it would be shadowed by its own subject."""

NAME = "last-build.json"
"""The last build's verdict, beside the log of it in the space's `.contour/`.

Written because a build that raised leaves the *previous* `.blend` untouched, so
the two fingerprints agree and a panel comparing them would call a picture of a
build that never finished current. `report.json` cannot serve: it is deleted at
the start of every stage, including the render that follows a check.
"""


def record(path, rep, blend):
    """Say what this check came to, where the page can read it — the whole
    report, because nothing else keeps it past the next stage (ADR 0024,
    decision 6).

    `results` is a verify verdict, and a report that carries one got as far as
    being judged — which is as far as being saved. A report without one is a
    stage that died, and the build on disk is whatever was there before it ran,
    so it is named only when this check made it.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    built = "results" in rep
    store.save(path, {"built": built, "ok": rep["ok"], "lines": rep["lines"],
                      "results": rep.get("results", []),
                      "secs": rep.get("secs"),
                      "build": sheet_views.fingerprint(blend) if built else None,
                      "when": datetime.now().astimezone().isoformat(timespec="seconds")})


def state(views=None, blend=None, verdict=None, marks=None):
    """What the panel shows, as one dict the page renders and does not reason
    about. `build` is None when nothing has ever been drawn, which is a space
    at the start and not a broken page."""
    said = store.load(verdict, None) if verdict else None
    # Whether the model is right, in plain words, beside which build the sheet
    # is of and never on it (ADR 0025, decision 4). None until a first check.
    told = words.say(said) if said else None
    sheet = store.load(views, None) if views else None
    if sheet is None:
        return {"build": None, "current": False, "verdict": told}
    failed = bool(said) and not said["built"]
    why = ("last build failed" if failed
           else sheet_views.stale(sheet, blend) and "the build moved on")
    return {"build": sheet["build"] or None, "current": not why, "why": why,
            "marks": pending(marks) if failed else None, "verdict": told}


def pending(path):
    """What the page says about marks nobody cast a ray for, or None.

    Said only when there are such marks: ADR 0018 was careful that marks report
    one line when open and nothing at zero, and a sentence that is always on
    screen is furniture nobody reads.
    """
    if not path or not marks_store.unresolved(marks_store.load(path)):
        return None
    return "marks not resolved: last build failed"
