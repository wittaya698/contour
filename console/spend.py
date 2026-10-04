"""What a run cost, per turn (ADR 0019, decision 37).

Token cost is the second of Contour's three stated priorities, and the tool that
serves it — `tools/tokens.py` — measures it by parsing the Claude Code transcript
for a project. A console run produces no such transcript, so recording nothing
here would blind that tool in the same change that makes runs longer and adds a
turn per gate.

What the console has instead is better than anything a transcript could be parsed
for: the SDK reports usage per turn, cache reads included. It is appended here,
one line per turn, in the vocabulary `tools/tokens.py` already counts in — so the
reader translates nothing and a console run and a terminal iteration can be read
off one table.

The write is above `lib/` for the veto store's reason: a run is the console's
own knowledge, and no `contour` subcommand has a turn to account for. Reading it
is not, so that half is `lib/spend.py`'s, where the connector can ask it.
"""
import json
from datetime import datetime, timezone

from lib.spend import (CACHE_READ_MULT, CACHE_WRITE_MULT, FIGURES, NAME,  # noqa: F401
                       OUTPUT_MULT, counts, load, path, thinking, weigh)


def total(space, run):
    """What one run has cost so far: the turns and the sum of each figure.

    Read back off the file rather than kept in memory, so the number on the page
    and the number the accounting reports are the same number — a total held
    beside the file is a second place for it to be wrong.
    """
    lines = load(space, run)
    figures = {k: sum(t.get(k, 0) for t in lines) for k in FIGURES}
    return {"turns": len(lines), **figures, "weighted": weigh(figures)}


def record(space, run, usage, gates=0, prompt=""):
    """Append one turn. Returns the line as written.

    `gates` is how many gates this run had stopped at before this turn, which is
    the only way the file can know a verdict happened between two turns: a turn
    that followed one carries a re-explanation of everything the agent had
    already said, and that cost is what makes tuning the ask-list an informed act
    rather than an irritated one (ADR 0019, decision 37).
    """
    line = {"run": run, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            # On every line and not only the first: the accounting is read by
            # somebody asking where their tokens went, and a run id is not an
            # answer to that. A line that can be read on its own also survives a
            # file whose first line was lost with the process that was writing it.
            "prompt": prompt, "gates": gates, **counts(usage)}
    where = path(space)
    where.parent.mkdir(parents=True, exist_ok=True)
    with where.open("a") as f:
        f.write(json.dumps(line) + "\n")
    return line
