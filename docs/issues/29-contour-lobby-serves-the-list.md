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

- [x] `contour lobby` works from anywhere, inside a space or not, and opens a page listing the same spaces as `contour spaces --json`
- [x] Every one of issue 01's protections holds for the lobby, and is tested against it, not only inherited on paper
- [x] The canvas and the console run on the same protected server as before; their tests pass unchanged
- [x] With no spaces, the page shows onboarding copy rather than an empty table
- [x] Closing the tab ends `contour lobby`, which prints a terse last line and exits 0
- [x] The lobby offers only the actions its host can perform, asked of the host through the page's **capability** mechanism; at this slice, that is none

## What it came to

**The server is `lib/page.py`.** `Page` holds issue 01's protections — the
secret, the loopback bind, the origin and `Sec-Fetch-Site` checks, JSON-only
POSTs — and the endpoints every page has: `/`, `/can`, `/beat`, `/done`. A host
adds its content as `served()`; a caller adds its own as `routes`, last, so
neither can replace a shared endpoint. `Canvas` is a `Page` serving the sheet,
the marks, the mask and the references, with the same constructor and
attributes as before; the console did not change.

**The heartbeat moved with it.** A `Page` given a `grace` ends when the beats
stop, never before a first one. The lobby turns it on (`$CONTOUR_LOBBY_GRACE`
shortens it for tests); the canvas leaves it off, so Done is still its lifetime.
The console keeps its own watcher, which has more reasons to end than a silence
(a lost parent, an idle clock, a pending gate); moving it onto `Page` is left
undone.

**The lobby is `lib/lobby.py` and `lib/lobby.html`.** It serves one route,
`/spaces`, from `listing()` in `lib/cli.py` — the reading `contour spaces
--json` prints, called on every request. `/can` is empty. No spaces shows what a
model space is and `contour init`, not an empty table. Closing the tab prints
`lobby closed — the page closed` and exits 0.

`tests/test_lobby.py`: the command run from outside and inside a space; each of
issue 01's protections asked of a running lobby; the ending, and no ending
before a first beat; the page's source. Thirteen mutants: twelve caught. The
survivor drops the page's immediate first beat, which only delays it by one
interval. The suite runs 536 tests, 6 skipped.

**One canvas test changed, by decision:** `test_canvas.py`'s one-page check now
names `lobby.html` beside `canvas.html`. ADR 0019 rejected the console adding a
second page for a space; the lobby is a page above the spaces (ADR 0021), and
any other page still fails it. `lobby` is in the intent roster as intentless:
it lists and writes nothing.

## Blocked by

- [28](28-spaces-speaks-json.md)
