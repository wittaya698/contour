# 75 — Claude's span questions, one at a time

**Type:** AFK · **Source:** ADR 0022's answers, worded by ADR 0025 decision 1 — [pages for someone who has never opened a terminal](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md)

## What to build

When agent spans are unanswered, the canvas says *Claude has 4 questions about
your pictures* and steps through them one by one: the reference zoomed on the
span, its number, and *Is this the seat's depth?*. The answers are *Yes, that's
it*, *Let me move it* and *Wrong thing…* with a reason, which are adopt, correct
and reject underneath; *skip for now* leaves it unanswered. A by-eye span says
*Claude placed these ends by eye — check them closely*.

The marks list stays as the overview, and answering there still works.

## Acceptance criteria

- [ ] Unanswered agent spans are offered one at a time, zoomed
- [ ] Each answer records adopt, correct or reject exactly as the list does
- [ ] Skip leaves the span unanswered and moves on
- [ ] A by-eye span is flagged as decided
- [ ] The list still shows every span and still answers

## Blocked by

None - can start immediately
