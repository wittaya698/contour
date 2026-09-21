# 0018-1 — Tracer: click the sheet, a mark lands, `check` reports it

**Type:** HITL · **Status:** ready

## Parent

[ADR 0018 — Marks: a canvas over the sheet, and a shared way to point](../adr/0018-marks-a-canvas-over-the-sheet.md)

## What to build

The whole loop, at its thinnest. `contour canvas`, run from inside a model
space, serves the existing sheet and one page from `http.server` on localhost
and opens a browser. Clicking the sheet and typing one line appends a record to
the space's `marks.json`. The page has a done action; the server then exits,
printing a terse report. Running `contour check` afterwards prints how many
marks are open.

No part identity, no anchoring, no references, no closing — those are later
slices. A mark at this stage carries the view it was placed on, the pixel, the
text, `author: user`, and `status: open`.

This slice also establishes the page itself: one HTML file, no build step, no
dependency beyond the Python standard library. ADR 0018's tripwire is that
needing a bundler means the scope went wrong.

## Acceptance criteria

- [ ] `contour canvas` serves the sheet and the page on localhost and opens a browser
- [ ] A click plus a line of text appends a record to a tracked `marks.json` in the space
- [ ] A record carries view, pixel, text, author and status
- [ ] The done action shuts the server down; the command exits 0 with a terse report naming how many marks were captured
- [ ] The command terminates on its own — nothing is left listening
- [ ] `contour check` prints `n marks open` when any are open, and nothing at all at zero
- [ ] That line never changes the exit code and is never counted as red
- [ ] The page is one file with no build step and no third-party dependency
- [ ] `marks.json` is tracked by git and is not covered by the spec guard
- [ ] Running `contour canvas` outside a model space fails with a clear message

## Blocked by

None — can start immediately.
