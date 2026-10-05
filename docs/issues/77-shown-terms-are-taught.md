# 77 — Shown terms are taught where they first appear

**Type:** AFK · **Source:** ADR 0025, decision 1 — [pages for someone who has never opened a terminal](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md)

## What to build

Each term in the *shown* tier — reference, sheet, mark, span, spec — carries a
one-line explanation where a page first shows it, in the words
`docs/CONTEXT.md`'s *On the page* gives it. Once a viewer has seen one, it stops
being offered; that memory is a per-viewer convenience and the page reads
correctly without it.

## Acceptance criteria

- [ ] Each shown term has its line where it first appears
- [ ] A dismissed explanation stays dismissed for that viewer
- [ ] With browser storage unavailable the page still renders and explains

## Blocked by

- [76](76-one-look-and-a-way-back.md)
