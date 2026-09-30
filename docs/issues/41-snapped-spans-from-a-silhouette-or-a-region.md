# 41 — Snapped spans from a silhouette or a region

**Type:** AFK · **Source:** ADR 0022 decisions 2, 4 — [the agent reads the references in spans](../adr/0022-the-agent-reads-the-references-in-spans.md)

## What to build

Slice 40 snaps a span to the runs of a scanline. The other two things
`contour measure` finds are extents: of the whole figure against the background,
and of one colour. This slice lets the agent draw a span across either.

The agent names the measurement — the silhouette, or a colour — and which extent
it means: across, or up. `contour measure` places the ends on the edges it found
and writes a **snapped** agent span, with its question stored and its answer
pinned back, exactly as slice 40 does.

ADR 0017 found that a naive bounding box is unusable on a JPEG: compression
specks moved `beaky`'s depth from 597 to 1300. The extent a span snaps to is the
one `contour measure` already reports, specks ignored, and not a second reading.

## Acceptance criteria

- [ ] The agent can create a snapped span across or up a silhouette, and across or up one colour's region
- [ ] The span's ends are the edges `contour measure` reports for that query, and its stored question re-runs to the same ends
- [ ] A colour the reference does not contain is refused, and draws nothing
- [ ] On `beaky`'s references, the front silhouette reads 888 across and the side silhouette 597, each within its error bar
- [ ] The record has the same shape as slice 40's; nothing that reads a span needs to know which query placed it

## Blocked by

- [40](40-a-snapped-agent-span-from-a-scanline.md)
