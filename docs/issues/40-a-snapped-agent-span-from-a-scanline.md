# 40 — A snapped agent span from a scanline

**Type:** AFK · **Source:** ADR 0022 decisions 2, 4 — [the agent reads the references in spans](../adr/0022-the-agent-reads-the-references-in-spans.md)

## What to build

Today the agent can point at a reference and cannot draw a distance on one: a
**span** can only be drawn by the user. This slice lets the agent draw one
without choosing a pixel.

The agent runs a scanline across a reference, as it can now, and says which of
the runs it found the question is about, and one line of what the distance is:
*the legs, centre to centre*. `contour measure` places the two ends on what it
measured, writes an **agent span** into the space's marks, and pins the answer
back on the same reference, in millimetres with its error bar, as it does for a
user's span.

The agent can ask for one of three distances between the runs it picks:
- centre to centre;
- the gap between them;
- the outer extent across them.

It cannot give a pixel for an end. There is no spelling of this command that
accepts one.

**The span stores the question that placed it**: the reference, the height, the
colour, which runs, which distance. That is the re-runnable basis ADR 0017 asked
for, so asking again places the same ends.

The canvas already draws an agent's marks in their own colour, so the span
appears there with no page change.

## Acceptance criteria

- [ ] The agent can create a span between two runs of a scanline, naming the runs and the distance wanted, and no form of the command takes a pixel for an end
- [ ] The span is stored as the agent's, marked **snapped**, with the question that placed it
- [ ] The millimetre answer is pinned back on the reference, with its error bar, as for a user's span
- [ ] Re-running a span's stored question places the same ends, and says so when the reference no longer gives them
- [ ] Picking a run the scanline did not find is refused, naming the runs it did find
- [ ] With no **anchor** stated in the space, the span is still drawn and the answer is in pixels, saying why
- [ ] On `beaky`'s front reference, the legs centre to centre read 168 within the error bar
- [ ] Turning picked runs into two ends is tested with no Blender; nothing under `refs/` is written

## Blocked by

None — can start immediately.
