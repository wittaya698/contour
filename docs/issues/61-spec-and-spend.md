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

- [ ] `spec` returns the spec unchanged, followed by the pointer line
- [ ] `spend` returns per-run cost in the same units `tools/tokens.py` uses
- [ ] `spend` on a space with no console runs says so
- [ ] Neither tool writes anything

## Blocked by

- [57](57-the-connector-answers-spaces.md)
