# 0018-4 — Anchor marks in part-local space, and re-project them onto every new sheet

**Type:** HITL · **Status:** ready

## Parent

[ADR 0018 — Marks: a canvas over the sheet, and a shared way to point](../adr/0018-marks-a-canvas-over-the-sheet.md)

## What to build

Pins that survive a rebuild, and pins you can see.

The sheet is regenerated on every build, so a mark stored in pixels starts lying
the moment geometry moves — and looks authoritative while doing it. Instead, a
sheet mark is born unresolved and carries its pixel only until it can be
anchored properly.

Once per canvas session — not per click, not per build — a single Blender run
casts one ray per unresolved mark from that sheet's camera through its pixel and
writes back the surface point in the hit part's own coordinates.
`Scene.ray_cast` returns location, normal, index and object together, confirmed
against `contour api`, so no position buffer is rendered and nothing is stored
beyond the camera parameters of each sheet. Move a part and its pins move with
it; resize it and they stay on the same spot; delete it and its pins are
explicitly orphaned rather than quietly misplaced.

The ray must hit the geometry the sheet was rendered from. Resolving at session
close normally keeps that window shut, but if the build has moved on since the
sheet was made, the canvas refuses to resolve and says so. It must never guess.

`contour render` then draws resolved marks as badges at their re-projected
positions, painted only over background pixels in the same manner as the
existing grid and rulers, so a rebuilt sheet shows where the open questions are.

**Expect this slice to overrun** — it carries anchoring, the stale-sheet
refusal, and badge rendering together. They are kept whole because anchoring you
cannot see is not demoable and badges with nothing anchoring them are fiction.
If it does overrun, the clean cut is to ship the resolution pass and let badges
follow.

## Acceptance criteria

- [ ] Each sheet records the camera parameters needed to reconstruct its rays
- [ ] At session close, one Blender run resolves every unresolved mark
- [ ] A resolved mark stores the surface point in the hit part's local coordinates
- [ ] Moving, rotating or resizing a part moves its pins with it
- [ ] Deleting a part marks its pins orphaned, visibly, rather than drawing them somewhere wrong
- [ ] Resolution refuses, with a clear message, when the geometry has changed since the sheet was rendered
- [ ] Resolution costs one Blender startup per session, not one per mark and not one per click
- [ ] `contour render` draws resolved marks as badges at their re-projected positions
- [ ] Badges paint only over background pixels and never obscure geometry
- [ ] Badges stay legible at the sheet's per-tile resolution
- [ ] A ref mark is untouched by all of this — it is pixel-stable by definition

## Blocked by

- [0018-3](0018-3-a-click-knows-its-part.md)
