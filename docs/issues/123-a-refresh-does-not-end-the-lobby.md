# 123 — A refresh does not end the lobby

**Type:** AFK · **Source:** found in flight, issue 120

## What to build

Reloading the lobby's page ends the lobby: the page says it is going as it
unloads, and the lobby, given no reload grace, ends at once. The canvas has the
same signal and waits five seconds for a beat to take it back. The lobby does
the same, and the reloaded page carries on in the same session.

## Acceptance criteria

- [ ] A page that says it is going and beats again within the grace leaves the lobby running
- [ ] A page that says it is going and does not beat again ends it, as today
- [ ] A reloaded lobby page lists the spaces and acts with its session

## Blocked by

None - can start immediately
