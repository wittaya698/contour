"""The last export, as the console's card says it (ADR 0025, decision 5).

Export has two ways in — the page's button, and the agent inside a run — and
one result, so what it came to is written by the one command both of them run,
beside the last build's verdict in the space's `.contour/`. The card is read
from that and from the build on disk, and never from which door was used.

Stdlib, and Blender-free: the launcher writes this and the console reads it.
"""
from datetime import datetime
from pathlib import Path

from . import store
from . import verdict as words
from . import views

NAME = "last-export.json"

SAME = "checked: it reopens the same as it was built"
DIFFERENT = "it reopens differently from how it was built"


def record(path, rt, glb, blend, run=None):
    """Say what this export came to. `rt` is the round-trip's report; `run` is
    the run it was made inside, which is how a card knows Claude made it. An
    export that wrote no file leaves no card: there is nothing to hand over,
    and a card naming the last one would be naming a file that is gone."""
    path, glb = Path(path), Path(glb)
    if not glb.is_file():
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    store.save(path, {"file": str(glb), "bytes": glb.stat().st_size,
                      "by": "claude" if run else "you",
                      "ok": rt["ok"],
                      "differs": [words.sentence(r) for r in rt.get("results", [])
                                  if not r["ok"]],
                      "build": views.fingerprint(blend),
                      "when": datetime.now().astimezone().isoformat(timespec="seconds")})


def offer(last_build, live=False):
    """Whether the page's button may export now, and the words when it may
    not. A run holds the space, and export takes the hold; a red build is a
    model that does not match its spec, and handing one over is the agent's
    call to argue inside a run, never a button's."""
    if live:
        return {"can": False, "why": "finish or end the run first"}
    kept = store.load(last_build, None)
    if kept is None or not kept["built"]:
        return {"can": False, "why": "check the model first"}
    if not kept["ok"]:
        return {"can": False, "why": "fix the failing checks first"}
    return {"can": True, "why": None}


def file(path):
    """The file the last export wrote, while it is still there, or None."""
    kept = store.load(path, None)
    return Path(kept["file"]) if kept and Path(kept["file"]).is_file() else None


def card(path, blend):
    """What the card shows, as one dict the page renders and does not reason
    about, or None before anything has been exported. `older` is whether the
    build on disk has moved past the one the file was exported from."""
    kept = store.load(path, None)
    if kept is None or not Path(kept["file"]).is_file():
        return None
    return {"name": Path(kept["file"]).name, "size": size(kept["bytes"]),
            "by": kept["by"],
            "roundtrip": SAME if kept["ok"] else DIFFERENT,
            "differs": kept["differs"],
            "older": kept["build"] != views.fingerprint(blend)}


def size(n):
    """A file's size as a person reads it."""
    for unit, at in (("MB", 1 << 20), ("KB", 1 << 10)):
        if n >= at:
            return f"{n / at:.1f} {unit}".replace(".0 ", " ")
    return f"{n} bytes"
