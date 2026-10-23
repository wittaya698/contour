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

- [x] What made the run ask is found and named here
- [x] The new-space flow's words say to propose tolerances and never ask, in one place they all point to
- [x] Looked at in a real console: a new space proposes its tolerances and asks none

## Found (2026-10-23)

The run was not the new-space flow. Its prompt was *Do you have questions?*,
asked in `walkie-talkie` before anything was in it, so neither `NEW_SPACE` nor
the new-space skill reached it. The only rules it read were the space's
`CLAUDE.md`, and they said nothing against asking: rule 1 flagged tolerances
*loudest*, which the run honoured in its last line, and *Speaking to the user*
gave the word as *how far off it may be*, beside *anchor* →
*How big is it in real life?*, which is a question the user is asked. The run
asked both the same way. Its first question, *so I can't guess it*, is the
rule before issue 148 too: the space was made before it.

The fix puts the rule where every run reads it. Rule 1, in the toolkit's
`CLAUDE.md` and the template's, now says never to ask for a tolerance or a
triangle budget, in a form or a closing, and to propose both. *Speaking to
the user* gives each as a proposal, *I'd let it be 15 mm off*, never asked.
`NEW_SPACE` step 3 and the skill point to rule 1 (`test_plain_voice.ProposedTest`).

A space keeps the `CLAUDE.md` it was made with: `walkie-talkie` and every
space made before this has the old rule 1 and asks the same way, until its
`CLAUDE.md` is brought up to the template's by hand. Nothing refreshes it.

Looked at in a console on 2026-10-23, in a new space with the walkie-talkie
photo: the form asked what it is, how big, where it is seen, its parts and
anything else, and nothing about how strict or how detailed. The spec write's
case listed *My numbers… the tolerances first*: *how far off the 110 mm height
may be is 1 mm*, and *tri_budget 10000*, each with its reason.

## Blocked by

None - can start immediately
