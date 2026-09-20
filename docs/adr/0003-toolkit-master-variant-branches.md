# 0003 — `master` is a toolkit; variants are long-lived branches

**Status:** Accepted · 2026-09-20 · **superseded in part by [ADR 0014](0014-toolkit-is-a-tool-a-model-is-a-project.md) and [ADR 0015](0015-model-spaces.md)**

> **Superseded in part 2026-09-20.** The first half of the decision stands:
> `master` holds only shared machinery and builds no model. The second half —
> each variant a long-lived branch, and `git merge master` into variants — is
> retired by ADR 0014 and was implemented by ADR 0015. Each model is now its own
> repository, a *model space*, so there is no branch to merge `master` into. The
> text below is left as it was decided, as the record of what was chosen and why.

## Context

Several models will coexist and be worked on independently. The obvious layout
— `master` holds the canonical model, variants fork from it — makes every
merge-forward conflict on `build.py`, the one file that matters most.

## Decision

`master` holds only shared machinery: `lib/`, `verify.py`, `schema/`,
`.claude/`, `fixtures/`, `docs/`. It builds no deliverable model.

Each variant is a long-lived branch adding exactly two files:
`spec/<variant>.yaml` and `models/<variant>/build.py`. Variants never merge
back. Shared fixes land on `master` and reach variants via `git merge master`.

## Consequences

- Merges forward are conflict-free by construction, because variants only add
  files no other branch has. A conflict is a signal that the rule was broken.
- Variants can sit on older toolkit versions deliberately.
- `master` is never executed as part of normal work, so toolkit bugs would only
  surface inside variant work, disguised as modeling problems. ADR 0005's
  fixture exists to close that gap.
- There is no single "the model" — `master` checked out alone builds nothing.

## Rejected

- **Linear `master` with short-lived `explore/` branches** — recommended
  initially; rejected in favour of permanently coexisting variants.
- **`master` as the canonical model** — conflicts in `build.py` on every merge.
- **Fully self-contained branches** — a verifier bug must be fixed N times.
- **Toolkit as a separate pinned package** — strongest boundary, but every
  shared-code edit becomes a cross-repo round trip.
