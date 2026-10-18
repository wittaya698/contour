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

## What was built

`lib/direction.py`, in the Blender-free half; `contour measure` loads the
picture and hands it over a column or a row at a time.

- **A line is two crossings picked**, as a snapped span is runs picked (ADR
  0022, decision 2). `--edges col:0.3` lists every place a column or row
  changes colour sharply, numbered, to a fraction of a pixel; `--line
  col:0.3#2,col:0.55#2` is the second crossing down each of two columns. By
  colour, not a background mask, which a photograph on a deck does not have.
  Rows count from the top here, as a mark's pixel does.
- **One mark per direction**, `{"direction": "x", "lines": [...]}`, each line
  `snapped` with the two crossings it was asked as, or `by eye`
  (`--line-by-eye`). It carries a `pixel` at its first line's middle, so the
  page shows it as an agent note until 141 asks it as a question.
- **Answered through the same store.** Adopt and reject as a span;
  `marks.correct_lines` takes the user's lines and keeps the agent's as
  `agent_lines`. A span's correction refuses a direction, and the reverse.
- **The worksheet draws a direction under the spans**, its lines thin and run
  to the picture's edges so they can be followed to where they meet, labelled
  apart. It counts in the worksheet's fingerprint; spans alone print as before.
- Checked under Blender on a painted box (`$BLENDER` is not set for the suite):
  `--edges` read the crossings the pure tests read, and the worksheet drew the
  direction along the box's edges.

## Acceptance criteria

- [x] A direction proposed on a test reference lands on the edges named, within a pixel
- [x] Adopted, corrected and rejected directions are recorded as spans' answers are
- [x] The worksheet draws directions apart from spans
- [x] The skill's guidance is in `templates/space/.claude/skills/build-model`

## Blocked by

- 138
