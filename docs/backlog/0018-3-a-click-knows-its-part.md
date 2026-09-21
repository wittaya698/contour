# 0018-3 — A click knows its part: the ID mask and hover

**Type:** AFK · **Status:** ready

## Parent

[ADR 0018 — Marks: a canvas over the sheet, and a shared way to point](../adr/0018-marks-a-canvas-over-the-sheet.md)

## What to build

Part identity, so a mark addresses a named part rather than a coordinate.

`contour render` emits a per-view identity mask alongside the sheet: a second
Workbench pass with `shading.color_type = 'OBJECT'` and each object's `color`
set to a unique index, so a pixel *is* a part number, occlusion included. The
mask lands in the space's git-ignored output directory and is regenerated on
every build, like everything else there.

The canvas reads the mask to answer two questions. On hover, it names the part
under the cursor — this must be instant and purely local, which is why the mask
exists rather than a Blender call per mouse-move. On click, the new mark carries
the part name.

Nearest-centroid was rejected in ADR 0018: it snaps a click on the beak to the
head whenever the head's centroid is nearer in screen space, and it turns a
click on empty background — *this gap is too wide* — into a comment on an
arbitrary neighbour. A click on background must carry no part at all.

`bpy.types.View3DShading.color_type` accepts `OBJECT` and `bpy.types.Object.color`
exists on this Blender, both confirmed against `contour api`.

## Acceptance criteria

- [ ] `contour render` emits one identity mask per view into the git-ignored output directory
- [ ] Every object in the build has a distinct index in the mask
- [ ] Hover names the part under the cursor, with no network or Blender call per movement
- [ ] A click on a part records that part's name on the mark
- [ ] A click on background records no part, and does not snap to a nearby one
- [ ] An occluded part is never reported for a pixel it does not own
- [ ] The extra passes run inside the existing Blender process, paying no second startup
- [ ] The mask never reaches the conversation — it is read from disk by the server
- [ ] Marks made before this slice, which carry no part, still load and display

## Blocked by

- [0018-1](0018-1-tracer-a-mark-lands-and-check-reports-it.md)
