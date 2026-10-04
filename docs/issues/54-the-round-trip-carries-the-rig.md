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

## Found by 52

A probe exported a keyed clip and read the `.glb` back. Two things to fix here:

- **The swing is lost.** The build saves the armature at `pose_position:
  REST`, and the exporter samples the pose it sees: a 30°/−30°/30° swing
  came out as two samples of a still pose. Export must pose the armature.
- **The fps is lost.** A saved build is one collection and no scene, so
  export runs at Blender's 24 fps: a 30-frame clip came out 1.25 s long. Each
  clip's fps is on its action as `fps`, which `kit` writes and `clips` checks.

## Acceptance criteria

- [ ] A rigged export reports bone, clip and frame counts against the build
- [ ] Part corners are compared at keys and between them, and a mismatch is red with the part, frame and distance
- [ ] A correct export with re-oriented bones is green
- [ ] A fixture export that is wrong in position (mirrored, or mis-scaled) is red

## Blocked by

- [52](52-clips-keyed-from-the-spec.md)
