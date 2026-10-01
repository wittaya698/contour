"""Presence: a page serving a space, said on disk (ADR 0021, decision 8).

A console holds its space only during a run, and a canvas never holds it (open
question 11), so a console left idle or a canvas left open was invisible: nothing
said a page was still serving the space. Anything that moved or removed the space
would leave that page writing to a path that no longer existed.

Not a hold. A hold stops a second run; presence stops nothing, and its one reader
is `contour spaces --json`, for the lobby to act on. It borrows the hold's shape
and the hold's rule for alive, so the two cannot disagree about who is still
there — but not its file: two canvases can be open on one space, and each says
so in a file of its own.
"""
import contextlib
import json
import os
import secrets
import socket

from . import lock
from . import space as space_lib

NAME = "presence"


def where(space):
    return space_lib.layout(space).dot / NAME


@contextlib.contextmanager
def present(space, kind):
    """Say this process is serving `space` as a `kind` of page, for as long as
    the block lasts. Removed on every path out of it; a process that dies
    without leaving is judged gone by `live`, so nothing has to clean up."""
    folder = where(space)
    folder.mkdir(parents=True, exist_ok=True)
    mine = folder / f"{secrets.token_hex(8)}.json"
    mine.write_text(json.dumps({"kind": kind, "pid": os.getpid(),
                                "host": socket.gethostname()}))
    try:
        yield mine
    finally:
        mine.unlink(missing_ok=True)


def live(space):
    """Every page serving `space` right now. Reading writes nothing: a record
    whose process is gone is left where it is and not reported, because the
    lobby that asks this promises to change nothing by asking."""
    found = []
    for f in sorted(where(space).glob("*.json")):
        try:
            record = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(record, dict) and lock.alive(record):
            found.append({k: record.get(k) for k in ("kind", "pid", "host")})
    return found
