# 139 — The anchor is a span

**Type:** AFK · **Source:** ADR 0032, decision 3 — [a span is measured through the camera](../adr/0032-a-span-is-measured-through-the-camera.md)

## What to build

`span.anchor_mm` reads only `dimensions.height` and `Scale` divides it by the
foreground box's height. `nexus-probe` states a *width*, so every span there
was pixels only.

- **The anchor is whichever one real dimension the spec states**, with the span
  on each reference that it is the length of.
- **The span is an agent span** proposed for that, with the dimension it claims
  to be (*is this the width you told me, 300 mm?*), answered as any other.
- **Until it is answered the reference reports pixels**, as now, and says why.
- **The foreground box sets no scale.** `contour measure`'s silhouette queries
  keep their pixels; their millimetres come through 138.

## What was built

- **`--claims DIM` on any span form** draws the anchor span: refused unless
  the spec states that size, any one of them (`span.claimed`). The span keeps
  the millimetres it claims and the picture's size, and its reading is the
  question, *is this the width you told me, 300 mm? (612 px)*.
- **`span.through` reads every span**: drawn, `--span ID`, and corrected on
  the canvas. From the marks alone, through `camera.read`, once the
  reference's anchor span and directions are adopted or corrected; else
  pixels, naming what they wait on (no anchor span, the anchor span
  unanswered, no direction answered) or the camera's own refusal.
- **No millimetre from the foreground box.** `--anchor` is refused by the
  launcher, before Blender starts; `span.anchor_mm` is gone; every query
  report is in pixels. A correction no longer reads at the scale a span
  kept, which came from the box. `--again` still places an old question's
  row from the anchor it was asked with, as a position and never a length.
- Checked under Blender on a painted box with a width-only spec: before the
  answers a span read `114 px (waits on m4, the anchor span, being answered)`;
  after, `196 mm ±19 mm` for an edge 200 mm long.

## Acceptance criteria

- [x] A spec whose only size is a width gives millimetres once its anchor span is answered
- [x] A reference with no answered anchor span reports pixels and names what it waits on
- [x] No millimetre anywhere comes from the foreground box

## Blocked by

- 138
