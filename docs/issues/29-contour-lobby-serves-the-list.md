# 29 — `contour lobby` serves the list

**Type:** AFK · **Source:** [ADR 0021](../adr/0021-the-lobby.md) decisions 1, 2

## What to build

`contour lobby` opens the **lobby** in a browser and shows every space, with the
health from slice 28. It is served by the launcher and needs only the standard
library, so it works on a bare clone.

**The server is split before it is reused.** The canvas's server carries issue
01's protections:
- a per-session secret;
- an explicit bind to `127.0.0.1`;
- an `Origin` / `Sec-Fetch-Site` check;
- JSON-only POSTs;
- the heartbeat that ends a session when its tab closes.

It is also shaped around one space, because it will not start without a sheet and
a marks file. Separate the protected, beating server from the sheet-and-marks
content, so that the canvas, the console and the lobby all sit on one
implementation of issue 01. A second copy of the protections for the lobby is
exactly the drift ADR 0019 served the canvas's own server to avoid.

**The empty state is onboarding.** With no spaces, the page says what a model
space is and where one would be made. It has no create action yet (that is slice
37); it tells the reader to use `contour init` for now.

## Acceptance criteria

- [ ] `contour lobby` works from anywhere, inside a space or not, and opens a page listing the same spaces as `contour spaces --json`
- [ ] Every one of issue 01's protections holds for the lobby, and is tested against it, not only inherited on paper
- [ ] The canvas and the console run on the same protected server as before; their tests pass unchanged
- [ ] With no spaces, the page shows onboarding copy rather than an empty table
- [ ] Closing the tab ends `contour lobby`, which prints a terse last line and exits 0
- [ ] The lobby offers only the actions its host can perform, asked of the host through the page's **capability** mechanism; at this slice, that is none

## Blocked by

- [28](28-spaces-speaks-json.md)
