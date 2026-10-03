# 50 — `beaky` gets its rig

**Type:** HITL · **Source:** ADR 0023, consequences — [a rig and its clips are part of the build](../adr/0023-a-rig-and-its-clips-are-part-of-the-build.md)

## What to build

Run slice 49's checks on `beaky`, and make them green.

The spec changes first, under rule 1: the agent proposes `revision: 1` — a
`parent:` on each part, in the tree below, and the origin-to-pivot tolerance,
flagged as the agent's and loudest — and the user confirms before anything is
written.

```
torso (root)
├─ neck
│  ├─ head ── beak, eye_L, eye_R
│  ├─ arm_L ── hand_L
│  └─ arm_R ── hand_R
├─ leg_L ── shoe_L
└─ leg_R ── shoe_R
```

Then `build.py` is fixed, not the spec. By arithmetic over its constants, before
any build: the head has no seam (its bottom and the neck's top are both at
z 1310), and four origins are off their pivots — neck by ~137 mm, hands ~73,
legs ~34, arms ~27. A build's numbers outrank this arithmetic.

The spec already says *pivot at its joint*; the seam is what makes that precise,
so no other spec line moves.

## Acceptance criteria

- [ ] The user confirmed `revision: 1` and its tolerance before it was written
- [ ] `contour check` is green on `beaky`, the rig checks included
- [ ] Every shape check that was green before is still green
- [ ] The user has seen the sheet of the fixed build

## Blocked by

- [49](49-seams-and-pivots-measured-at-rest.md)
