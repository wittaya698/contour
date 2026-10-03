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

- [x] The agent can create a span between two runs of a scanline, naming the runs and the distance wanted, and no form of the command takes a pixel for an end
- [x] The span is stored as the agent's, marked **snapped**, with the question that placed it
- [x] The millimetre answer is pinned back on the reference, with its error bar, as for a user's span
- [x] Re-running a span's stored question places the same ends, and says so when the reference no longer gives them
- [x] Picking a run the scanline did not find is refused, naming the runs it did find
- [x] With no **anchor** stated in the space, the span is still drawn and the answer is in pixels, saying why
- [x] On `beaky`'s front reference, the legs centre to centre read 168 within the error bar
- [x] Turning picked runs into two ends is tested with no Blender; nothing under `refs/` is written

## What it came to

- The span form is `contour measure <ref> --scanline V [--of HEX] --runs A,B
  --between centres|gap|extent "what it is"`. The scanline's report now numbers
  its runs, so the agent picks from exactly what it was shown.
- `contour measure` used to ignore any flag it did not know, so `--to 560,700`
  would have been dropped silently and the agent would have believed it placed
  an end. The span form refuses every flag that is not its own, naming it.
- The ends are pixel edges for `gap` and `extent` and run centres for
  `centres`, so each reads the same number the scanline already printed for
  it. They are stored counted from the top, as the canvas draws, which it does
  with no change: any mark with a `to` is a line, blue when the agent wrote it.
- The stored question holds the anchor it was asked under. Without an anchor a
  scanline height is a fraction of the silhouette, so an anchor stated later
  would otherwise move the row and asking again would place different ends.
- `contour measure --again <m>` writes nothing. It says *same ends*, or what the
  same question places now and why that differs; an answer is never moved
  after it was given.
- On a copy of `beaky`'s front, in a space of its own: the legs centre to
  centre read **168 mm ±3 mm**, and asking again gives the same ends. The test
  needs `$BLENDER` and beaky's reference, and skips without either.
- Not done here: ADR 0022 decision 9 puts rule 1's new clause in "the slice
  that makes agent spans drawable", which is this one, while the batch puts it
  in 46. It changes `CLAUDE.md` and the space template, so it waits for the
  user.

## Blocked by

None — can start immediately.
