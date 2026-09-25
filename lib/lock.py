"""One run holds one space (ADR 0019, open question 11).

Two agents over one model space race on `build.py`, and the loser's work
disappears into a file the other one overwrote. The launcher takes this lock so
that terminal-versus-terminal is covered too, not only console-versus-terminal:
the console is a client of the toolkit with no privileged access, and a lock it
owned would leave the case that races today unprotected.
"""
import json
import os
import secrets
import socket
from pathlib import Path

NAME = "run.lock"


class Held(Exception):
    """Somebody else has the space. Carries the record so a caller can say who."""

    def __init__(self, record):
        super().__init__("space is held")
        self.record = record


def path(space):
    return Path(space) / ".contour" / NAME


def holder(space):
    """The record of whoever holds this space, or None."""
    try:
        return json.loads(path(space).read_text())
    except (OSError, ValueError):
        return None


def alive(record):
    """Is the run on this record still running?

    Signal 0 asks the kernel about a pid without sending anything. A record
    written on another machine — a space in a synced folder — cannot be judged
    this way at all, and unknowable is not gone: guessing gone there would open
    a space somebody else is building in.
    """
    if not record.get("pid"):
        return False                      # a record that names nobody holds nothing
    if record.get("host") != socket.gethostname():
        return True
    try:
        os.kill(record["pid"], 0)
    except ProcessLookupError:
        return False
    except (KeyError, TypeError, ValueError):
        return False
    except PermissionError:
        return True                       # somebody else's process, but a process
    return True


def take(space, command, run=None):
    """Hold the space, or raise `Held`. Never waits: a caller that queued would
    look like a hung build, and the honest answer is that somebody else is in
    here.

    `run` is the id of the run this caller already belongs to. A run's own
    builds are not refused by its own lock — the lock is between sessions, and
    a session that could not build would make it useless for the thing it
    protects. Such a caller gets the record back unchanged and, having taken
    nothing, releases nothing.
    """
    lock = path(space)
    lock.parent.mkdir(parents=True, exist_ok=True)
    record = {"pid": os.getpid(), "host": socket.gethostname(),
              "command": command[:200], "run": run or secrets.token_hex(8)}
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        theirs = holder(space) or {}
        if run and theirs.get("run") == run:
            return theirs
        if alive(theirs):
            raise Held(theirs)
        # The holder died without releasing. Take the space over rather than
        # leave it wedged behind a file the user would have to know about — and
        # say so, because a hold that ended by dying is worth hearing about.
        record["took_over"] = theirs
        tmp = lock.with_suffix(".lock.new")
        tmp.write_text(json.dumps(record))
        os.replace(tmp, lock)
    else:
        with os.fdopen(fd, "w") as f:
            json.dump(record, f)
    return record


def release(space, record):
    """Give the space back. Only the process that took it can: a record handed
    back by a re-entrant `take` carries somebody else's pid, and dropping the
    lock on their behalf would open the space while their run is still live."""
    if not record or record.get("pid") != os.getpid():
        return False
    on_disk = holder(space) or {}
    if on_disk.get("run") != record.get("run"):
        return False                      # already taken over as stale
    path(space).unlink(missing_ok=True)
    return True
