# 60 — `picture`

**Type:** AFK · **Source:** ADR 0024, decision 3 — [the connector: Desktop reads and opens, never drives](../adr/0024-the-connector-desktop-reads-and-opens.md)

## What to build

A connector tool that returns one of a space's pictures as an MCP image: the
`sheet`, the `filmstrip` or the `worksheet`. With it, the build it was drawn
from, and whether that build is still current — the same comparison the panel
makes, so the connector and the console never disagree about a picture. A
picture never drawn says *not drawn yet*; nothing is rendered to answer.

This is the one part of the protocol that is new to the connector, which is why
it is a slice of its own.

## Acceptance criteria

- [ ] `picture` returns each of the three as an image Desktop shows
- [ ] Each comes with its build, and says when that build is no longer current
- [ ] A picture never drawn says *not drawn yet*, and nothing renders
- [ ] Nothing about `picture` starts Blender

## Blocked by

- [57](57-the-connector-answers-spaces.md)
