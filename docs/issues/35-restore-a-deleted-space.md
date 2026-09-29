# 35 — Restore a deleted space

**Type:** AFK · **Source:** [ADR 0021](../adr/0021-the-lobby.md) decision 6

## What to build

The **lobby** lists deleted spaces, the bundles in the trash, beside the live
ones, and can restore one. Restoring is a clone of its bundle back into a space
root. It is also a `contour` command, so it can be done without a page.

A restored space is a space: its marker, pre-push stub and scaffolding are all
checked. Its `pre-push` stub lives in `.git/hooks`, which a clone does not carry,
so it is reinstalled rather than assumed. A restored space that could push would
break rule 8 in the one place nobody would think to look.

## Acceptance criteria

- [ ] The lobby and a `contour` command both list deleted spaces, with name and date, separately from live ones
- [ ] Restore recreates the space at its old location, or a chosen one, with tracked content byte-identical to what was deleted
- [ ] The restored space refuses every push, and `contour doctor` in it is all `ok`
- [ ] Restore refuses when the name or path is taken, and changes nothing
- [ ] After a restore, the bundle stays in the trash until the user removes it

## Blocked by

- [34](34-delete-leaves-a-bundle.md)
