# 80 — `contour update` replaces only what nobody edited

**Type:** AFK · **Source:** ADR 0026, decisions 1, 3, 4 and 5 — [update: a space's copies brought in step](../adr/0026-update-brings-a-space-in-step.md)

## What to build

Run inside a space, `contour update` brings its scaffold — the files `SCAFFOLD`
lists — in step with the toolkit. A file is replaced only when it equals the
template as it was at the toolkit commit `.contour/project` records, filled in for
the space's current name; one that differs was edited, and is named and left
alone. A missing file is written. The recorded commit moves to the current one.
When that commit is not in the toolkit's history, nothing is overwritten.

`--dry-run` says what would change and what would be left, and why. It takes the
space's hold and refuses while a page is open on it, as rename does. The result
is left uncommitted. Machine-readable output, for the lobby.

## Acceptance criteria

- [ ] An untouched file is replaced and an edited one is named and left
- [ ] A renamed space's untouched files count as untouched
- [ ] A recorded commit missing from history overwrites nothing
- [ ] It refuses during a run and while a page is open, worded as rename words it
- [ ] `--dry-run` changes nothing
- [ ] `contour doctor` reports the space in step afterwards, except for files left alone

## Blocked by

None - can start immediately
