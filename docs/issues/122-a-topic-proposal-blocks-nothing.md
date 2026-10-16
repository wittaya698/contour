# 122 — A topic proposal blocks nothing

**Type:** AFK · **Source:** ADR 0030, decision 6 as amended on acceptance (issue 120) — [topics label a model for finding](../adr/0030-topics-label-a-model-for-finding.md)

## What to build

A topic proposal waits in its space as an approval does, and is answered the same
way, but a request to the space starts while one waits. Every other approval
still refuses a request until it is answered (ADR 0028). The space's status and
the lobby still say a proposal waits.

## Acceptance criteria

- [x] A request to a space whose only waiting approval is a topic proposal starts
- [x] A request to a space with any other approval waiting is refused, as today, and names only those
- [x] Status, the lobby and the connector still say the proposal waits
- [x] A run that ends with a proposal waiting leaves it waiting, answered as before

## Blocked by

None - can start immediately
