# 112 — A veto that is not about a part is not promoted to one

**Type:** AFK · **Source:** `beaky-0028`, 2026-10-11

## What was found

`beaky-0028`'s two build vetoes, *v1* (no reason) and *v2* (*Cancel for now*),
were both promoted to marks on `arm_L`: `m1` with no text, and `m2` reading
*Cancel for now*. Neither veto was about the arm, or about any part: they
refused a build.

`console/vetoes.py`'s `promote` checks that the part is one the build knows,
and that the veto was not promoted before. It does not check what the veto
refused, or that it has a sentence to carry, though its own docstring says *a
veto nobody recorded has no sentence to carry*.

## What to build

Only a veto with a reason, of a spec or reference write, is offered for
promotion and promoted: those are the gated calls whose refusal can be about
what the model is. A build, a save or a push refused is a decision about when,
not about a part.

## Acceptance criteria

- [x] A build, save or push veto is neither offered for promotion on the page nor promoted
- [x] A veto with no reason is not promoted
