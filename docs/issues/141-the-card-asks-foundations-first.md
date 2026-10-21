# 141 — The card asks foundations first

**Type:** AFK · **Source:** ADR 0032, decision 6 — [a span is measured through the camera](../adr/0032-a-span-is-measured-through-the-camera.md)

## What to build

The question card, per reference: its directions, then its anchor span, then
its spans. A span's question shows millimetres only once its reference's
foundations are answered, and pixels with why before.

- **A direction is asked as a span is:** highlighted (131), moved by its lines'
  ends (132), undone as a slip (136).
- **Skip puts a foundation off**, and its spans keep showing pixels.
- **Rejecting a direction** says which answered spans it measured, since they
  are read again.

## Acceptance criteria

- [x] On a reference with unanswered foundations, the card asks them before its spans
- [x] A span asked before its foundations are answered shows pixels and why
- [x] Answering the last foundation turns its spans' numbers to millimetres without a reload
- [x] Looked at in a real console on an angled photograph

## What was built

- **The card asks one reference at a time.** References come in the order the
  list first reaches each one. On each, the card asks its directions, then its
  anchor span, then its spans. *Skip* puts any of them off, and the next one is
  asked.
- **A direction is asked as a span is.** The card names it *direction 5 ·
  2 lines*, by its badge, and asks *Are these the long edges, parallel on the
  object?* It is highlighted on the big picture, framed whole on the card, and
  undone as a slip. *Let me move it* puts a handle on every end of every line.
  Save sends its lines to `/correct`, which hands them to
  `marks.correct_lines`.
- **The anchor span asks for the size it claims to be:** *Is this the front,
  bottom edge — the width you told me, 300 mm?*, with its pixels beside it.
- **Pixels say why.** A span read in pixels shows what its millimetres wait on,
  with ids turned into the badges the person sees: *115 px ±2 px*, then
  *waits on span 8, the anchor span, being answered*.
- **Readings are read again inside the answer that changes them.** Every
  answer given on the page re-reads the open readings on its reference through
  the camera (`span.reread`). It runs as a hook inside the answer's own write,
  so the slip from 136 holds the re-read readings too, and an undo puts them
  back byte for byte. The page already reads the marks back after an answer,
  so the numbers turn without a reload. Not re-read: an anchor span's reading,
  which is its question, and a reading made at a kept scale, by the foreground
  box, which 142 handles.
- **Not built: *rejecting a direction says which answered spans it
  measured*.** That case cannot arise. Only an unanswered direction can be
  rejected, and a span is read only through answered ones, so a rejected
  direction has measured nothing.

`tests/test_foundations.py`. Looked at in the canvas, driven headless in
Chrome, on the painted angled box: three directions, an anchor span and two
spans, with the spans first in the list. The card asked the three directions,
then the anchor. Skipping the anchor brought up a span reading *115 px ±2 px*,
which said what it waited on. Adopting the anchor turned that span to *205 mm
±21 mm* on the card without a reload; the edge is 200 mm. Moving one end of a
direction and saving corrected only that end, and undoing it left
`marks.json` as it began.

## Blocked by

- 132, 136, 139, 140
