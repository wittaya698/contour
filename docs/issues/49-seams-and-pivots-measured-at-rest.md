# 49 — Seams and pivots measured at rest

**Type:** AFK · **Source:** ADR 0023, where a part turns is measured, not declared — [a rig and its clips are part of the build](../adr/0023-a-rig-and-its-clips-are-part-of-the-build.md)

## What to build

For every part with a parent, verify measures its **seam** — the ring along which
its surface crosses its parent's — and its **pivot**, the seam's centre. Then:

- a joint with no seam is red: the part has floated off, or only touches at a
  tangent point, which is no seam (ADR 0023);
- a part whose origin is further from its pivot than the spec's tolerance is red.

The tolerance is a spec field, the user's like every other. A spec with a rig and
no tolerance is red for the missing field, not silently lenient.

This needs no bones: it is geometry at rest, and a measurement the checks stay
pure over (ADR 0020). It is what makes `build.py`'s hand-placed origins checked
rather than trusted.

## Acceptance criteria

- [ ] Each joint's seam and pivot are measured from the built geometry
- [ ] No seam is red, naming the part and its parent
- [ ] An origin off its pivot beyond tolerance is red, with the distance in mm
- [ ] A rig with no origin tolerance is red for the missing field
- [ ] A fixture shows each failure: a floating part, a tangent part, an origin off its pivot

## Blocked by

- [48](48-the-spec-carries-a-rig-tree.md)
