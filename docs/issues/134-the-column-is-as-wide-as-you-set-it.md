# 134 — The column is as wide as you set it

**Type:** AFK · **Source:** design session 2026-10-18

## What to build

The column is meant to be 300 px and has no hard limit: what is in it — the
card's 536 px zoom, a wide transcript line — pushes it out, to half the screen
in the session that found this, and the picture shrinks to make room.

- **A divider between the picture and the column, dragged to set the width.**
  The column's content no longer sets it.
- **Kept per browser**, as a viewer's convenience: another person's layout is
  their own. A width that cannot be read back starts from the default.
- **Bounded:** neither side can be dragged narrower than it is usable at.
- **Double-click puts it back** to the default.
- The card's zoom grows and shrinks with the column.

## Acceptance criteria

- [ ] Dragging the divider sets the column's width, and the picture refits (133)
- [ ] Nothing in the column widens it past what was set
- [ ] A reload keeps the width; a browser that keeps nothing still works
- [ ] Neither side goes below its minimum; double-click restores the default

## Blocked by

None - can start immediately
