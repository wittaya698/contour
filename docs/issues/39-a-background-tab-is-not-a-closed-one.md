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

- [ ] A page that has said it is hidden, then goes silent past `GRACE_S`, does not end its server, for both the lobby and the console
- [ ] It still ends after the long grace if it never comes back
- [ ] A page that says it is going ends its server promptly, without waiting out any grace
- [ ] A visible page that goes silent still ends after `GRACE_S`, as today
- [ ] A console at a pending gate is never ended by a hidden tab's silence
- [ ] The hidden and going messages pass the same token, JSON and origin checks as every other POST
- [ ] By hand, in Safari: the lobby and a console it entered both survive 5 minutes in a background tab, and closing either tab still ends it within seconds

## Blocked by

None — can start immediately.

Issue 36's manual check (parts B and C) waits on this: a lobby or console that
dies in a background tab cannot show that closing the lobby leaves its consoles
running.
