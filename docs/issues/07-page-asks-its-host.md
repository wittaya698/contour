# 07 — The page asks its host what it can do

**Type:** AFK · **Source:** ADR 0019 decision 23

## What to build

One page, two hosts. Served by the launcher it is marks-only; served by the
console it is the full surface. The page asks its host what it can do rather than
assuming, through one capabilities endpoint that both servers answer.

This is what makes the containment mean anything. Keeping the launcher
stdlib-pure is worthless if the pipeline is not fully usable without the console,
and marking is not a nicety: the sheet is the surface both parties point at, and
`marks.json` is the tracked record of why two builds differ. If marking required
the environment, the zero-dependency toolkit would lose a capability it already
has, and *clone it, run `selftest`, mark up a sheet* would stop being a complete
story for anyone the toolkit is shared with.

Two pages sharing components was rejected as a bundler with a delay — the same
signal that a bundler would have been. If the page outgrows one file, the
console's extra views are served beside it, not bundled into it.

## Acceptance criteria

- [x] Both servers answer the capabilities endpoint
- [x] Launcher-served, the page offers marking and shows no console affordance
- [x] Console-served, the page offers the console's surface
- [x] `contour canvas` behaves exactly as before this slice, from the user's side
- [x] The page is still one file with no build step
- [x] An unknown capability name is ignored rather than breaking the page

## Blocked by

- [06 — `contour-console` exists and serves the page](06-contour-console-serves-the-page.md)
