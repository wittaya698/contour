# 140 — Claude proposes directions

**Type:** AFK · **Source:** ADR 0032, decision 2 — [a span is measured through the camera](../adr/0032-a-span-is-measured-through-the-camera.md)

## What to build

`contour measure` gains a direction: the agent names the edges (*the body
tube's top and bottom edges*), measurement snaps lines to them as it snaps a
span's ends, and the direction is recorded as a question in `marks.json`.

- **Two lines at least**, each snapped; a line that finds no edge is said, and
  placed by eye only as a span's end is, and says so.
- **Answered as a span is:** adopt, correct, reject, through the same
  endpoints and the same record of who drew it.
- **The worksheet draws them**, so the agent sees its own directions at its
  checkpoint (ADR 0022).
- `build-model`'s skill says when to propose them: before any span on a
  reference that is not straight on.

## Acceptance criteria

- [ ] A direction proposed on a test reference lands on the edges named, within a pixel
- [ ] Adopted, corrected and rejected directions are recorded as spans' answers are
- [ ] The worksheet draws directions apart from spans
- [ ] The skill's guidance is in `templates/space/.claude/skills/build-model`

## Blocked by

- 138
