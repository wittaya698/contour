# 162 — `measure --help` shows its options

**Type:** AFK · **Source:** the console run that checked issues 158 and 159, 2026-10-23

## What to build

A new-space run read `lib/cmd_measure.py`, `lib/span.py` and ADRs to work out
how to tie an anchor to a span. The answer, `--claims DIM`, is in
`measure`'s own option list, the docstring at the top of `lib/cmd_measure.py`.
The agent cannot reach it: `contour measure --help` prints *FAIL measure: name
a reference image first* and then the launcher's list of every command, which
gives `measure` one line.

`contour measure --help`, and `contour measure` with no image, print
`measure`'s option list, the same text the docstring holds, so the two cannot
drift. Neither starts Blender.

## Acceptance criteria

- [ ] `contour measure --help` prints the option list, `--claims` among it, and exits 0 (tested)
- [ ] `contour measure` with no image says to name one, and prints the same list (tested)
- [ ] The list is read from one place, so an option added there shows in `--help` (tested)
- [ ] Neither starts Blender (tested)

## Blocked by

None - can start immediately
