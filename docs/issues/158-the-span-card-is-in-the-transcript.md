# 158 — The span card is in the transcript

**Type:** AFK · **Source:** ADR 0035, decision 3 — [A run waits on its by-eye spans](../adr/0035-a-run-waits-on-its-by-eye-spans.md)

## What to build

While the run waits on its spans (157), the canvas's card is shown in the
transcript at the park: the picture zoomed on the span, its question, *Yes,
that's it*, *Let me move it*, *Wrong thing…* and *skip for now*, one span at a
time, with *1 of 7*. Moving a span's ends works there as it does in the panel
(issue 132), and a slip can be undone (issue 136).

It is the same card, not a second one: the panel and the transcript show the
same state, and an answer in either is the answer in both, without a reload
(issue 135). Once the park ends, the transcript keeps a line saying what was
answered, as a form keeps its answers.

## Acceptance criteria

- [x] At the park, the transcript shows the card for the first span it waits on
- [x] Each answer there moves to the next span, and the panel shows it answered
- [x] An answer given in the panel moves the transcript's card on too
- [x] *Let me move it* drags the ends in the transcript's card
- [x] Looked at in a real console on a photo: the spans are answered without scrolling up

## Blocked by

- 157
