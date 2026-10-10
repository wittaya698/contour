"""The ceiling: what an unattended run may spend before it is stopped (ADR 0027,
decision 13).

In weighted tokens, the unit `lib/spend.py` weighs a turn in and the spend line
already speaks, so the number the person sets is the number they watch. It
lives in `~/.contour` beside the ask-list, out of every space and so out of the
agent's in-scope reach and the requester's, for ADR 0019 decision 6's reason.
There is no default: with none set, an unattended run is refused, so the first
one makes the person choose a number rather than Contour choosing it for them.
"""
import json
import os

from lib.policy import home

NAME = "ceiling.json"


def path():
    """`~/.contour/ceiling.json`, moved with the rest by `$CONTOUR_HOME`."""
    return home() / NAME


def read():
    """The ceiling in weighted tokens, or None when none is set."""
    try:
        return int(json.loads(path().read_text())["weighted"])
    except FileNotFoundError:
        return None


def set(weighted):
    """Set the ceiling. A whole number above nothing: a ceiling of nothing
    would stop every run at its first turn, which is no run at all."""
    if not isinstance(weighted, int) or isinstance(weighted, bool) or weighted < 1:
        raise ValueError(f"a ceiling is a whole number of weighted tokens above "
                         f"0, not {weighted!r}")
    where = path()
    where.parent.mkdir(parents=True, exist_ok=True)
    fresh = where.with_name(NAME + ".new")
    fresh.write_text(json.dumps({"weighted": weighted}) + "\n")
    os.replace(fresh, where)
    return weighted


def remove():
    """No ceiling: unattended runs are refused again until one is set."""
    path().unlink(missing_ok=True)
