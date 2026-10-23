# 159 — A spec gate names spans still unanswered

**Type:** AFK · **Source:** ADR 0035, decision 7 — [A run waits on its by-eye spans](../adr/0035-a-run-waits-on-its-by-eye-spans.md)

## What to build

A spec write's gate, shown while by-eye agent spans are unanswered, adds a
line naming them by what they measure and their ids: *2 of Claude's spans are
still unanswered: width (m3), grille (m5). Their numbers are not in this
spec*, with a way to their cards. It does not stop Allow.

This holds whether or not a park came first: a span skipped at the park, or
drawn after it, is still unanswered.

## Acceptance criteria

- [ ] A spec gate with by-eye spans unanswered names each one
- [ ] With none unanswered the line is not there
- [ ] Snapped spans unanswered are not named
- [ ] Allow and Deny work as they do without the line

## Blocked by

- 156
