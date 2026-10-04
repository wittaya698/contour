# 52 — Clips keyed from the spec

**Type:** AFK · **Source:** ADR 0023, the spec carries intent as numbers — [a rig and its clips are part of the build](../adr/0023-a-rig-and-its-clips-are-part-of-the-build.md)

## What to build

A spec's `clips:` block is read, keyed onto the armature, and checked.

```yaml
clips:
  walk:
    feel: "toy-like, stiff-legged, on the spot"
    frames: 30
    fps: 30
    loop: true
    keys:
      0:  { leg_L: [25, 0, 0], leg_R: [-25, 0, 0] }
      15: { leg_L: [-25, 0, 0], leg_R: [25, 0, 0] }
    tol_deg: 2
```

Angles are degrees, in the parent's frame, from rest. `loop: true` means the last
frame equals the first; it is not written out as a key.

Checks, each with a fixture that fails it: the clip's length; that a looping clip
closes; every key pose within its tolerance. `feel` is not checked — it is judged
at the checkpoint.

May be split in two if it proves thick: keying with length and loop, then the
key-pose check.

## Acceptance criteria

- [x] The schema documents `clips:` and its fields
- [x] A clip is keyed onto the armature from the spec alone
- [x] Wrong length, an unclosed loop and a key pose off tolerance are each red, naming the clip, frame and bone
- [x] Each of those failures is shown by a fixture

## What it came to

One slice, not two. `kit.rig()` keys every clip the spec names onto an action
and NLA track of its own: a key pose is the whole pose, so a bone a key does
not name is keyed at rest, and a loop's closing frame is key 0 again. The
clip's fps rides on its action, because a saved build carries no scene.

**Axes.** Issue 51's bones stand up +Z, so a bone's own Y is the model's Z and
a key written straight onto a bone would turn y and z about the wrong axes.
The user chose to keep the bones standing and convert: `lib/pose.py` is the
one place that does, both ways — `kit` keys through it in Euler order `XZY`,
which puts each of the spec's angles on a channel of its own, and the gather
reads every bone back off the evaluated pose through it. Because the two
share the conversion, a check passing proves only that they agree, so a
scratch build tested it against geometry: `[90, 0, 0]` tips a part to −Y,
`[0, 90, 0]` to +X, `[90, 0, 90]` to +X, as the model's axes say.

**Rest.** The armature is saved at `pose_position: REST`, so the shape checks,
the sheet and the round-trip see the model as shaped; the gather poses it
only while it reads the clips, one track at a time, and puts it back.

The new check, `clips`, reads each clip's length, fps, whether a loop closes,
and every bone at every key, each angle taken the short way round. The spec
check knows `clips:` and its fields and holds a key to the clip's frames and
to a part; `tol_deg` is required. `feel` is known and checked by nothing.
Clips with no rig are red. Mutants: *clip too short*, *loop left open*, *key
on the wrong axis*; the smoke fixture sways on all three axes. Its first run
found `scene.reset` kept old actions, so a rebuild keyed `sway.001` — reset
now clears actions too.

Left for 54, written there: the export loses the swing and the fps.

## Blocked by

- [51](51-an-armature-built-from-the-tree.md)
