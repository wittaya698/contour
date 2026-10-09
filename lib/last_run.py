"""A space's latest run, read (ADR 0027, decision 8).

The reading half, below the console so the connector and the launcher can ask
it, as `lib/spend.py` is to `console/spend.py`. One record per space, the newest
run's only: a status, not a history, and nothing resumes from it.
"""
from . import space as space_lib, spend, store, verdict

ENDED = ("finished", "stopped")

NAME = "last-run.json"
"""In the space's `.contour/`, which a space git-ignores whole but for its
marker: run state is this machine's, and never part of a version."""


def path(space):
    return space_lib.layout(space).dot / NAME


def read(space):
    """The latest run as a requester reads it, or None if nothing has run.

    An ended run also says what the last check found and what the run cost,
    both read here from the files that hold them and never copied into the
    record, so there is one verdict and one price wherever they are read.
    """
    said = store.load(path(space), None)
    if said is None or said.get("state") not in ENDED:
        return said
    from . import panel
    kept = store.load(space_lib.layout(space).dot / panel.NAME, None)
    cost = next((r for r in spend.runs(space) if r["run"] == said.get("run")), None)
    return {**said, "verdict": kept and verdict.say(kept),
            "spend": {"turns": cost["turns"] if cost else 0,
                      "weighted": cost["weighted"] if cost else 0}}
