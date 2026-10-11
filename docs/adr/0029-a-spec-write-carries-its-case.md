# 0029 — Under a console, a spec write carries its case

**Status:** Accepted · 2026-10-11 · **amends ADR 0028, decision 1, and issues 101, 102 and 106** ([0028](0028-approvals-wait-and-the-run-goes-on.md))

> **Accepted on its first real run** (issue 109). Run `d1ce99f5` in
> `beaky-0028`, requested from Desktop by a chat that still had the connector's
> old words (*set depth to 648 … beak note to ~187*), with the beak already 10%
> longer and `CLAUDE.md` still on rule 1's old wording:
>
> - **It made the write with `spec_write`, first time,** found from the tool's
>   own description: no `Edit` before it, no refusal, no retry.
> - **The page showed its case beside its diff,** *depth 615 → 648 mm*: that the
>   user asked for it, that no span stands behind it, how 648.5 is reached from
>   the build's numbers, and that the beak stands about 191.5 proud, not the
>   requested 187.
> - **The user answered it on the page,** denied with *~191*, and the veto is
>   recorded. The spec stayed at revision 5.
> - **Its closing said what waits,** and repeated the 191.5 point already in
>   the case.

## Context

Rule 1 says that under a console the proposal is *your text just before the
write*, and the gate keeps that text as the write's case (`Run.proposal`). Three
unattended runs in `beaky-0028` tried the spec write without saying anything
before it:

- `d85a0bb6`, refused by issue 106 for a case that did not name *644*, retried
  with no text at all;
- `889417cd`, told by issue 107 to put the case *as text in your reply, before
  the tool call*, retried with no text at all;
- `2c982b0d`, told by issue 108 that *your thinking is not shown to the person*,
  retried with no text at all, and closed saying *my reason was written just
  before each attempt*.

Its thinking held a good case, naming 648.5 and the user's request, written as
if to the person. The agent cannot tell its thinking from its reply, and a
refusal is one more thing it reads and does not act on. Three wordings did not
change it.

## Decision

1. **The console gives its agent one tool, `spec_write`,** taking the whole new
   `spec.yaml` as `content` and the case for it as `case`. The case is an
   argument, so it is wherever the write is: nothing has to be said first.
2. **Under a console, it is the only way a spec changes.** An `Edit`, a `Write`
   or a script that writes `spec.yaml` is refused, watched or not, and told to
   use `spec_write` with its case (this absorbs issue 101's refusal of a
   script). A terminal session has no such tool, and rule 1's prose confirm is
   unchanged there.
3. **The gate reads it as an `Edit` of the whole spec as it reads now** (a
   `Write` where there is no spec yet). The diff, the approval it may become,
   the veto it may become and applying it later are what they were, and one
   answered after the spec moved *no longer applies*, rather than undoing what
   moved it.
4. **Its case is checked as before:** part of a change is refused (issue 104),
   and a case that does not name each number it sets (issue 106). Spans are read
   from the case.
5. **Watched, the case is said** into the transcript as Claude's words just
   before the gate, where rule 1 puts the proposal and the person reads it.
   Unattended, it is kept with the approval, as before.
6. **The tool and its words are `console/run.py`'s;** `console/agent.py` only
   puts them in the SDK's shape (ADR 0019, decision 1).

## Consequences

- Rule 1's wording changes in both `CLAUDE.md` files: under a console the
  proposal is the case the write carries. That needs the user's confirm, and a
  space picks it up with `contour update`.
- Issues 107 and 108's refusal wordings are gone: there is no *text before the
  write* left to point at.
- A space whose agent never reaches `spec_write` (it asks in prose instead, as
  run `8af4cd7e` did, with nothing measured) is unchanged. That is rule 1 as a
  terminal keeps it, and not a failure of this.
- Accepted when a real unattended run makes a spec write whose case is on the
  page beside its diff.
