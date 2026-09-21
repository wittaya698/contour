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
| [0018-1](0018-1-tracer-a-mark-lands-and-check-reports-it.md) — Tracer: click the sheet, a mark lands, `check` reports it | **HITL** | — |
| [0018-2](0018-2-close-a-mark-and-prune.md) — Close a mark from the page, and prune closed ones | AFK | 0018-1 |
| [0018-3](0018-3-a-click-knows-its-part.md) — A click knows its part: the ID mask and hover | AFK | 0018-1 |
| [0018-4](0018-4-anchor-in-part-local-space-and-reproject.md) — Anchor marks in part-local space, and re-project them | **HITL** | 0018-3 |
| [0018-5](0018-5-ref-marks.md) — Ref marks: annotate the references | AFK | 0018-1 |
| [0018-6](0018-6-agent-authored-marks.md) — Agent-authored marks | AFK | 0018-1, 0018-2 |
| [0018-7](0018-7-a-ref-mark-aims-contour-measure.md) — A ref mark aims `contour measure` | AFK | 0018-5, 0018-6 |

0018-1 is the tracer bullet. Once it lands, 0018-2, 0018-3 and 0018-5 are all
unblocked at the same time.
