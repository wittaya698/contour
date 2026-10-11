# 106 — The case on the page is whatever the agent said last

**Type:** HITL · **Source:** [issue 102](102-an-unattended-agent-tries-the-write.md)'s real run, against rule 1 and ADR 0028, decision 1 — [approvals wait, and the run goes on](../adr/0028-approvals-wait-and-the-run-goes-on.md)

## What was found

An approval keeps, as its case, the agent's last text before the call
(`Run.proposal`). In run `3008d980` in `beaky-0028`, that text was narration
about a build just set aside: *While that waits, I'll read the last recorded
check result.* The page showed it above *depth 615 → 644 mm* as though it were
the argument. The argument itself (the user asked for a longer beak; the side
reference reads about 597 mm deep, so this moves away from the pictures) came
in the closing, where the page does not put it beside the approval.

Issue 101 made *no* case visible, as *Claude gave no case for this*. This is the
other way round: text that is not a case passed as one.

## Options (to decide)

- **The case must name what the write sets.** A spec write whose text just
  before it does not mention each new value its diff shows (*644* for depth
  615 → 644) is refused, as 101 and 104 refuse theirs, and the agent is told to
  put its case, with the numbers, just before the write. Checkable at the gate,
  fits a change the user asked for as well as one measured on a span, and
  narration does not pass it. It cannot tell a good argument from a bad one;
  nothing at the gate can.
- **The page shows the run's closing beside its approvals,** marked as said
  after the act. Nothing is refused, and the argument is seen wherever the agent
  put it. But it is the account of the whole run, written after the write, which
  is what rule 1 says a gate must not stand in for.
- **Both:** refuse a case without the numbers, and show the closing too.
- **Neither:** leave it to rule 1's wording, and see whether agents learn it.
  Two runs in, they have not.

## Decided

**The first: the case names what the write sets.** In every console run, as 101
and 104 are, a spec write is refused when the agent's text just before it does
not mention each number the write sets — *644* for depth 615 → 644, *3* for a
tolerance 20 → 3 — and the agent is told to put its case, with them, just before
the write. Only numbers: a description or a note is prose, and asking for it to
be quoted back would ask for a copy, not a case. A write that sets no number
needs none named, and one with nothing before it still says *Claude gave no
case for this* (issue 101).

## Acceptance criteria

- [x] What the page shows as a spec write's case argues for that change, or the page says plainly that there is none
- [ ] Issue 102's two criteria are met by a real unattended run
