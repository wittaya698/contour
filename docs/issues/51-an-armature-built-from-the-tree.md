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

- [x] A spec with a rig builds an armature with one bone per part, parented as the tree
- [x] Every part is weighted wholly to its own bone
- [x] Every shape check reads the same at rest as without the armature
- [x] A bone count or parent that disagrees with the tree is red, shown by a fixture
- [x] The armature object is not reported as an unexpected part

## What it came to

`kit.rig()`, the last line of a rigged `build.py`, reads the tree from the spec
being built — `cmd_build` hands it over — so the space declares nothing more.
Each bone's head is on its part's origin, which `pivots` already holds to the
seam; every bone points up +Z with no roll, so every bone's rest frame is the
world's, which slice 52's degrees can lean on. Parts are bound by vertex group
and armature modifier but not parented to the rig, so no origin or transform
moves: `smoke` and `beaky` read the same on every shape check as before.

The gather keeps armatures out of `objects`, which ends `parts unexpected:
rig`, and lists them under `rigs`; each part says the bone it is `bound_to`. A
new check, `bones`, holds one rig to the tree — a bone missing, extra or
hanging from the wrong parent, a part not wholly on its own bone, no armature
or two, and an armature where the spec has no rig, which `parts` can no longer
see. Mutants: *bone off the tree*, *extra bone*, *part not weighted*.

The round-trip found one more: re-importing a skinned `.glb` gives each bone a
1 m icosphere to draw it by, measured as a part — origin a metre down, 80
triangles more. It is the importer's and not the model's, so the re-import now
asks for none (`disable_bone_shape`). That is all slice 54 inherits; comparing
the rig itself across the file is still its job.

`beaky` (in its own space): `bones 14/14`, every other reading unchanged, and
its export round-trips 14/14.

## Blocked by

- [47](47-bones-without-operators.md)
- [49](49-seams-and-pivots-measured-at-rest.md)
