# 131 — The span being asked about is the one you see

**Type:** AFK · **Source:** design session 2026-10-18; ADR 0022, decision 5

## What to build

The question card zooms into one agent span, and nothing on the big picture
points back to it: all spans are drawn alike, blue and dashed, so with eighteen
on a reference the person matches the crop to the picture by eye. The cursor is
a crosshair whatever is under it.

- **The asked span stands out.** On the big picture it is drawn heavier, and
  the other spans fade. One Claude placed by eye stays broken while it is
  asked (ADR 0022, decision 3). Its number badge matches what the card says.
- **The card names it:** *span 15*, beside the reading.
- **The picture follows the question.** When the card moves to a question on
  a different reference, the big picture switches to that reference — never
  while the person is part-way through: a mark being typed, or a drag held.
  Then it switches once they finish.
- **The cursor says what a click will do:** a crosshair where a click marks or
  draws, a pointer over a button. Issue 132 adds the grab cursor on a span's
  ends.

## Acceptance criteria

- [x] With a question showing, the asked span is drawn unlike the others on the big picture
- [x] The card names the span by the number its badge carries
- [x] A question on another reference switches the big picture to it
- [x] A mark being typed, or a drag held, is never interrupted by that switch
- [x] Looked at in a real console with a reference carrying many agent spans

## Blocked by

None - can start immediately
