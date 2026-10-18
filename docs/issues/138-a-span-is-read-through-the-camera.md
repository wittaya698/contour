# 138 — A span is read through the camera

**Type:** AFK · **Source:** ADR 0032, decisions 1, 2, 4 and 5 — [a span is measured through the camera](../adr/0032-a-span-is-measured-through-the-camera.md)

## What to build

The arithmetic alone, in `lib/`, with no page and no Blender: from a
reference's answered directions and its anchor span, a span's millimetres and
its `±`.

- **Directions to a camera.** Each direction's lines meet at a point; three
  square directions give the lens and the camera's turn. Parallel lines, which
  meet nowhere, are a straight-on direction and need no special case.
- **A span along a direction, against the anchor, through a tie.** Along the
  anchor's own direction with one direction known, or along any of three square
  ones once the camera is recovered, but only where the span is tied to the
  anchor: an end shared with it or with a span already read, or a plane through
  it. Along no direction, along one the camera cannot scale, or tied to nothing,
  it returns why and no number.
- **The `±` is a spread.** Every line and both span ends moved a pixel each way,
  the span read again; the widest pair is the bar.
- **Tested against known answers:** renders of a box of known size from known
  cameras, straight on and steep, read back within their own `±`.

## Acceptance criteria

- [ ] A box rendered straight on reads its edges back within `±`, as the old scale did
- [ ] The same box rendered at a steep three-quarter view reads its edges back within `±`
- [ ] A steeper view earns a wider `±`
- [ ] A diagonal span, or one along an unscalable direction, gives no number and says which direction it needs
- [ ] A box edge at another depth from the anchor, tied to it by a shared corner, reads back within `±`; the same edge with its corner untied gives no number and says what would tie it
- [ ] Nothing in it imports `bpy`; `test_lib_split` lists it as free

## Blocked by

- 137
