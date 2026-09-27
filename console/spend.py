"""What a run cost, per turn (ADR 0019, decision 32).

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

Above `lib/` for the veto store's reason: a run is the console's own knowledge.
No `contour` subcommand has a turn to account for.
"""
import json
from datetime import datetime, timezone

NAME = "spend.jsonl"
"""One line per turn, appended, in the space's own `.contour/`.

Appended rather than rewritten so a run that dies mid-turn still accounts for the
turns it had already spent — the figure exists to be trusted, and a total that
loses whatever came before a crash is the one that flatters.
"""


def counts(usage):
    """One turn's usage, in the words `tools/tokens.py` counts in.

    The SDK's own keys are the API's, and the accounting's are shorter. Named
    here, once, so the reader never has to know two spellings for one number.
    """
    usage = usage or {}
    return {"input": usage.get("input_tokens", 0) or 0,
            "cache_read": usage.get("cache_read_input_tokens", 0) or 0,
            "cache_write": usage.get("cache_creation_input_tokens", 0) or 0,
            "output": usage.get("output_tokens", 0) or 0}


def path(space):
    return space / ".contour" / NAME


def load(space, run=None):
    """Every recorded turn, oldest first; one run's, if a run is named."""
    where = path(space)
    if not where.exists():
        return []
    lines = []
    for line in where.read_text().splitlines():
        if not line.strip():
            continue
        try:
            turn = json.loads(line)
        except json.JSONDecodeError:
            continue           # a line half-written when something died
        if run is None or turn.get("run") == run:
            lines.append(turn)
    return lines


FIGURES = ("input", "cache_read", "cache_write", "output")

# Anthropic's cache pricing, relative to a fresh input token, and output's
# premium over one. Here rather than in `tools/tokens.py`, which imports them:
# the page and the accounting must not each hold an opinion about what a turn
# cost, or a run would be two prices depending on where it was read.
CACHE_READ_MULT = 0.10
CACHE_WRITE_MULT = 1.25
OUTPUT_MULT = 5.0


def weigh(figures):
    """The four figures as one comparable number — relative units, never dollars.

    A gated run is mostly cache reads, and four columns is not something a person
    watching a run can add up in their head; this is the column they can.
    """
    return round(figures.get("input", 0)
                 + figures.get("cache_read", 0) * CACHE_READ_MULT
                 + figures.get("cache_write", 0) * CACHE_WRITE_MULT
                 + figures.get("output", 0) * OUTPUT_MULT)


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
    rather than an irritated one (ADR 0019, decision 32).
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
