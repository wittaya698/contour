"""Restoring a deleted model space: a clone of its bundle (ADR 0021, decision 6).

A deleted space is a bundle in the trash and a record beside it of where the
space stood (`lib/delete.py`). Restoring clones the bundle back to a space root,
and the bundle stays in the trash until the user removes it: a restore is undone
by deleting again, and that writes a new bundle.
"""
from pathlib import Path

from . import delete, git
from . import space as space_lib
from .survey import deleted   # the trash as the list shows it (issue 84)


def refusal(gone, where, toolkit):
    """Why this restore may not happen, or None. Checked before anything is
    written, so a refused restore leaves no directory behind."""
    if where.exists() or where.is_symlink():
        return f"{where} already exists; restore somewhere else with --to <dir>"
    if any(s.name == gone["name"] for s in space_lib.spaces(space_lib.roots(toolkit))):
        return (f"a live space is already called {gone['name']}; rename or delete "
                f"it first, since a space's name is its identity")
    return None


def restore(id, toolkit, to=None):
    """Clone the deleted space `id` back where it stood, or into the directory
    `to`, and make it a space again: its `pre-push` stub reinstalled, since no
    clone carries `.git/hooks`.

    `to` is where the space goes and not what it is called: a space's name is
    its directory, and its spec says the same name, so it comes back under the
    name it was deleted with."""
    gone = next((d for d in deleted() if d["id"] == id), None)
    if gone is None:
        return {"id": id, "refused": f"nothing in the trash is called {id}; "
                                     f"contour spaces lists what is"}
    if not gone["name"]:
        return dict(gone, refused=f"nothing records what {id} was called, and a "
                                  f"space's name is its identity; rename the bundle "
                                  f"<name>-<date>.bundle")
    if not (to or gone["path"]):
        return dict(gone, refused=f"nothing records where {gone['name']} stood; "
                                  f"say where to restore it with --to <dir>")
    where = Path(to) / gone["name"] if to else Path(gone["path"])
    said = dict(gone, path=str(where), refused=refusal(gone, where, toolkit))
    if not said["refused"]:
        said["refused"] = git.clone(gone["bundle"], where) or space_lib.stub(where, toolkit)
    return said


GONE = "a removed bundle cannot be undone: nothing else in contour holds its history"


def proposed_purge(id):
    """What removing the bundle `id` would do. Writes nothing. Says whether a
    space stands where it stood, or this bundle is the only copy left."""
    gone = next((d for d in deleted() if d["id"] == id), None)
    if gone is None:
        return {"id": id, "refused": f"nothing in the trash is called {id}; "
                                     f"contour spaces lists what is"}
    copy = (f"a live space still stands at {gone['live']}, though this bundle may "
            f"hold history it no longer has" if gone["live"]
            else "this is the only copy of the space")
    return dict(gone, copy=copy, gone=GONE, refused=None)


def purge(id):
    """Remove the bundle `id` and its record, and return what was proposed."""
    said = proposed_purge(id)
    if said["refused"]:
        return said
    bundle = Path(said["bundle"])
    try:
        bundle.unlink()
        delete.about(bundle).unlink(missing_ok=True)
    except OSError as e:
        said["refused"] = f"could not remove {bundle}: {e}"
    return said


def purge_lines(said):
    """The purge proposal as a person reads it."""
    return [f"remove {said['bundle']}", f"    {said['name']}, deleted {said['deleted']}", "",
            said["copy"], said["gone"], "",
            f"nothing changed. to do it: contour purge {said['id']} --yes"]
