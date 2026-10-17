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

## Acceptance criteria

- [ ] A spec whose only size is a width gives millimetres once its anchor span is answered
- [ ] A reference with no answered anchor span reports pixels and names what it waits on
- [ ] No millimetre anywhere comes from the foreground box

## Blocked by

- 138
