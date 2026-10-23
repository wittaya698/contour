# 155 — A new spec is written whole the first time

**Type:** AFK · **Source:** the console run that checked issue 151, 2026-10-23

## What to build

A new-space run's first spec write was refused twice before the gate showed
it: once for having no `revision:` line (*a spec write is the whole change,
revision bump included*), then for a case that did not name `10000, 0.01, 0.1,
1024`. Both refusals were right. Together with two refused calls before them,
the page said *4 stops cost 38 extra turns*.

`NEW_SPACE` step 4 says to draft `spec.yaml` and flag every number, but not
that a new spec carries `revision: 1` nor that its case names every number it
sets, the toolkit's usual ones included. Say both there, in the words the
refusals use, so the first write is the one shown.

## Acceptance criteria

- [ ] `NEW_SPACE` step 4 says a new spec is written with `revision: 1`
- [ ] It says the write's case names every number the spec sets, with why, the toolkit's usual values too
- [ ] Looked at in a real console: a new space's first spec write reaches the gate without a refusal

## Blocked by

None - can start immediately
