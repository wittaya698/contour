# Backlog

Vertical slices waiting to be built. One file per slice, named
`<adr>-<n>-<slug>.md`, each a complete path through every layer rather than one
layer of many.

A slice is **AFK** if it can be implemented and merged without a human in the
loop, and **HITL** if it needs a decision or a visual review that only the user
can give. Prefer AFK.

Delete a file when its slice ships. Git holds the history; this directory holds
what is still outstanding.

## ADR 0018 — Marks: a canvas over the sheet

| Slice | Type | Blocked by |
|---|---|---|
| [0018-7](0018-7-a-ref-mark-aims-contour-measure.md) — A ref mark aims `contour measure` | AFK | — |

0018-1 (the tracer), 0018-2 (close and prune), 0018-3 (the ID mask), 0018-4
(pins and badges), 0018-5 (ref marks) and 0018-6 (agent marks) have shipped;
git holds them. 0018-7 is the last of ADR 0018 and can start now.
