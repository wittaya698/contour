"""The mark store: a located comment, on disk (ADR 0018).

A mark is a comment that knows where it is. It carries the view it was placed
on, the pixel, one line of text, who wrote it, and whether it is still open.

The file is a flat JSON array, tracked by git — a mark is a finding about the
model, and `beaky`'s one known defect lived in the one file nothing verifies
(ADR 0016). It is not a spec: the spec guard covers `refs/` only, so writing
here needs no confirmation gate.
"""
import json
import subprocess
from pathlib import Path

from . import store

NAME = "marks.json"
PREFIX = "m"
"""The file and the letter its ids carry. `lib/store.py` holds the mechanics of
a JSON file and none of this: `m1` means a mark, which is a fact about marks."""


def load(path):
    """Every mark on file, or none at all. A space with no marks has no file."""
    return store.load(path, [])


def save(path, marks):
    return store.save(path, marks)


def next_id(marks):
    return store.next_id(marks, PREFIX)


def append(path, mark, author="user"):
    """Store one mark, stamped with its id, author and status. Returns it.

    Always open, whoever wrote it. There is no way to append a closed mark
    because there is no reason to: a finding that was never outstanding is not
    a finding, and `close` is the one door, reached only from the page.
    """
    marks = load(path)
    stored = {"id": next_id(marks), **mark, "author": author, "status": "open"}
    save(path, marks + [stored])
    return stored


def close(path, mark_id):
    """Mark one finding as dealt with, by the only party allowed to say so.

    Returns the closed mark, or None if no such id is on file — the page can
    be looking at a list the store no longer has.
    """
    marks = load(path)
    found = None
    for mark in marks:
        if mark.get("id") == mark_id:
            mark["status"] = "closed"
            found = mark
    if found is not None:
        save(path, marks)
    return found


def _released(path):
    """The last release tag and the marks it holds — `(tag, marks)`, or
    `(None, [])` when there is no tag to archive anything.

    The tag *is* the archive, so `git show` is asked what it actually
    contains rather than a stamp of our own being trusted about it.
    """
    path = Path(path)
    # Two keys: the last one given is git's primary, so this is newest
    # first, with the version number breaking a same-second tie.
    tags = _git(path.parent, "tag", "--sort=-v:refname", "--sort=-creatordate")
    if not tags:
        return None, []
    tag = tags.splitlines()[0]
    blob = _git(path.parent, "show", f"{tag}:./{path.name}")
    try:
        return tag, (json.loads(blob) if blob else [])
    except json.JSONDecodeError:
        return tag, []


def _git(cwd, *args):
    try:
        done = subprocess.run(("git",) + args, cwd=cwd, capture_output=True,
                              text=True)
    except OSError:
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def prune(path):
    """Drop closed marks the last release tag already holds.

    Returns a line naming what went and where it still is, or None when
    nothing was dropped: deleting from a tracked file in silence is worse
    than not deleting at all.

    Open marks are never pruned, at any age — an unanswered finding does not
    expire — and nothing is dropped that git cannot show back, so with no tag,
    or no marks file in it, this does nothing at all.
    """
    tag, archived = _released(path)
    if not archived:
        return None
    gone = {m.get("id") for m in archived if m.get("status") == "closed"}
    here = load(path)
    kept = [m for m in here
            if not (m.get("status") == "closed" and m.get("id") in gone)]
    dropped = len(here) - len(kept)
    if not dropped:
        return None
    save(path, kept)
    return f"{phrase(dropped)} pruned, closed at {tag}"


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
