# 135 — An answer shows what comes next without a reload

**Type:** AFK · **Source:** design session 2026-10-18

## What to build

After answering, the person sometimes had to reload to see the next question.
Which answer it follows is not known: it happened more than once and could not
be pinned to one button. `answered()` reads the marks back and redraws, which
should move the card on, so something on some path does not.

- **Reproduce it first**, with the stand-in agent: a run that leaves several
  agent spans, each answer tried in turn — *Yes*, *Let me move it*, *Wrong
  thing* (and its prompt cancelled), on the card and in the list — and the
  Run column's question options too.
- **Then fix the path that is stale**, with a test that fails before the fix.
  A failed request is said on the page, never swallowed.
- If the only path found is *Let me move it* looking dead, it is 132's and this
  issue closes into it.

## Acceptance criteria

- [x] The stale path is named here, with how it was reproduced
- [x] Every answer moves the card on, or says why it could not, without a reload
- [x] A request that fails is said on the page

## What was found

Reproduced against the stand-in console, the page driven headless over
Chrome's debugging pipe, with eight agent spans on the megaphone reference.
After each answer the card was checked against a fresh read of `/marks`.

- **Every answer the page gives itself moved the card on:** *Yes*, *Let me
  move it* then Save or Cancel, *Wrong thing* with a reason or cancelled,
  *skip*, and the list's adopt, correct and reject.
- **The stale path was any span written by someone else.** The page read
  `/marks` on load and after its own answers, and never again. A span placed
  by a run's `contour measure`, or an answer given in another tab, reached
  the card only on a reload. The file held 4 questions while the card said 3,
  for as long as it was watched. That is how answering in the Run column
  comes to need a reload: the run the answer starts places its spans where
  the page never looks.
- **Fixed:** the marks are read on a 2 s clock as well as on load and after
  an answer, through one read (`reread`). It redraws only when they changed,
  and a read that comes back after a newer one is dropped.
- **Two smaller stale things went with it.** After Save, the line under the
  picture still said to drag an end and Save. An answer that failed was
  swallowed. Now a failed answer says it is not recorded and keeps a moved
  span's ends for another Save. A failed read-back says the card may be
  behind for a moment.

`tests/test_next.py`. Each test failed before its fix.

## Blocked by

None - can start immediately
