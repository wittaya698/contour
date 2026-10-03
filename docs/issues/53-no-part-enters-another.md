# 53 — No part enters another, at any frame

**Type:** AFK · **Source:** ADR 0023, what is checked — [a rig and its clips are part of the build](../adr/0023-a-rig-and-its-clips-are-part-of-the-build.md)

## What to build

For every clip, at every frame, no part may enter another — except a part and its
parent, at their seam. And that seam may not grow beyond a tolerance as the part
turns: a part turning about its seam's centre keeps the seam about the same size,
so a seam that grows means the pivot is wrong. That is how a wrong pivot is caught
without a picture.

Every frame, not only key poses: mid-swing, between keys, is where a hand passes
closest to the torso. Silent on green; on red one line, such as
`walk f8: hand_L enters torso`.

The seam-growth tolerance is a spec field, the user's.

## Acceptance criteria

- [ ] Every frame of every clip is checked, not only the keys
- [ ] A collision is red, naming the clip, the frame and both parts
- [ ] A seam growing beyond its tolerance is red, naming the joint and frame
- [ ] Fixtures show both: two colliding parts, and a part turning about a wrong pivot
- [ ] Green adds no lines to the report

## Blocked by

- [52](52-clips-keyed-from-the-spec.md)
