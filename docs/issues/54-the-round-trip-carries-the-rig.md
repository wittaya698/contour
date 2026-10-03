# 54 — The round-trip carries the rig

**Type:** AFK · **Source:** ADR 0023, what is checked, on export — [a rig and its clips are part of the build](../adr/0023-a-rig-and-its-clips-are-part-of-the-build.md)

## What to build

`contour export` re-imports the `.glb` and re-measures it (ADR 0006). With a rig,
it also compares:

- **counts** — bones, clips, frames per clip;
- **where every part ends up** — the world-space corners of each part's bounding
  box at every key and at frames between keys, `.glb` against `.blend`, within a
  tolerance in mm.

Not angles. The glTF importer re-orients bones, so a correct file can come back
with different numbers on a differently-oriented bone; comparing angles would be
red on a correct export. Angles check intent against the spec; positions check
fidelity against the build.

## Acceptance criteria

- [ ] A rigged export reports bone, clip and frame counts against the build
- [ ] Part corners are compared at keys and between them, and a mismatch is red with the part, frame and distance
- [ ] A correct export with re-oriented bones is green
- [ ] A fixture export that is wrong in position (mirrored, or mis-scaled) is red

## Blocked by

- [52](52-clips-keyed-from-the-spec.md)
