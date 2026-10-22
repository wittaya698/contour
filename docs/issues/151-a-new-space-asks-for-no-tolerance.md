# 151 — A new space asks for no tolerance

**Type:** AFK · **Source:** a new-space run seen on 2026-10-22

## What to build

A new-space run ended its closing with six questions, the sixth *How strict
should it be? Once I measure the photo, how far off may each size be? About
±2 mm, or something looser?* The new-space skill says never to ask the user for
a tolerance or a triangle budget, and `NEW_SPACE` step 3 says to propose them.
The run asked anyway.

A lead, not a finding: the space's `CLAUDE.md` tells the agent to say
*tolerance* as *how far off it may be*, and that phrase reads as a question.
Reproduce first, with the stand-in agent or a real run, then fix whichever of
the prompt, the skill or the template made it ask.

## Acceptance criteria

- [ ] What made the run ask is found and named here
- [ ] The new-space flow's words say to propose tolerances and never ask, in one place they all point to
- [ ] Looked at in a real console: a new space proposes its tolerances and asks none

## Blocked by

None - can start immediately
