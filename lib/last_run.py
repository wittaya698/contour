"""A space's latest run, read (ADR 0027, decision 8).

The reading half, below the console so the connector and the launcher can ask
it, as `lib/spend.py` is to `console/spend.py`. One record per space, the newest
run's only: a status, not a history, and nothing resumes from it.
"""
from pathlib import Path

from . import space as space_lib, spend, store, verdict

ENDED = ("finished", "stopped")

NAME = "last-run.json"
"""In the space's `.contour/`, which a space git-ignores whole but for its
marker: run state is this machine's, and never part of a version."""


WITHHELD = ("this run set something aside for you, so what it did is told on its "
            "console's page and not here")

ANSWERED = ("this run set something aside, and all of it has been answered on "
            "its console's page; nothing waits")
"""The withheld closing once nothing it set aside is left waiting: the first
read as something still waiting, over an empty list (issue 105)."""


def waiting(space, act):
    """A parked run, in the sentence the hold's refusal says: the space, and
    what it is waiting for you to do."""
    return f"{Path(space).name} is waiting for you: {act}"


def approvals(space):
    """What waits in this space for the person, as the record says it: the acts
    and a question's text, never why (ADR 0028, decision 5)."""
    return (store.load(path(space), None) or {}).get("approvals") or []


def awaiting(acts):
    """What waits, in one plain line, or None when nothing does."""
    if not acts:
        return None
    return (f"{len(acts)} approval{'s' if len(acts) > 1 else ''} waiting: "
            + "; ".join(acts))


def unattended(space):
    """Is a run nobody was watching still going in this space? Its console
    has no person's tab to be the way in, so it shows its own page when asked
    (ADR 0027, decision 7)."""
    run = read(space) or {}
    return run.get("requester") is not None and run.get("state") not in ENDED


def parked(space):
    """What a run here is waiting for you to do, or None. Only while the run
    that said so still holds the space: a console that died at a gate left a
    record saying it waits, and nothing does."""
    from . import lock
    run, rec = read(space) or {}, lock.holder(space)
    if run.get("state") != "waiting for you" or not rec or not lock.alive(rec) \
            or rec.get("run") != run.get("run"):
        return None
    return run.get("act")


def path(space):
    return space_lib.layout(space).dot / NAME


def read(space):
    """The latest run as a requester reads it, or None if nothing has run.

    A run that set something aside has its closing withheld, said as such.
    An ended run also says what the last check found and what the run cost,
    both read here from the files that hold them and never copied into the
    record, so there is one verdict and one price wherever they are read.
    """
    said = store.load(path(space), None)
    if said is not None and said.get("set_aside"):
        # The closing of a run that set something aside is the case for it,
        # which only the page shows (ADR 0028, decision 5), and once answered
        # it would be stale besides: withheld for good.
        withheld = WITHHELD if said.get("approvals") else ANSWERED
        said = {**said, "closing": withheld if said.get("closing") else None}
    if said is None or said.get("state") not in ENDED:
        return said
    from . import panel
    kept = store.load(space_lib.layout(space).dot / panel.NAME, None)
    cost = next((r for r in spend.runs(space) if r["run"] == said.get("run")), None)
    return {**said, "verdict": kept and verdict.say(kept),
            "spend": {"turns": cost["turns"] if cost else 0,
                      "weighted": cost["weighted"] if cost else 0}}
