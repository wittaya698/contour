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

- [x] A rigged export reports bone, clip and frame counts against the build
- [x] Part corners are compared at keys and between them, and a mismatch is red with the part, frame and distance
- [x] A correct export with re-oriented bones is green
- [x] A fixture export that is wrong in position (mirrored, or mis-scaled) is red

## What it came to

**Both 52 findings are fixed in `contour export`.** It poses the armature
before exporting and sets the scene to the clips' rate, read from each
action's `fps`. It exports one glTF animation per NLA track. A probe on the
smoke fixture measured the difference. Exported at rest, the plinth stood
37 mm from the build at frame 10. Exported posed, every part stood within
0.00003 mm of the build at every frame. Clips at two rates cannot share one
file, so the export refuses them and names each clip with its fps
(`checks.one_rate`).

**Counts come from the file and positions from the re-import.**
`glb.measure` counts the skins' joints and reads each animation's length in
seconds, without Blender. That reading is needed because the importer
converts seconds to frames at whatever rate the importing scene has, so a
re-import alone cannot see a wrong fps. `gl_rig` turns each length into
frames at the build's fps (`sway runs 16.0f at 24fps in the file, built
20f`). `re_motion` re-imports the file at the build's rate. It compares
every part's world box at every frame of every clip with the build's. Each
part is named once, at its worst frame (`sway f10: plinth 42.4mm from the
build, past 0.1mm`). Every frame covers both the keys and the frames between
them. On a pass, the report line adds `rig 3 bones, sway 20f kept`.

**The importer lays its strip one frame late.** It puts the NLA strip at
frame 1, over an action keyed from 0. The gather now reads a clip from the
frame its strip starts on, for as long as its action runs. The build's own
reading is unchanged, because `kit` lays the strip at 0. The re-import now
holds its rig at rest, as the build does, so the shape checks still measure
the model as shaped.

`roundtrip_mm` is per clip and required, by the user's choice. The smoke
fixture's 0.1 is the agent's number, kept well above the 0.00003 mm
measured. The round-trip has five new mutants, each checked to be caught by
its own rule:

- exported at rest, caught by `re_motion`;
- exported at 30 fps, caught by `gl_rig`;
- the file mirrored in X, caught by `re_motion`; at rest the fixture is
  symmetric, but the plinth's 8° turn about Y is not;
- the file in millimetres, caught by `re_motion`;
- the real file read back with the `TEMPERANCE` bone heuristic. Every bone
  then points down, and the mutant must stay green.

## Blocked by

- [52](52-clips-keyed-from-the-spec.md)
