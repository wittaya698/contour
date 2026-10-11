# 110 — A canvas the connector opened ends with its tab

**Type:** HITL, decided · AFK · **Source:** [issue 108](108-thinking-is-not-said.md)'s runs, against ADR 0024 — [the connector](../adr/0024-the-connector-desktop-reads-and-opens.md)

## What was found

A chat opened `beaky-0028`'s canvas at 16:25 with `open`, for a span the
user did not need. The user closed the tab. At 16:59 `contour update` refused:
*a page is open on this space: canvas (pid 24217)*. The canvas was still running,
and still on the space's presence.

A canvas ends on **Done**, and only on Done. Its page sends `/going` as the tab
closes, and the canvas records it and acts on nothing (issue 39), because under
the launcher a person ran `contour canvas` and knows to finish it. Opened for
them by a chat, nobody told them there was anything to finish.

## To decide

- **A canvas the connector opened ends when its tab goes,** after a grace
  period for a reload, as a console ends a run when its beats stop. One a
  person started from a terminal keeps waiting for Done.
- **Or every canvas ends when its tab goes.** Simpler, and a terminal
  `contour canvas` would return on a closed tab where it waits now.
- **Or none does,** and `status` and the lobby say a canvas is open and how to
  end it.

## Decided (the user's)

**Every canvas ends when its tab goes,** as well as on Done. Nothing is lost:
each mark is written to `marks.json` as it arrives, so Done never guarded any
work, only said the user was finished. And a terminal's `contour canvas`, left
waiting on a closed tab, was the same fault, only less often met.

- **The canvas takes issue 39's rule** (`Page.closed`): a tab that says it is
  going, or is silent past 10 seconds on screen, or past an hour hidden, has
  closed.
- **A reload is not a closed tab.** It says going and then beats again, so the
  canvas waits 5 seconds after *going* (`RELOAD_S`) and carries on if a beat
  comes. The lobby and the console keep ending on *going* at once.
- **A closed tab is said as one:** *the tab closed, 1 mark kept*, never as
  Done's *captured*, so whoever started the canvas does not take it for the
  user's answer. The marks are anchored as on Done.
- **Under a console nothing changes.** The console owns the page's lifetime, and
  its canvas is given no grace of its own.

## Acceptance criteria

- [x] A canvas whose tab says it is going ends after the reload grace, and its report says the tab closed and how many marks were kept
- [x] A beat after going keeps it serving
- [x] A tab gone silent on screen ends it
- [x] `contour canvas` has the graces by default; a console's canvas has none
- [x] A canvas opened from Desktop and closed by its tab no longer holds the space (by hand, by the user)
