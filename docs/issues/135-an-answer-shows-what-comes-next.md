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

- [ ] The stale path is named here, with how it was reproduced
- [ ] Every answer moves the card on, or says why it could not, without a reload
- [ ] A request that fails is said on the page

## Blocked by

None - can start immediately
