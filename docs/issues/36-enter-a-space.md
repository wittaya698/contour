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

- [ ] Enter opens a console on the chosen space in a new tab; the lobby keeps running
- [ ] With no console environment, `enter` is not granted, and the row shows the environment line instead
- [ ] Closing the lobby's tab leaves every console it opened running, each with its own presence
- [ ] A space already open in a console is shown as open, from its presence, and entering it again does not start a second console
- [ ] Open in Finder opens the space's directory

## Blocked by

- [33](33-accept-adr-0021.md)
