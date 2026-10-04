# 56 — `beaky` walks, and ADR 0023 is accepted

**Type:** HITL · **Source:** ADR 0023, the tracer bullet — [a rig and its clips are part of the build](../adr/0023-a-rig-and-its-clips-are-part-of-the-build.md)

## What to build

`beaky` gets an on-the-spot `walk`, and ADR 0023 gets its verdict.

The agent proposes `revision: 2`: the `walk` clip — legs ±25° about X in opposite
phase, each arm ±20° opposite its own leg, 30 frames at 30 fps, looping — with its
key-pose angle tolerance and seam-growth tolerance, every number flagged as the
agent's, tolerances loudest. The user confirms before it is written.

Then: green on every check, exported and round-tripped, and the user looks at the
filmstrip. **Accept, amend or withdraw** ADR 0023 on what that shows.

Things this may turn up, which would amend rather than withdraw:
- a stiff-legged walk with no knee reads wrong, and the rig needs a part `beaky`
  does not have;
- the seam-growth check is too noisy to be a check;
- degrees per bone are too heavy to write for anything beyond a cycle.

## Acceptance criteria

- [x] The user confirmed `revision: 2` and its tolerances before it was written
- [x] `contour check` and `contour export` are green on `beaky`
- [x] The user has seen the filmstrip of that build
- [x] ADR 0023's status says accepted, amended or withdrawn, with the evidence

## Blocked by

- [50](50-beaky-gets-its-rig.md)
- [53](53-no-part-enters-another.md)
- [54](54-the-round-trip-carries-the-rig.md)
- [55](55-the-filmstrip.md)

## What it came to

Accepted, 2026-10-04. The user confirmed revision 2 as proposed; the first build
was green, export and round-trip green, and the user approved the filmstrip and
the `.glb` played in Blender. Evidence and the two limitations it found (ground
contact unchecked; the front row says little of a walk) are in ADR 0023.
