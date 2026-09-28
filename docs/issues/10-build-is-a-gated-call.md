# 10 — A build is a gated call, and that gate resolves marks

**Type:** AFK · **Source:** ADR 0019 decisions 10, 14

## What to build

Mark resolution moves from session close to the instant before a rebuild, and the
build's own gate becomes the place it happens.

ADR 0018 resolved marks at session close because the ray must hit the geometry the
sheet was drawn from, and called that a window to be kept shut. A console that
rebuilds would open the window on every build. But the console *owns* the build,
so it knows the instant before geometry changes — which is a strictly better place
to cast rays than session close ever was. The window is deleted rather than
managed.

**Putting the build on the ask-list is what makes this one mechanism instead of
two.** Because the sheet is always on screen it can always be clicked, and an
agent rebuild would otherwise invalidate marks mid-typing. Gated, the only thing
that can invalidate a mark is a call the user personally approved — so
*resolve before rebuild* and the ask-list compose, and there is no second
concurrency story to own.

The cost is a click per build, which is the most-pressured gate in the system. The
sanctioned relief is a deliberate per-space ask-list entry, never a button on the
dialog.

The staleness test already exists — `views.json` carries a fingerprint of the
build its cameras drew — and needs only to be moved.

## Acceptance criteria

- [x] Approving a build resolves every unresolved mark before geometry changes
- [x] Resolution casts rays against the build the sheet was drawn from, verified by fingerprint
- [x] A mark made and then a build approved: the pin survives in part-local coordinates
- [x] A mark on a part that the build deletes is explicitly orphaned, not quietly misplaced
- [x] No build path exists that skips the gate, so no path exists that skips resolution
- [x] Allowing the build category in a space's ask-list still resolves marks
- [x] `contour canvas` still resolves at session close when run without the console

## Blocked by

- [08 — A gated run, end to end](08-a-gated-run-end-to-end.md)
- [09 — The sheet panel, labelled](09-the-sheet-panel-labelled.md)
