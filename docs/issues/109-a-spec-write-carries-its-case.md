# 109 — Under a console, a spec write carries its case

**Type:** AFK · **Source:** [issue 108](108-thinking-is-not-said.md)'s runs · **Decision:** [ADR 0029](../adr/0029-a-spec-write-carries-its-case.md)

## What to build

The console's agent gets `spec_write`, taking the whole new spec and the case
for it. Every other spec write under a console is refused and told to use it.
The gate reads it as an `Edit` of the whole spec as it reads now, so the diff,
the approval, the veto and a later allow are what they were, and its case is
the one it carries: said into the transcript before a watched gate, kept with
an approval when unattended.

## What a real run did

Run `d1ce99f5` in `beaky-0028`, requested from Desktop by a chat that still had
the connector's old words (*set depth to 648 … beak note to ~187*), with the beak
already 10% longer and `CLAUDE.md` still on rule 1's old wording: it made one `spec_write`, and the page showed *depth 615 → 648 mm* with its
case: the user's request, no span, the arithmetic to 648.5, and that the beak
stands about 191.5 proud, not 187. The user denied it with *~191*.

Still untested: the connector's new words. That chat started before Desktop was
restarted, so its request named the numbers. And the page shows a moved `notes`
entry as the whole list, before and after.

## Acceptance criteria

- [x] A `spec_write` waits with the case it carries, whatever was said before it
- [x] An `Edit`, `Write` or script writing `spec.yaml` under a console is refused and told to use `spec_write` with its case
- [x] One answered after the spec moved no longer applies
- [x] Watched, its case is in the transcript just before its gate
- [x] Rule 1's wording in both `CLAUDE.md` files says so — confirmed by the user
- [x] A real unattended run makes a spec write whose case is on the page beside its diff — run `d1ce99f5`

## Blocked by

None.
