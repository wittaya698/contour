# 132 — A span is moved by its ends, and you see it move

**Type:** AFK · **Source:** design session 2026-10-18; ADR 0022, decision 5

## What to build

*Let me move it* changes a hint line far below the card and nothing else. The
person then drags a whole new span, and nothing is drawn until the mouse comes
up: the page ignores movement on a reference (`canvas.html`, the `mousemove`
handler returns while a reference shows). Most corrections are one end a few
pixels off an edge, and both ends have to be placed again for it.

- **Let me move it gives the span handles.** Claude's span stays where it is,
  with a handle on each end. Drag only the end that is wrong.
- **The line follows the handle live**, on the big picture and on the card's
  zoom, which is the place for fine work. Over a handle the cursor is a grab
  hand.
- **Save and Cancel.** Save sends the two ends through `/correct`, as now; the
  server does not change. Cancel puts the ends back and the question stands.
- **A new span, drawn by the person, is drawn live too.** The same missing
  feedback, on the same pictures.

## Acceptance criteria

- [ ] *Let me move it* shows handles on the asked span's two ends
- [ ] Dragging a handle redraws the span as it moves, on the big picture and the card
- [ ] Save records a correction with the moved ends; the other end is unchanged
- [ ] Cancel leaves the span unanswered and where Claude put it
- [ ] Drawing a new span draws it while the mouse is down
- [ ] Looked at in a real console

## Blocked by

- 131
