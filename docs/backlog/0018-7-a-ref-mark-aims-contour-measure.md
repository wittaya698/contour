# 0018-7 — A ref mark aims `contour measure`

**Type:** AFK · **Status:** ready

## Parent

[ADR 0018 — Marks: a canvas over the sheet, and a shared way to point](../adr/0018-marks-a-canvas-over-the-sheet.md)

## What to build

The payoff. Two pins on a reference define a span the *user* chose, and
`contour measure` reads between them instead of sweeping a scanline the agent
guessed at. The result is written back as an agent mark on the same reference,
carrying the measurement in millimetres against the set's anchor.

This is the slice that proves the feature earns its keep, and it has a waiting
test case. `beaky-solo` was built from a single perspective reference and its
leg spacing came out 126 mm against `beaky`'s 168 — 25% low, because a
separation is a vector and projects by the cosine of the yaw while a diameter
does not. The error is invisible inside the image: the reference's own inner gap
sits in the same ratio to the same leg width, so nothing in the picture
contradicts it. `beaky-solo`'s `NOTES.md` open question 3 — *what separates the
legs* — is open for exactly this mechanical reason.

Note what this slice does and does not settle. It lets the user state the span
they mean on the image. It does not recover the yaw, and so it does not turn a
perspective reference into an orthographic one; ADR 0018's parent finding
stands.

## Acceptance criteria

- [ ] Two ref marks can be paired into a span from the canvas
- [ ] `contour measure` reads the span between them, using the set's anchor for scale
- [ ] The result is written back as an agent mark on the same reference
- [ ] The result states millimetres and the measurement's own precision
- [ ] A span whose reference set has no anchor is refused, not guessed
- [ ] Measuring never writes anything under the references directory
- [ ] Verified end to end against `beaky-solo` open question 3

## Blocked by

- [0018-5](0018-5-ref-marks.md)
- [0018-6](0018-6-agent-authored-marks.md)
