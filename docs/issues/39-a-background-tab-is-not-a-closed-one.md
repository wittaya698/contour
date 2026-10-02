# 39 — A background tab is not a closed one

**Type:** AFK · **Source:** found checking issue 36 by hand, 2026-10-02 · ADR 0019, ADR 0021 decision 2

## What to build

The lobby and the console each live as long as their tab (ADR 0021, decision
2; ADR 0019). A browser gives no reliable signal that a tab has closed, so each
page beats every 3 seconds. The server takes 10 seconds of silence (`GRACE_S`)
to mean the tab is gone, then ends, giving back its port, its presence and, for
the console, its run.

**Browsers slow down or pause timers in tabs nobody is looking at.** A tab left
open in the background stops beating, and the server ends exactly as if it had
been closed. The page stays on screen, dead. Nobody was idle: the user was in
another tab or another app, which is what using the lobby looks like. You enter
a space, then go back to the list.

Seen three times on this machine, in Safari, all ending with "… closed — the
page closed":
- a console the lobby started, after the user went back to the lobby tab to
  look at the row;
- a console started the same way by hand, whose tab was left behind another;
- the lobby itself, about a minute after it opened, while its browser was
  behind the terminal.

**It costs more on a console with a pending gate.** The beat check in
`console/server.py`'s `watch` comes before the check that suppresses the idle
clock while a gate is pending. So a console waiting at a gate in a background
tab ends its run. That decides the gate by silence, which ADR 0019 rules out.

The canvas is not affected. It records beats and acts on none, and its lifetime
is its Done button.

**The fix keeps "closing the tab ends it", and stops reading "hidden" as
"closed".** The page knows which it is:
- when it is **hidden** (`visibilitychange`), it says so. Until it beats as
  visible again, the server allows a long grace rather than 10 seconds, without
  relying on further beats, since a hidden tab may send none;
- when it is **really going** (`pagehide`), it says so with a `keepalive`
  request. That request carries the token header, which a `sendBeacon` cannot,
  so issue 01's protections still hold. The server then ends promptly;
- while it is **visible**, nothing changes: 10 seconds of silence still ends it.

A tab that closes without the `pagehide` request arriving (a browser quit or a
crash) is caught by the long grace instead of the short one. That is the trade:
a server that occasionally outlives its tab, against one that regularly dies
under it. The long grace bounds the first. The console's presence and hold are
already judged by whether its process is alive, so a lingering console stays
honest about being open.

**Open, for the implementer to propose before writing:** how long the long
grace is. The console already ends after an hour idle (`IDLE_S`). The lobby has
no idle limit, and a lobby that lingers an hour costs a port and nothing more.

## Acceptance criteria

- [x] A page that has said it is hidden, then goes silent past `GRACE_S`, does not end its server, for both the lobby and the console
- [x] It still ends after the long grace if it never comes back
- [x] A page that says it is going ends its server promptly, without waiting out any grace
- [x] A visible page that goes silent still ends after `GRACE_S`, as today
- [x] A console at a pending gate is never ended by a hidden tab's silence
- [x] The hidden and going messages pass the same token, JSON and origin checks as every other POST
- [x] By hand, in Safari: the lobby and a console it entered both survive 5 minutes in a background tab, and closing either tab still ends it within seconds

## What it came to

The rule for what a silence means now lives in one place, `Page.closed`, and
both watchers ask it: `Page`'s own, which ends the lobby, and the console's,
which used to restate it. A tab has closed when it said it is going, or when it
has been silent past `grace` while on screen, or past `hidden_grace` after it
said it is hidden. The canvas under the launcher has no grace, so it records
both new words and acts on neither; its lifetime is still its Done button.

- **Hidden** rides on the beat: `POST /beat` carries `{"hidden": true}`, and
  any beat without it puts the tab back on the short grace. Each page sends
  `hidden: document.hidden` on every beat and once more from
  `visibilitychange`, while a tab about to be throttled can still send it.
- **Going** is a new shared endpoint, `POST /going`, sent from `pagehide`
  through the page's one `ask` helper with `keepalive`. So it carries the token
  header, and stands behind the same token, JSON and origin checks as every
  other POST.
- **The long grace is an hour** for both, as proposed: the console's `IDLE_S`,
  so a hidden console lives no longer than an idle one already could, and for
  the lobby a port held an hour at worst. `$CONTOUR_LOBBY_HIDDEN_GRACE` and
  `$CONTOUR_CONSOLE_HIDDEN_GRACE` shorten it for tests, beside the existing
  grace hatches.
- **A gate under a hidden tab has no silence limit at all.** The trade, stated:
  a browser that crashes while hidden at a gate leaves the console waiting
  until the terminal that launched it closes. That is the cost of never
  deciding a gate by silence, and the parent check still ends it. A tab that
  says it is going, or goes quiet while visible, still ends a console at a
  gate, as before: that is the page closing.

A `pagehide` from a back/forward-cache navigation also says going, so a page
restored from that cache comes back to a server that has ended. Rare for these
pages, which nobody navigates away from in the same tab; left alone.

Checked by hand in Safari by the user: the lobby and a console it entered both
survived a background tab, and closing either tab still ended it.

## Blocked by

None — can start immediately.

Issue 36's manual check (parts B and C) waits on this: a lobby or console that
dies in a background tab cannot show that closing the lobby leaves its consoles
running.
