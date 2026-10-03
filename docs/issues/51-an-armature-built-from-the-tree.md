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

Slice 47 found bones are made in edit mode, entered and left by the whitelisted
`object.mode_set` through `lib.ctx_override`, with the rig made the active object
through the data API; the bind itself — vertex groups, the armature modifier — is
all data API. See ADR 0023's evidence.

The armature is an object, and verify counts every object as a part: the probe
went red on `parts unexpected: rig`. The rig's object is recognised as the rig,
not as an undeclared part.

## Acceptance criteria

- [ ] A spec with a rig builds an armature with one bone per part, parented as the tree
- [ ] Every part is weighted wholly to its own bone
- [ ] Every shape check reads the same at rest as without the armature
- [ ] A bone count or parent that disagrees with the tree is red, shown by a fixture
- [ ] The armature object is not reported as an unexpected part

## Blocked by

- [47](47-bones-without-operators.md)
- [49](49-seams-and-pivots-measured-at-rest.md)
