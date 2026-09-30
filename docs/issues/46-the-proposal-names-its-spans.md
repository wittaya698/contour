# 46 — The proposal names its spans

**Type:** HITL · **Source:** ADR 0022 decisions 6, 7, 9 — [the agent reads the references in spans](../adr/0022-the-agent-reads-the-references-in-spans.md)

## What to build

The mechanisms exist after slices 40–45. This slice changes what the agent is
told, which is the part that makes *measure, never recall* checkable.

**Rule 1 gains its clause.** The wording the user approved on 2026-09-30, recorded
in ADR 0022:

> A measurement read off a reference is a **span** — the user's, or an agent
> span — and the proposal names it. A number from a reference with no span
> behind it is not an argument, and a by-eye agent span argues nothing until the
> user has answered it.

It goes into the toolkit's `CLAUDE.md` and the space template together.

**The two skills say how.** Drafting a spec, and arguing a revision, both change:
- every number from a reference names its source: a span by id, the user, or
  *not measurable*, said plainly;
- a number from an unanswered **snapped** agent span is listed as the agent's
  own reading;
- a number from an unanswered **by eye** span is not proposed;
- the agent draws its spans with `contour measure`, which the new-space skill
  does not name today;
- the agent looks at the **worksheet** once, at the **checkpoint** where it
  believes its reading is finished, before proposing.

**Three stale examples are settled.** Rule 1, the new-space skill and the
build-model skill each use `beaky`'s depth of 620 as a worked example. ADR 0017
measured it at 597 and found the conclusion drawn from it inverted. The
build-model skill states that conclusion as fact: *the build was right and the
contract was not*. No verified case of a measurement showing a spec wrong is on
record to replace it, so the user decides: a real case, or wording that is
plainly an illustration.

**HITL because** it changes a hard rule, and because the template change puts
every existing space into drift until it is refreshed, in each space's own
repository, under rule 5.

## Acceptance criteria

- [ ] Rule 1 carries the approved clause, in the toolkit's `CLAUDE.md` and in the space template, identically
- [ ] The new-space skill and the build-model skill state the three sources, the two span rules, and the worksheet checkpoint
- [ ] The new-space skill names `contour measure` as how a reference is measured
- [ ] No skill or rule states that `beaky`'s reference depth is 620, or that its contract was wrong about depth
- [ ] The user chose the replacement for the 620 example
- [ ] `contour doctor` reports the drift in each existing space, and each is refreshed only on the user's say

## Blocked by

- [44](44-a-by-eye-agent-span.md)
- [45](45-contour-worksheet.md)
