"""Approvals waiting: what an unattended run's gates set aside (ADR 0028,
decisions 1 and 3).

Above `lib/` for the veto store's reason: a gate is the console's, so the one
door that writes an approval is here, and no `contour` subcommand can write one.
Only a console reads it either: it holds the call and the diff, which the survey
and the connector must never hand a requester (ADR 0027, decision 8).

In the space's `.contour/`, which a space git-ignores whole but for its marker:
an approval is this machine's business until somebody answers it, and a veto it
becomes is kept where vetoes are.
"""
import os
import time

from lib import space as space_lib, store

NAME = "approvals.json"

PREFIX = "a"


def path(space):
    return space_lib.layout(space).dot / NAME


def load(space):
    """Every approval waiting in this space, oldest first: the order they are
    answered in (ADR 0028, decision 3)."""
    return store.load(path(space), [])


def set_aside(space, run, category, tool, call, said, case):
    """Keep one call a gate could not pass, with what the gate would have shown:
    the act and the diff in `said`, and the agent's `case` for it. Returns it.

    The call as the agent wrote it, copied: what is applied later is what the
    person reads, and nothing the agent still holds can change it.
    """
    kept = load(space)
    approval = {"id": store.next_id(kept, PREFIX), "run": run, "at": time.time(),
                "category": category, "tool": tool, "call": dict(call),
                "said": said, "case": case}
    where = path(space)
    where.parent.mkdir(parents=True, exist_ok=True)
    beside = where.with_name(where.name + ".new")
    store.save(beside, kept + [approval])
    os.replace(beside, where)
    return approval
