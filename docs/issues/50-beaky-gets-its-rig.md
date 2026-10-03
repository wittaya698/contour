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

- [x] The user confirmed `revision: 1` and its tolerance before it was written
- [x] `contour check` is green on `beaky`, the rig checks included
- [x] Every shape check that was green before is still green
- [x] The user has seen the sheet of the fixed build

## What it came to

- Measured first, in a scratch copy of the space with the tree and a tolerance
  of 0, so every pivot read out. The arithmetic held where it looked (head
  tangent; neck 135.6, hands 68.3, legs 30.8, arms 25.5 mm) and missed three: the
  beak's origin was 36.3 mm off (its base is buried in the head, its pivot is where
  it leaves it), the eyes 4.2, the shoes 0.3.
- The user confirmed `revision: 1`: the tree as above, and
  `transform.pivot_tolerance_mm: 1`, proposed as the agent's number.
- `build.py`: the neck rises 3 mm (`NECK_Z` 1170 → 1173), 3 mm into the head and
  4 into the torso, a seam at each with the height unchanged. Clean cuts have their
  pivot worked out — two spheres on one axis, the beak and eyes leaving the head,
  the arm's end entering the hand. Arms and legs cut a sphere obliquely; theirs are
  the measured centres, written as constants and said so.
- `pivots`' red message now says where the pivot is, `… off its pivot at (x, y,
  z)mm`: a distance alone gave the fix nothing to move to.
- `contour check` on `beaky`: 20/20, `seams 13 joints | pivots 0.5/1mm`; every
  shape reading unchanged. The worst left, 0.5 mm, is the hands: faceting and the
  mean of crossing points, not a misplaced origin.

## Blocked by

- [49](49-seams-and-pivots-measured-at-rest.md)
