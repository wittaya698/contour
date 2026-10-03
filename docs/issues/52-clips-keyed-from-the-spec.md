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

- [ ] The schema documents `clips:` and its fields
- [ ] A clip is keyed onto the armature from the spec alone
- [ ] Wrong length, an unclosed loop and a key pose off tolerance are each red, naming the clip, frame and bone
- [ ] Each of those failures is shown by a fixture

## Blocked by

- [51](51-an-armature-built-from-the-tree.md)
