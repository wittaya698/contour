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

- [ ] On a reference with unanswered foundations, the card asks them before its spans
- [ ] A span asked before its foundations are answered shows pixels and why
- [ ] Answering the last foundation turns its spans' numbers to millimetres without a reload
- [ ] Looked at in a real console on an angled photograph

## Blocked by

- 132, 136, 139, 140
