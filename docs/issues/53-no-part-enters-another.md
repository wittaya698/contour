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

- [x] Every frame of every clip is checked, not only the keys
- [x] A collision is red, naming the clip, the frame and both parts
- [x] A seam growing beyond its tolerance is red, naming the joint and frame
- [x] Fixtures show both: two colliding parts, and a part swept through its parent —
  not a wrong pivot, which growth does not catch (below)
- [x] Green adds no lines to the report

## What it came to

**The seam rule catches a sweep, not a wrong pivot.** A scratch build of the
smoke fixture measured each seam's size — how far the overlap reaches from the
seam's centre — at every frame of `sway`. Turning on the right pivot, the
pillar's seam with the faceted cap widens by 2.8 mm. The plinth's bone moved
40 mm off its seam widens its seam by only 1.5 mm, and 10 mm off by 0.3 mm. So
no tolerance passes the right sway and fails the wrong pivot; a seam slides
rather than grows. The wrong pivot is already caught at rest: `pivots` holds
each origin to its seam, and `kit.rig()` puts each bone's head on its origin.
What growth does catch is the hole the rule's own exemption leaves: a part
swinging through its parent crosses only its parent, so "enters another" never
fires, but its seam grows by ten millimetres or more. The user kept growth for that.

The gather reads `contacts` at every frame of every clip, beside the poses, and
each contact record carries `reach`. The `clips` check judges them: a part
crossing any but its parent is named once, at the first frame it does
(`sway f0: cap enters plinth`); a seam wider than at rest by more than the
clip's `seam_growth_mm` is named once, at its worst frame (`sway f5: plinth's
seam with pillar grows 10.7mm, past 3mm`). Both rules are lines in the `clips`
check, so green adds nothing to the report.

`seam_growth_mm` is per clip and required, by the user's choice. The smoke
fixture's 3 is the agent's number, just above the 2.8 mm the right sway
measures. Mutants: *part enters another* (the cap sunk into the plinth) and
*seam swept through its parent* (a key at frame 5, which no spec key names,
turning the plinth 90° through the pillar). Each was checked to be caught by
its own rule and not by the key rules.

## Blocked by

- [52](52-clips-keyed-from-the-spec.md)
