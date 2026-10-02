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

- [x] The confirm step shows every line of the proposal, and the page cannot confirm without showing it
- [x] A refused rename (held, open in a console or canvas, name taken) shows the command's reason and changes nothing
- [x] After a rename, the list shows the new name, and the row says renamed-uncommitted until the space's next commit
- [x] The confirm text says that a terminal agent session in the space cannot be seen
- [x] End to end on a throwaway space: rename from the page, then `contour check` in it is green with `revision:` bumped
- [x] With a console open on that space, the same rename is refused

## What it came to

- The lobby's server gained `POST /rename` and the `rename` capability. It runs
  `contour rename <name> --json` in the space the page named, and returns the
  command's answer unchanged. A path the listing does not hold gets a 404, so the
  page cannot point the command anywhere it was not shown.
- The confirm carries the proposal the page showed. The server proposes again,
  and if the command no longer says the same, the confirm is refused with "the
  proposal changed since it was shown". This makes "cannot confirm without
  showing it" something the server enforces, not just how the page is built.
  Only then does it run `--yes`.
- "Renamed, uncommitted" is a `renamed` field in the listing (`contour spaces
  --json` too). It is read from git each time: the spec at HEAD names one model
  and the spec on disk another. Nothing is stored, so it survives a lobby restart
  and clears on the next commit.
- End to end means `contour check` gets past its revision check with `$BLENDER`
  pointing nowhere, as in issue 31. A fully green check needs Blender, which the
  suite does not have. The page itself was driven through a real rename and a
  refusal in headless Chrome over a throwaway space. The suite's page tests are
  structural.

## Blocked by

- [29](29-contour-lobby-serves-the-list.md)
- [31](31-contour-rename.md)
