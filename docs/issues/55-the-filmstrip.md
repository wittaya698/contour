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

- [ ] A command renders a clip's filmstrip to an image, labelled with its build
- [ ] Six side and six front frames, evenly through the clip, on the sheet's grid and scale
- [ ] A build without a checkpoint renders no filmstrip into the agent's context
- [ ] The build-model skill says when to look at one

## Blocked by

- [52](52-clips-keyed-from-the-spec.md)
