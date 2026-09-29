# 32 — Rename from the lobby

**Type:** AFK · **Source:** [ADR 0021](../adr/0021-the-lobby.md) decision 5

## What to build

A rename action on each row of the **lobby**. It asks for the new name, then shows
the proposal from slice 31, in full, including what the rename leaves behind.
It performs the rename only when the user confirms that proposal. The page runs
the command, and holds none of the rules itself: a refusal from `contour rename`
is shown as the command worded it.

Afterwards, the row shows the space as **renamed, uncommitted** until a commit in
that space carries the rename. The lobby never commits.

This is the last slice of ADR 0021's tracer bullet, and the first time a real
space is renamed, which happens only when the user clicks confirm.

## Acceptance criteria

- [ ] The confirm step shows every line of the proposal, and the page cannot confirm without showing it
- [ ] A refused rename (held, open in a console or canvas, name taken) shows the command's reason and changes nothing
- [ ] After a rename, the list shows the new name, and the row says renamed-uncommitted until the space's next commit
- [ ] The confirm text says that a terminal agent session in the space cannot be seen
- [ ] End to end on a throwaway space: rename from the page, then `contour check` in it is green with `revision:` bumped
- [ ] With a console open on that space, the same rename is refused

## Blocked by

- [29](29-contour-lobby-serves-the-list.md)
- [31](31-contour-rename.md)
