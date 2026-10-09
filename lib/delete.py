"""Deleting a model space: it leaves a bundle (ADR 0021, decisions 6, 7 and 8).

A space holds the one input nothing can regenerate, its `refs/`, and nothing
backs it up yet (open question 6). So a delete writes a `git bundle` of every
ref into a trash directory first, and removes the space only once the bundle is
written and proved. Never a copy of the tree: a copy of a space is a space, and
would list as a live one (ADR 0015).

`propose` changes nothing; `perform` does what `propose` says, given the space's
own name as the confirm — the command line's spelling of typing it.
"""
import contextlib
import json
import shutil
import time
from pathlib import Path

from . import git, lock, presence
from .survey import about, trash   # where the trash is, read where the trash is listed


def destination(root):
    """A bundle path named for the space and the date, that nothing holds yet."""
    stem = f"{root.name}-{time.strftime('%Y-%m-%d')}"
    to, n = trash() / f"{stem}.bundle", 1
    while to.exists():
        n += 1
        to = trash() / f"{stem}-{n}.bundle"
    return to


def record(root, bundle):
    """Write down where the space stood and when it went, beside its bundle:
    the bundle carries the history and not the path, and restoring to the old
    location needs the path. Returns None, or what went wrong."""
    try:
        about(bundle).write_text(json.dumps(
            {"name": root.name, "path": str(root), "deleted": time.strftime("%Y-%m-%d")}))
    except OSError as e:
        return f"could not write {about(bundle)}: {e}"
    return None


def refusal(root, name, mine=None):
    """Why this delete may not happen, or None. `mine` is the hold `perform`
    took, which is not somebody else's run."""
    if name != root.name:
        return (f"{name!r} is not this space's name; to delete it, type {root.name}: "
                f"contour delete {root.name} --yes")
    occupied = presence.occupied(root, "delete", mine)
    if occupied:
        return occupied
    changed = git.changes(root)
    if changed is None:
        return "git could not say whether this space has uncommitted changes"
    if changed:
        return ("uncommitted changes, which a bundle cannot carry: " + ", ".join(changed)
                + "; commit or discard them first")
    work = sorted(str(f.relative_to(root)) for f in (root / "work").rglob("*")
                  if not f.is_dir())
    if work:
        return ("a working file is in work/, which git ignores and a bundle cannot "
                "carry: " + ", ".join(work) + "; move it out of the space first")
    return None


DISK = ("the bundle is on the same disk as the space: it undoes a mistaken "
        "delete, and is no backup against losing the disk")

LEFT = ("out/ and exports/ are not kept: they are rebuilt from build.py")


def propose(root, name, mine=None):
    """What deleting the space at `root` would do. Writes nothing."""
    return {"path": str(root), "name": root.name, "bundle": str(destination(root)),
            "disk": DISK, "left": LEFT, "unseen": presence.UNSEEN,
            "refused": refusal(root, name, mine)}


def perform(root, name):
    """Do what `propose` says, and return what it said.

    Holds the space throughout, so no run can start halfway through (ADR 0021,
    decision 7). The hold's file is inside the space and goes with it.
    """
    try:
        mine = lock.take(root, f"contour delete {name}")
    except lock.Held:
        return propose(root, name)
    try:
        proposal = propose(root, name, mine)
        if proposal["refused"]:
            return proposal
        to = Path(proposal["bundle"])
        try:
            to.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            failed = f"could not make {to.parent}: {e}"
        else:
            failed = git.bundle(root, to) or record(root, to)
        if failed:
            for f in (to, about(to)):
                with contextlib.suppress(OSError):
                    f.unlink(missing_ok=True)  # half a bundle is no bundle
            proposal["refused"] = f"no bundle, so nothing was deleted: {failed}"
            return proposal
        try:
            shutil.rmtree(root)
        except OSError as e:
            proposal["refused"] = (f"the bundle is written, but removing the space "
                                   f"stopped partway: {e}; what is left is at {root}, "
                                   f"and everything committed is in {to}")
        return proposal
    finally:
        lock.release(root, mine)


def lines(proposal):
    """The proposal as a person reads it."""
    return [f"delete {proposal['path']}",
            f"    bundle -> {proposal['bundle']}", "",
            proposal["disk"], proposal["left"], "", proposal["unseen"], "",
            f"nothing changed. to do it: contour delete {proposal['name']} --yes"]
