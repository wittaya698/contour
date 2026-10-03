# 47 — Bones without operators, probed on 5.2.1

**Type:** HITL · **Source:** ADR 0023, the probe — [a rig and its clips are part of the build](../adr/0023-a-rig-and-its-clips-are-part-of-the-build.md)

## What to build

ADR 0023 binds each part to a bone of a real armature, and that needs bones to be
created headless. `contour api` confirms `Armature.edit_bones.new(name)` exists on
5.2.1, but in every Blender the agent knows, `edit_bones` is empty outside edit
mode, and entering edit mode is `bpy.ops.object.mode_set` — not in the whitelist.

Find out which of three is true on this Blender, in a build and not by recall:

1. bones can be made through the data API alone;
2. they can be made with one `object.mode_set`, called through `lib.ctx_override`
   and nothing else;
3. neither — it needs more operators, or edit mode does not work headless.

The answer is recorded under ADR 0023 as evidence, the way ADR 0022 records its
bullet. Under 1 nothing changes. Under 2 the whitelist gains one line with its
reason, and the user signs that line off before it lands — that is what makes this
slice HITL. Under 3 ADR 0023 is amended to its fallback, node animation, and slice
51 is rewritten to build that instead of an armature.

The probe runs in a scratch build, never in `beaky`.

## Acceptance criteria

- [x] Which of the three holds on 5.2.1 is shown by a build that ran, and its result is recorded under ADR 0023
- [x] If the whitelist gains `object.mode_set`, the user has approved that line and its reason before it lands
- [x] If neither works, ADR 0023 and slice 51 say node animation instead
- [x] No `bpy.ops` call outside the whitelist was made to find out

## What it came to

The second of the three. `edit_bones.new` outside edit mode raises, and
`Armature.bones` has no `new()`, so the data API alone cannot make a bone. One
`object.mode_set`, through `lib.ctx_override.call` with the rig made active by the
data API, makes them — no change to `ctx_override`. A rigid bind built all through
the data API follows a posed bone. The numbers are under ADR 0023's evidence.

The whitelist's fourth line was approved by the user before the call that used it.
Node animation is not needed; slice 51 builds an armature, and now also owns the
probe's one red, `parts unexpected: rig`.

## Blocked by

None - can start immediately.
