# 91 — The channel

**Type:** AFK · **Source:** ADR 0027, decision 7 — [the unattended run](../adr/0027-the-unattended-run.md)

## What to build

The lobby's enter and the connector's `open console` reach a console running
unattended: they ask it to open its own page, the asking carries nothing, and
the console opens its URL in this machine's browser itself. The secret goes from
console to browser and never through the caller. When a gate or a question
parks, the console posts a system notification of its own, naming the space and
the act in plain words, with no link. The lobby's row says *waiting for you*.

## Acceptance criteria

- [ ] `open console` and the lobby's enter bring up an unattended console's page, and no URL reaches the caller
- [ ] Asking twice opens the page, never a second console
- [ ] A parked gate or question posts a notification naming the space and the act, holding no URL
- [ ] The lobby row reads *waiting for you* while a run is parked

## Blocked by

- [89](89-contour-request.md)
