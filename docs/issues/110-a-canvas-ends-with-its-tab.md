# 110 — A canvas the connector opened ends with its tab

**Type:** HITL · **Source:** [issue 108](108-thinking-is-not-said.md)'s runs, against ADR 0024 — [the connector](../adr/0024-the-connector-desktop-reads-and-opens.md)

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

## Acceptance criteria

- [ ] A canvas opened from Desktop and closed by its tab no longer holds the space
