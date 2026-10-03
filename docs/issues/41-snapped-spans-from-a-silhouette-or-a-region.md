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

- [x] The agent can create a snapped span across or up a silhouette, and across or up one colour's region
- [x] The span's ends are the edges `contour measure` reports for that query, and its stored question re-runs to the same ends
- [x] A colour the reference does not contain is refused, and draws nothing
- [x] On `beaky`'s references, the front silhouette reads 888 across and the side silhouette 597, each within its error bar
- [x] The record has the same shape as slice 40's; nothing that reads a span needs to know which query placed it

## What it came to

`contour measure <ref> --silhouette --extent across|up "what it is"`, or
`--region HEX` in place of `--silhouette`. The ends sit on the pixel edges of
the box `bbox` already reports, with specks ignored: across at its mid-height
and up through its mid-column. So the span reads the report's own `w` or `h`
and never a second number. As in slice 40, any flag the form does not name is
refused, so `--pixel`, `--to`, a stray `--scanline`, or both `--silhouette` and
`--region` at once draw nothing.

The record is slice 40's: it goes through the same `span.pinned`, and the
stored question is `{extent, of, anchor, tol, bg_tol}`, with `of: null` for the
silhouette. Only `--again` looks inside the question, to choose between
re-scanning and re-boxing.

On copies of `beaky`'s references, with the spec height at 1700, the front reads
`888 mm ±3 mm (593 px at 1.498 mm/px)` and the side `597 mm ±3 mm (391 px at
1.526 mm/px)`. Asked again, each says `same ends`. A colour that is not there
(`#00FF00`) is refused, naming its tolerance.

## Blocked by

- [40](40-a-snapped-agent-span-from-a-scanline.md)
