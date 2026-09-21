# 0018-5 — Ref marks: annotate the references

**Type:** AFK · **Status:** ready

## Parent

[ADR 0018 — Marks: a canvas over the sheet, and a shared way to point](../adr/0018-marks-a-canvas-over-the-sheet.md)

## What to build

The second mark type, and the one that motivated the ADR.

The canvas serves the space's references alongside the sheet. A mark placed on a
reference carries pixel coordinates and the user's words alone — nothing in a
photograph knows what a part is — and it needs no anchoring machinery, because a
reference never changes. Rule 1 guarantees that, which makes the cheap storage
correct exactly where the machinery is absent.

The two types mean different things and must be distinguishable at a glance. A
sheet mark says *the build is wrong* and resolves against a build. A ref mark
says *here is what I meant*; no build can ever close one. It is answered by a
measurement or by a spec revision, both of which happen elsewhere.

Nothing under the references directory is written. Marks about a reference live
in the space's marks file, like every other mark.

## Acceptance criteria

- [ ] The canvas lists and serves every image in the space's references directory
- [ ] A click on a reference creates a mark carrying the image, the pixel and the text
- [ ] A ref mark carries no part and is never sent for ray resolution
- [ ] Sheet marks and ref marks are visually distinct in the canvas
- [ ] No build outcome, green or red, can close a ref mark
- [ ] Nothing under the references directory is created, modified or deleted
- [ ] Ref marks count toward the `n marks open` line alongside sheet marks
- [ ] Ref mark coordinates survive a rebuild unchanged

## Blocked by

- [0018-1](0018-1-tracer-a-mark-lands-and-check-reports-it.md)
