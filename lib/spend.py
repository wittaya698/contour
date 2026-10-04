"""What the console's runs cost, read (ADR 0019, decision 37; ADR 0024, decision 3).

The reading half of the spend accounting, below the console so the connector can
ask it: the launcher may never import the console. `console/spend.py` is still
the only writer of `spend.jsonl` — a run is the console's own knowledge, and no
`contour` subcommand has a turn to account for — and the page, `tools/tokens.py`
and a chat all read it through here, so a run is one price wherever it is read.
"""
import json

from . import space as space_lib

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


def thinking(usage):
    """How much of one turn's output was thought rather than said.

    Not one of `FIGURES` — the console does not record it, because the page
    weighs what a turn cost and thinking is already inside `output`. It is named
    here for the other reason `counts` exists: this is where the SDK's own
    spelling is kept, and the accounting must not hold a second copy of it. The
    details block is absent on a turn that did none, so *no thinking* and *no
    such key* are the same answer, which is zero and never a crash.
    """
    details = (usage or {}).get("output_tokens_details") or {}
    return details.get("thinking_tokens", 0) or 0


def path(space):
    """The layout says where a space's `.contour` is; the name is this
    module's own (slice 17)."""
    return space_lib.layout(space).dot / NAME


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


def runs(space):
    """Every run in this space, oldest first, as one row each: its prompt, when
    it began, its turns and the sum of each figure, the gates it stopped at and
    what the turns after one cost, and the weighted total.

    A run is one prompt and every turn it caused, which is what `tools/tokens.py`
    has always called an iteration, so this is its row for a console run.
    """
    out = {}
    for turn in load(space):
        it = out.setdefault(turn.get("run", "?"), {
            "run": turn.get("run", "?"),
            "prompt": turn.get("prompt") or turn.get("run", "?"),
            "at": turn.get("at", ""), "turns": 0,
            **{k: 0 for k in FIGURES},
            # How many gates the run stopped at, and what the turns after one
            # cost. A gate buys a turn of re-explanation, and this is the figure
            # that makes tuning the ask-list a decision rather than a mood.
            "gates": 0, "after_gates": 0,
        })
        it["turns"] += 1
        for k in FIGURES:
            it[k] += turn.get(k, 0)
        it["gates"] = max(it["gates"], turn.get("gates", 0))
        if turn.get("gates", 0):
            it["after_gates"] += weigh(turn)
    for it in out.values():
        it["weighted"] = weigh(it)
    return list(out.values())
