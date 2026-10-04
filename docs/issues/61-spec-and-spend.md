# 61 — `spec` and `spend`

**Type:** AFK · **Source:** ADR 0024, decisions 3 and 4 — [the connector: Desktop reads and opens, never drives](../adr/0024-the-connector-desktop-reads-and-opens.md)

## What to build

Two connector tools that read.

`spec` returns a space's `spec.yaml` as text, and ends with one line: a spec
changes only inside a space, argued from a span the user can see on the canvas.
That line is what turns a chat arguing for a new tolerance into a chat sending the
user to draw a span.

`spend` returns what the console's runs in that space cost, from its
`spend.jsonl`, in the units `tools/tokens.py` reports. A space no console has run
in says so.

## Acceptance criteria

- [x] `spec` returns the spec unchanged, followed by the pointer line
- [x] `spend` returns per-run cost in the same units `tools/tokens.py` uses
- [x] `spend` on a space with no console runs says so
- [x] Neither tool writes anything

## What it came to

`spec` returns the file's text as one plain text block, not a JSON string,
followed by a blank line and the instructions' second line, read from
`connector.INSTRUCTIONS` so the two cannot drift apart. `contour init` writes no
spec, so a space without one says *no spec.yaml yet* above the same pointer.

`spend` needed the reading half of the accounting below the console, which the
launcher may never import. That half (`NAME`, the figures and multipliers,
`counts`, `thinking`, `load`, `weigh`) moved to `lib/spend.py`, together with
`runs`, the per-run grouping that used to live in `tools/tokens.py`'s
`console_runs`. `console/spend.py` keeps the one write (`record`) and `total`,
and imports the rest. `tools/tokens.py` reads through `lib/spend.py`, so a run's
row in a chat is its row in `tokens.py --json`, figure for figure; the test
compares the two. A space with no runs says *no console has run here*.

That neither tool writes is tested by every file's bytes and mtime before and
after, and the test was checked by planting a write.

## Blocked by

- [57](57-the-connector-answers-spaces.md)
