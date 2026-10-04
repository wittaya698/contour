"""How many vetoes git does not hold yet, for readers below the console.

Read-only on purpose. A veto has one writer, the user at a gate, and its only
door is `console/vetoes.py`; but the connector asks this count too (ADR 0024,
decision 3), and the launcher may never import the console. So the count lives
here and the console asks it here, and the page and a chat cannot disagree
about how many are at risk.
"""
import json
from pathlib import Path

from . import git, store

NAME = "vetoes.json"
"""Beside `marks.json` at the space's root, and tracked for the same reason."""


def load(space):
    return store.load(Path(space) / NAME, [])


def committed(space):
    """The veto ids `HEAD` already holds.

    Asked of git rather than stamped on the veto as it is written: a stamp would
    be a claim about a commit that had not happened, and the thing that makes it
    true or false afterwards is `git checkout`, which does not come past here.
    """
    # A space that is not a repository yet, or a machine with no git, is not an
    # error to raise at the page — it is a space where no veto is committed,
    # which is what the count then says. `lib/git.py` says so once, for every
    # caller that used to decide it alone (slice 21).
    blob = git.show(space, "HEAD", NAME)
    try:
        return {v.get("id") for v in json.loads(blob)} if blob and blob.strip() else set()
    except json.JSONDecodeError:
        return set()


def uncommitted(space):
    """How many vetoes would die with this working tree."""
    held = committed(space)
    return sum(1 for v in load(space) if v.get("id") not in held)
