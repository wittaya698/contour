"""A space's latest run, written (ADR 0027, decision 8).

Above `lib/` for the veto store's reason: a run is the console's own knowledge,
so the record's one writer is here. Reading it is `lib/last_run.py`'s.
"""
import os

from lib import store
from lib.last_run import path


def write(space, record):
    """Replace the record. One per space: the newest run's, whole.

    Written beside it and moved into place, because a requester reads it while
    the run is still going, and half a record is not one it can parse.
    """
    where = path(space)
    where.parent.mkdir(parents=True, exist_ok=True)
    beside = where.with_name(where.name + ".new")
    store.save(beside, record)
    os.replace(beside, where)
