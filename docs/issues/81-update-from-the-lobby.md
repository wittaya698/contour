# 81 — Update from the lobby

**Type:** AFK · **Source:** ADR 0026, decision 2 — [update: a space's copies brought in step](../adr/0026-update-brings-a-space-in-step.md)

## What to build

*needs an update* on a lobby row gets its action. Update shows what the dry run
says — what will change, what will be left alone and why — and does it on
confirm. Refusals come back in `contour update`'s words. Afterwards the row says
*updated, not saved yet* until the next commit.

## Acceptance criteria

- [ ] Update shows the dry run before doing anything
- [ ] Refusals read as the command words them
- [ ] The row says *updated, not saved yet* until a commit carries it

## Blocked by

- [67](67-a-lobby-row-is-a-picture-and-a-verdict.md)
- [80](80-contour-update.md)
