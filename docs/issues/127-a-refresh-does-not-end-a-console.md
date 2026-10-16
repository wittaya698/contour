# 127 — A refresh does not end a console

**Type:** AFK · **Source:** found in flight, issue 123

## What to build

Reloading a console's page ends the console. The page says it is going as it
unloads, and the console builds its canvas with no reload grace, so it ends at
once, with whatever run was going. The lobby had the same fault, and issue 123
gave it the canvas's five seconds for a beat to take the going back. The
console gets the same grace, and the reloaded page carries on in the same
session, its transcript replayed as a reloaded tab already replays it.

A gate is not answered by a reload: the reloaded page shows it waiting, as it
was (ADR 0019, decision 17).

## Acceptance criteria

- [ ] A console page that says it is going and beats again within the grace leaves the console and its run going
- [ ] A page that says it is going and does not beat again ends the console, as closing its tab does today
- [ ] A page reloaded while a gate waits shows the same gate, still waiting

## Blocked by

None - can start immediately
