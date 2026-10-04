# 55 — The filmstrip

**Type:** AFK · **Source:** ADR 0023, what is seen — [a rig and its clips are part of the build](../adr/0023-a-rig-and-its-clips-are-part-of-the-build.md)

## What to build

A clip as one picture: six frames from the side in one row, six from the front in
another, on the sheet's grid, one 1024² image labelled with the build it came
from. The cost of one sheet, for a whole cycle.

Rendered at a checkpoint only, never on every build (ADR 0005): the clip's
numbers are checked every build, and the filmstrip is for what numbers miss —
whether it looks like a walk.

Playback, for the user's eyes, is deferred (ADR 0023).

## Acceptance criteria

- [x] A command renders a clip's filmstrip to an image, labelled with its build
- [x] Six side and six front frames, evenly through the clip, on the sheet's grid and scale
- [x] A build without a checkpoint renders no filmstrip into the agent's context
- [x] The build-model skill says when to look at one

## Blocked by

- [52](52-clips-keyed-from-the-spec.md)

## What it came to

- `contour filmstrip [clip]` writes `out/filmstrip.png`. The clip may go
  unnamed when the spec has one; with several it is asked which. It holds the
  space, because it reads the build, and carries no gate category: like the
  worksheet, it writes only a file of its own.
- Frames: a loop is cut into six with no pose twice (30 → 0, 5 … 25); a clip
  that stops runs 0 … N with both ends.
- Scale: one for all twelve tiles, the sheet's (`views.sheet_scale`, now shared
  with `contour render`) over the corners the whole clip sweeps, unless the
  widest view would not fit a tile a sixth of the image wide — then only as far
  out as it takes. beaky, 0.88 m hand to hand, is the case that needs it.
- The build deletes the last filmstrip, so one on disk is always of the build
  beside it. `contour check` still renders the sheet and nothing else.
- A filmstrip in which nothing moves in any frame is refused rather than drawn:
  that is the clip posed at rest, and a still labelled as a clip would lie.
- Clip playback is `measure.playing`, shared with the clip measurement. Moving
  it there turned up that an NLA track compared with `is` only matches the
  same Python wrapper, so tracks are now compared by pointer.
- Proven on the fixture by `FilmstripTest` in `tests/test_fixture.py`, which the
  selftest now runs beside `FixtureTest`.
