# 136 — A slip can be undone

**Type:** AFK · **Source:** design session 2026-10-18; ADR 0022, decision 5

## What to build

An answer to an agent span is final (`marks._answering`: *it cannot be
answered twice*). A wrong button or a bad drag then stands. This adds one
undo, for slips — not a change of mind, which is a span of the person's own
and already outranks Claude's reading.

- **Only the last answer, and only until the person moves on.** After an
  answer the card says *Adopted span 15 · undo* (or in the list, beside the
  span, when the card is not showing). The window closes when they answer
  another span, skip, reload or leave, or a run starts.
- **The page holds the window; the server checks it.** Undo is refused, with a
  reason, unless the span is still exactly as the answer left it and no run
  has started since. A tab left open behind a run cannot reopen a question
  the run already used.
- **Restored exactly, with no trace.** Adopt: the span is Claude's question
  again. Correct: Claude's ends back, the closed reading reopened, the new
  reading removed. Reject: reopened, the why and *not to be used* cleared.
- ADR 0022 decision 5 stands: answers are final, and this window is the only
  exception. `CONTEXT.md` says so under **agent span**.

## Acceptance criteria

- [ ] Each of the three answers, undone, leaves `marks.json` as it was before it
- [ ] Undo is offered for the last answer only, on the card or in the list
- [ ] Answering another, skipping, reloading or a run starting takes the offer away
- [ ] The server refuses an undo once the span changed or a run started, and the page says why

## Blocked by

- 131
