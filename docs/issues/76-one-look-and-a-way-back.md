# 76 — One look, and a way back to the lobby

**Type:** AFK · **Source:** ADR 0025, decision 12 — [pages for someone who has never opened a terminal](../adr/0025-pages-for-someone-who-never-opened-a-terminal.md)

## What to build

The lobby and the canvas-and-console page take their colours, type, buttons and
verdict styles from one stylesheet that both hosts serve. Every page carries the
same thin header: *Models › oak-chair* and issue 66's verdict. *Models* goes to
the lobby, starting one if none is running.

## Acceptance criteria

- [x] Both pages render from the one stylesheet, light and dark
- [x] The header shows on the lobby, the canvas and the console
- [x] Models opens the running lobby, or starts one

## Blocked by

- [66](66-the-verdict-in-plain-words.md)
