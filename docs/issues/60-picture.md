# 60 — `picture`

**Type:** AFK · **Source:** ADR 0024, decision 3 — [the connector: Desktop reads and opens, never drives](../adr/0024-the-connector-desktop-reads-and-opens.md)

## What to build

A connector tool that returns one of a space's pictures as an MCP image: the
`sheet`, the `filmstrip` or the `worksheet`. With it, the build it was drawn
from, and whether that build is still current — the same comparison the panel
makes, so the connector and the console never disagree about a picture. A
picture never drawn says *not drawn yet*; nothing is rendered to answer.

This is the one part of the protocol that is new to the connector, which is why
it is a slice of its own.

## Acceptance criteria

- [x] `picture` returns each of the three as an image Desktop shows
- [x] Each comes with its build, and says when that build is no longer current
- [x] A picture never drawn says *not drawn yet*, and nothing renders
- [x] Nothing about `picture` starts Blender

## What it came to

A tool may now hand the connector MCP content blocks (`connector.image`)
instead of a reading. `picture` returns the PNG as an image block, then a text
block with the reading. A picture not on disk returns only
`{"said": "not drawn yet"}`, and the stub Blender's trace proves nothing started.

- **sheet**: `panel.state` over `views.json`, so `build`, `current` and `why`
  are the panel's own, including *last build failed*.
- **filmstrip**: its build was only in its pixels. The launcher now writes
  `out/filmstrip.json` (`{"build": …}`, the `views.json` shape) when a
  filmstrip succeeds, and `panel.state` reads that instead. A build already
  deletes `filmstrip.png`, and the record sits beside it.
- **worksheet**: of no build, so `build` is null. The launcher writes a
  fingerprint of the spans it drew to `.contour/worksheet.json`, and the
  reading says *the spans changed since it was drawn: run contour worksheet*
  when they move, or that it is not known, for a worksheet with no record
  (a fresh clone, or one drawn before this).

## Blocked by

- [57](57-the-connector-answers-spaces.md)
