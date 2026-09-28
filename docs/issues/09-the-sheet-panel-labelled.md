# 09 — The sheet panel, labelled

**Type:** AFK · **Source:** ADR 0019 decisions 13, 24, 29

## What to build

The page becomes an equal split: transcript and sheet. The transcript is where
decisions are visible and where a gate fires; the sheet is where a build is
verified and where marks live.

**Every build renders for the page; only a checkpoint renders for the agent.**
Renders were rate-limited because a sheet entering the conversation costs ~1400
tokens — a cost to the agent's context, not to the render. A sheet going to a page
costs neither, so the panel can be current. The agent's budget is untouched: it
still may not pull a sheet into context except at a checkpoint.

*Checkpoint* keeps its meaning and loses its trigger. It no longer means *render
now*; it means only *the agent believes it is done, or is stuck* — the part with no
mechanical replacement, since green is not the same as finished and *stuck* has no
signal at all.

**The panel states which build it is drawn from.** `views.json` already carries a
fingerprint of the build its cameras drew, so a stale sheet is labelled rather than
quietly authoritative.

**A failed build leaves the last good sheet, labelled.** Red produces no geometry
and red is the common state inside a fix loop. Rendering a partially built scene
was rejected as the most dangerous option available: a picture of a model that has
never existed, in the panel where every other picture is real. Overlaying the
failing check was rejected because a check knows a number, not a location, so
overlays would appear for some failures and not others and teach the reader to
distrust their absence.

**And because no resolution happened, the page says so** — *marks not resolved:
last build failed* — rather than leaving marks silently pending, which would return
the anchoring window through a side door as a mark that looks pinned and is not.

The cost accepted: four extra Workbench passes and the identity mask on every
build. The lever if it hurts is a lower-resolution panel render, never a less
frequent one.

## Acceptance criteria

- [x] Transcript and sheet share the page as an equal split
- [x] The sheet panel shows the build fingerprint it was drawn from
- [x] A finished build updates the panel without the agent spending context
- [x] A failed build leaves the last good sheet with an explicit not-current label
- [x] A failed build shows *marks not resolved: last build failed*
- [x] No partially built scene is ever rendered
- [x] No failing check is overlaid on the sheet
- [x] The agent still pulls a sheet into context only at a checkpoint
- [x] A space that has never built shows an empty panel, not a broken one

## Blocked by

- [08 — A gated run, end to end](08-a-gated-run-end-to-end.md)
