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

- [x] Each of the three answers, undone, leaves `marks.json` as it was before it
- [x] Undo is offered for the last answer only, on the card or in the list
- [x] Answering another, skipping, reloading or a run starting takes the offer away
- [x] The server refuses an undo once the span changed or a run started, and the page says why

## How it was built

- **One way back for all three answers.** Each answer keeps a *slip*: every
  record it touched, as it was and as the answer left it. `marks.unanswer`
  puts those back in place and drops any record the answer added, so adopt,
  correct and reject are undone the same way and `marks.json` comes back
  byte for byte.
- **The canvas holds the last slip only, in memory.** `POST /unanswer` refuses
  any span but that one, and refuses it again once it has been undone. It also
  refuses when any record the answer touched has changed since, or when the
  run named in `.contour/last-run.json` is not the one that was latest at the
  answer. That last check covers a run started from any console.
- **The page holds the window.** It offers *Adopted span 15 · undo* on the
  card, or beside the span in the list when the card is not showing. Another
  answer, a skip, a reload, or a run's prompt arriving in the transcript takes
  the offer away. A refusal is said under the list.

`tests/test_slip.py`. Checked end to end on the stand-in console, driven
headless.

## Blocked by

- 131
