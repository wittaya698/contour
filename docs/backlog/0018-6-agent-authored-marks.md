# 0018-6 — Agent-authored marks

**Type:** AFK · **Status:** ready

## Parent

[ADR 0018 — Marks: a canvas over the sheet, and a shared way to point](../adr/0018-marks-a-canvas-over-the-sheet.md)

## What to build

The return path the ADR was written for: the agent's findings arrive as badges
on the picture instead of paragraphs nobody reads.

The agent writes marks with `author: agent` — check deltas, `contour measure`
readings, the parts it is unsure of — and the canvas renders them distinctly
from the user's own. The agent may attach *addressed in build N* to any mark,
which dims it, but that is not a close: the finding stands until the user closes
it.

The discipline is part of the feature, not a guideline beside it: **a mark is a
question or a measurement, never narration.** A canvas that fills with the agent
describing what it did is a canvas the user stops opening.

An agent mark is never a spec edit. Rule 1 is untouched — propose, the user
confirms, then write with `revision:` bumped. The canvas makes a proposal
visible; it does not become the gate.

## Acceptance criteria

- [ ] The agent can append a mark carrying `author: agent`
- [ ] Agent marks are visually distinct from user marks in the canvas
- [ ] The agent can attach an *addressed in build N* note, which dims the mark
- [ ] That note does not close the mark and does not remove it from the open count
- [ ] No agent path can set a mark's status to closed
- [ ] Writing a mark never writes the spec, and never writes anything under the references directory
- [ ] Agent marks are subject to the same pruning rule as user marks

## Blocked by

- [0018-1](0018-1-tracer-a-mark-lands-and-check-reports-it.md)
- [0018-2](0018-2-close-a-mark-and-prune.md)
