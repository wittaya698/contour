# 38 — Create a variation of a space

**Type:** AFK · **Source:** [ADR 0021](../adr/0021-the-lobby.md) decision 4

## What to build

A *variation of this* action on each row of the **lobby**. A variation is a new
space, never a copy (ADR 0015; `beaky-lite`, `-fable` and `-solo` were all made
this way). So this is slice 37's create, with one difference: the first prompt
points the agent at the source space's `spec.yaml` and `build.py` **for
reference**.

Nothing is copied: not the spec, not `build.py`, not `refs/`. Reference images the
variation needs are brought in by the user in its own run. A copied spec would
arrive already agreed to, and the variation's contract has to be confirmed as its
own.

## Acceptance criteria

- [ ] The new space contains exactly what `contour init` makes, and nothing from the source
- [ ] The console's first prompt names the source space and its `spec.yaml` and `build.py` paths, as reference
- [ ] The source space is not modified, and gets no presence from the new console
- [ ] The default name suggests `<source>-` and must still be edited to something new

## Blocked by

- [37](37-create-a-space-from-the-lobby.md)
