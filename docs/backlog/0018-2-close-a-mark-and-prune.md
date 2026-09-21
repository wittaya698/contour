# 0018-2 — Close a mark from the page, and prune closed ones

**Type:** AFK · **Status:** ready

## Parent

[ADR 0018 — Marks: a canvas over the sheet, and a shared way to point](../adr/0018-marks-a-canvas-over-the-sheet.md)

## What to build

The lifecycle half of a mark. In the canvas, a mark can be closed by the user in
one action. A closed mark renders differently from an open one and stops
counting toward the `n marks open` line.

Only the user closes a mark. Nothing else in the pipeline may close one — not a
green check, not the agent, not a rebuild. ADR 0018 rejects auto-closing
outright: a mark exists precisely because the spec did not catch the thing, so
green would erase the findings that matter most.

Closed marks older than the last release tag are pruned from the file when the
canvas runs; git holds the archive. Open marks are never pruned, at any age.

## Acceptance criteria

- [ ] A mark can be closed from the page in a single action, with no typing required
- [ ] A closed mark is visibly distinct from an open one
- [ ] Closed marks are excluded from the `n marks open` count
- [ ] No command path other than the user's action can move a mark to closed
- [ ] A passing `contour check` leaves every mark's status untouched
- [ ] Closed marks older than the last release tag are dropped when the canvas runs
- [ ] Open marks are never pruned regardless of age
- [ ] Pruning is a no-op in a space with no release tag

## Blocked by

- [0018-1](0018-1-tracer-a-mark-lands-and-check-reports-it.md)
