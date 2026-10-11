# 119 — A release carries its topics

**Type:** AFK · **Source:** ADR 0030, decision 9 — [topics label a model for finding](../adr/0030-topics-label-a-model-for-finding.md)

## What to build

The `.glb` in `release/v<N>/` carries the model's topics as they stood at
release, as glTF `extras` on the root, and keeps them. A working `contour
export` carries none. `contour release` is not built, so this extends
`release-model`'s steps; when the command lands it inherits the same.

## Acceptance criteria

- [ ] A release made with topics `creature`, `bird` has both in its `.glb`, read back after round-trip
- [ ] A working export of the same model has no topics in it
- [ ] Approving `forest` afterwards changes nothing in `release/v1/`
- [ ] Changing a topic turns no check red and asks for no release

## Blocked by

- [113](113-a-release-tag-is-v-n.md)
- [114](114-a-space-carries-its-approved-topics.md)
