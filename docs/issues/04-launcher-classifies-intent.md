# 04 — The launcher classifies a call's intent

**Type:** AFK · **Source:** ADR 0019 decision 20

## What to build

The gate needs to know what a call *means*, in Contour's vocabulary: a spec
write, a commit, a push, a build, a ref write. The launcher answers, rather than
the console pattern-matching the call's text.

A glob list is brittle exactly where the stakes are. One intent has four
spellings — `./contour check`, `contour check`, a `cd` into the space first, and
`contour render`, which also builds — so a permission list needing four rules
will still have a hole, and a gap in it is a rule that has silently stopped being
enforced.

Semantic categories are also what make *the strictest list* definable at all:
strictest means every category gated, which is finite and checkable, where a glob
list can never be known to be complete.

Two halves:

**Classify.** Given a call, return the category it belongs to, or none.

**Enumerate.** Print the categories the toolkit knows. Slice 05's file is
meaningful only against the current set, and a list that cannot be printed cannot
be audited.

The console therefore knows the launcher's command table — coupling to the one
surface in this system that is already authoritative and already exhaustive.

## Acceptance criteria

- [ ] All four spellings of a build classify as one category
- [ ] A spec write, a commit, a push and a ref write each classify to their own category
- [ ] A call matching nothing classifies as none, and is distinguishable from an error
- [ ] The category list is printable and its order is stable
- [ ] Adding a launcher command that carries an intent fails a test until it is classified
- [ ] Classification needs no Blender run and no network

## Blocked by

None — can start immediately.
