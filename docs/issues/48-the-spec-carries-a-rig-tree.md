# 48 — The spec carries a rig tree

**Type:** AFK · **Source:** ADR 0023, the spec carries intent as numbers — [a rig and its clips are part of the build](../adr/0023-a-rig-and-its-clips-are-part-of-the-build.md)

## What to build

A spec states its **rig** as a `parent:` on each `parts:` entry: the name of the
part it hangs from. Part names are written once, so the tree cannot disagree with
the part list.

```yaml
parts:
  - { name: torso,  count: 1 }                 # no parent: the root
  - { name: neck,   count: 1, parent: torso }
  - { name: arm_L,  count: 1, parent: neck }
```

The schema says so, and verify checks it: exactly one part has no parent; every
parent names a part; the tree has no cycle. A spec with no `parent:` anywhere has
no rig, and nothing here applies to it, so every existing space stays green
without a revision.

As every check must (ADR 0009), each of these has a fixture spec that fails it.

## Acceptance criteria

- [ ] The schema documents `parent:` on a part
- [ ] A spec with no `parent:` at all builds and verifies exactly as before
- [ ] Two roots, an unknown parent and a cycle are each red, with one line naming the part
- [ ] Each of those failures is shown by a fixture, so the check proves it can fail

## Blocked by

None - can start immediately.
