# 113 — A release tag is `v<N>` and nothing else

**Type:** AFK · **Source:** [ADR 0013](../adr/0013-releases-are-versioned-folders.md), amended 2026-10-11

## What was found

The mark store prunes closed marks the last release tag already holds, and it
takes *the last release tag* to be the newest tag of any name. A bookmark tag a
user cuts in their own space — `before-rig-rewrite` — is read as a release, and
closed marks it holds are pruned from `marks.json`. Nothing is lost at that
moment, since `git show` is asked first; but the marks are then kept by a tag
nobody promised to keep, and `git tag -d` on a finished experiment leaves them
under no name. ADR 0018 says a *release* holds them. ADR 0013 and
`release-model` meanwhile named releases `<variant>-v<N>`, which a lobby rename
would orphan.

## What to build

Only a tag of exactly the form `v<N>` is a release. Every reader of releases —
the mark store's pruning, and `release-model`'s numbering — sees those and no
others, and the newest is the one with the highest N. `release-model` tags
`v<N>`. No space has a tag, so nothing is migrated.

## Acceptance criteria

- [ ] A space whose only tag is `before-rig-rewrite` prunes no marks
- [ ] With `v1`, `v2` and a later bookmark tag, pruning reads `v2`
- [ ] `v10` is newer than `v9`
- [ ] `release-model` (template and its copy instructions) tags `v<N>` and reads N from `v<N>` tags only
- [ ] The tests that tagged `v0.10.0` say what they now prove, or move to `v<N>`

## Blocked by

None - can start immediately
