# 51 — An armature built from the tree

**Type:** AFK · **Source:** ADR 0023, the bind — [a rig and its clips are part of the build](../adr/0023-a-rig-and-its-clips-are-part-of-the-build.md)

## What to build

From a spec's rig, the build makes an armature: one bone per part, its head on
that part's pivot, parented as the tree says, and each part's vertices weighted
wholly to its own bone. Rigging lives in the toolkit; a space's `build.py` asks
for it and declares nothing more than the spec already does.

The rest pose is the model as shaped, so every shape check is unchanged and still
measures at rest. Verify adds that the bones match the tree: one per part, the
same parents.

Built however slice 47 found bones can be made — or as node animation, if 47
amended the ADR.

## Acceptance criteria

- [ ] A spec with a rig builds an armature with one bone per part, parented as the tree
- [ ] Every part is weighted wholly to its own bone
- [ ] Every shape check reads the same at rest as without the armature
- [ ] A bone count or parent that disagrees with the tree is red, shown by a fixture

## Blocked by

- [47](47-bones-without-operators.md)
- [49](49-seams-and-pivots-measured-at-rest.md)
