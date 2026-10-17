# 133 — The picture fills its space

**Type:** AFK · **Source:** design session 2026-10-18

## What to build

The big picture is drawn at its own pixel size and only ever shrunk
(`max-width: 100%`). A reference 490 px wide stays 490 px on any screen.

- **Fit the whole picture.** As large as the space beside the column allows,
  all of it in view and in its own shape — a small reference is enlarged. It
  refits when the window or the column (issue 134) changes size.
- **Nothing measured moves.** Marks and spans are kept in the picture's own
  pixels, so a click maps back exactly at any scale. An enlarged picture is
  softer, never less precise.
- **No zoom on the big picture.** The card's zoom and the ends' handles (132)
  are where fine work happens; a second zoom would add panning and scroll
  conflicts. Its own issue if it is still missed after 131 and 132.

## Acceptance criteria

- [ ] A small reference fills the space beside the column, whole, in its own shape
- [ ] Resizing the window refits it
- [ ] A mark placed on an enlarged picture lands on the same picture pixel as at natural size
- [ ] The sheet fits the same way

## Blocked by

None - can start immediately
