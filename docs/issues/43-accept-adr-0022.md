# 43 — Accept ADR 0022

**Type:** HITL · **Source:** [ADR 0022](../adr/0022-the-agent-reads-the-references-in-spans.md)

## What to build

Nothing, beyond the verdict.

ADR 0022 is Proposed, and gated on a tracer bullet. In `beaky`, the agent draws
**snapped** spans on the references for the three numbers ADR 0017 measured:

| | ADR 0017 | from |
|---|---|---|
| width | 888 | front silhouette |
| depth | 597 | side silhouette |
| legs, centre to centre | 168 | a scanline across the legs |

Then, on the canvas, the user adopts one span, corrects one and rejects one.

Slices 40–42 are that bullet. **Accept, amend or withdraw** on what it shows.

The claim under test is narrow: that the agent can say *which* edges and never
*where* they are, and still get the numbers. Things the bullet may turn up, which
would amend rather than withdraw:
- picking runs by number is too brittle, and the agent picks the wrong ones often;
- three kinds of distance between runs are not enough, or are too many;
- correcting a span by dragging is too coarse to fix a wrong end.

If the agent's picks are wrong more often than they are right, that is the
finding, and it is worth more than a pass. ADR 0017's bullet disagreed with what
was expected, and that disagreement was the reason to accept it.

**Do not start slices 44–46 first.** Each cites a decision that can still move.

## Acceptance criteria

- [x] The three spans were drawn by the agent in `beaky`, with no pixel typed for any end
- [x] Each number is compared with ADR 0017's, and the comparison is recorded in ADR 0022
- [x] The user gave each of the three answers once, on the canvas
- [x] ADR 0022 is Accepted, amended or withdrawn, with the result recorded in it
- [x] `docs/adr/README.md` and the ADR state the same status
- [x] Nothing in `beaky` was committed without the user's say (rule 5)

## What it came to

**Accepted**, 2026-10-03. The three snapped spans read 888, 597 and 168 — ADR
0017's numbers exactly — with no end typed as a pixel. The user adopted the
width, corrected the depth and rejected the legs, once each, on the canvas.

None of the three expected amendments turned up. Picking runs by number was not
tested hard: the leg scanline found two runs, on flat colours. Two things are
left open in the ADR:
- the picture went blank after a correction, though the record was right; not
  reproduced in headless Chrome;
- decision 9 was amended to put the rule 1 clause in 46, where the issues
  README already had it.

Nothing in `beaky` was committed; its `marks.json` holds the answers, untracked.

## Blocked by

- [41](41-snapped-spans-from-a-silhouette-or-a-region.md)
- [42](42-the-user-answers-an-agent-span.md)
