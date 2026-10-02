# 36 — Enter a space

**Type:** AFK · **Source:** [ADR 0021](../adr/0021-the-lobby.md) decisions 2, 9

## What to build

Entering a space from the **lobby** opens that space's **console**, in its own
tab and on its own port. The console is spawned as `contour-console` in the
space's directory, exactly as if it had been typed there. The lobby adds nothing
to it and passes it nothing but where to stand.

Entering is a **capability**, `enter`, granted only where the console's
environment exists. Where it does not, the row shows the same line
`contour-console` prints to make one, instead of the button. Nothing else in the
lobby needs the environment.

Closing the lobby ends none of the consoles it opened.

Each row also gets **open in Finder**, the escape hatch for anything the lobby
does not do.

## Acceptance criteria

- [x] Enter opens a console on the chosen space in a new tab; the lobby keeps running
- [x] With no console environment, `enter` is not granted, and the row shows the environment line instead
- [x] Closing the lobby's tab leaves every console it opened running, each with its own presence
- [x] A space already open in a console is shown as open, from its presence, and entering it again does not start a second console
- [x] Open in Finder opens the space's directory

## What it came to

- Entering runs `contour-console` in the space with nothing but the working
  directory, in a session of its own. A Ctrl-C in the lobby's terminal reaches
  its whole process group, and without the new session it took every console
  down with the lobby; the test that sends one failed until it was added.
- Where to find the console's environment, and the line that makes one, moved
  from `contour-console` into `lib/enter.py`, which both import. The lobby
  grants `enter` and the page shows that line from the same lookup, so they
  cannot disagree with the console about whether it can run.
- A space already open in a console is refused a second one, from the
  listing's presence. The lobby never sees a console's URL, which carries the
  console's secret, so it cannot send the page to the open tab; the row says
  the tab is the way in. Storing the URL in the presence record was rejected:
  it would put the secret in a file.
- Open in Finder is its own capability, `reveal`, granted only on macOS: on
  Linux `open` is `openvt`, so the route refuses where it is not granted.
- Found on the way: a Ctrl-C while the lobby was still opening its browser
  escaped as a traceback, because `webbrowser.open` sat outside the `try`. It is
  inside now. `console/server.py` has the same shape and is left for its own
  slice.
- The first criterion is tested as far as a console starting on the space and
  the lobby still answering. The tab itself is the console's own: the user
  pressed Enter in Safari and watched it open.
- Checking the rest by hand turned up [39](39-a-background-tab-is-not-a-closed-one.md):
  the lobby and the console take a background tab's paused beats for a closed
  tab, and end. The hand check that closing the lobby leaves its consoles
  running, and that a console stays shown as open, waits on 39. The tests cover
  both.

## Blocked by

- [33](33-accept-adr-0021.md)
