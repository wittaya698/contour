# 44 — A by-eye agent span

**Type:** AFK · **Source:** ADR 0022 decisions 3, 6 — [the agent reads the references in spans](../adr/0022-the-agent-reads-the-references-in-spans.md)

## What to build

Snapping needs an edge that measurement can find. A photograph of a real object,
or a soft gradient, may give none: ADR 0017 notes that the colour queries do not
work on a real chair. For those, the agent may place a span's ends freely.

Such a span is **by eye**, and everything that shows it says so:
- the record is marked by eye, and stores no question, because there was none;
- the pinned answer states that its error bar covers the arithmetic between the
  ends and not the placing of them;
- the canvas draws it distinctly from a snapped span.

A by-eye span can be answered like any agent span (slice 42). Until it is, its
number is one the agent may not propose for the spec. This slice makes that state
readable: asking about a span says whether its number may be proposed as the
agent's, or must wait for the user.

The snapped path stays the default. The agent's by-eye spelling is separate from
slice 40's, so a by-eye span is never made by accident.

## Acceptance criteria

- [x] The agent can create a span with two free ends, only through the by-eye spelling
- [x] The record, the pinned answer and the canvas each say the span is by eye
- [x] The answer's wording states what its error bar does not cover
- [x] An unanswered by-eye span reports that its number may not be proposed; an adopted or corrected one reports that it may
- [x] An unanswered snapped span reports that its number may be proposed as the agent's own
- [x] Nothing under `refs/` is written

## What it came to

- `contour measure <ref> --by-eye --from X,Y --to X,Y "what it is"` draws one.
  Rows count from the bottom, as every height `contour measure` reports does.
  `--from` or `--to` without `--by-eye` is refused on a bare query, and the
  snapped spellings already refused both, so a free end is never placed by
  accident.
- The record is `placed: "by eye"`, with its scale and no question; `--again`
  refuses it, saying it was placed by eye.
- Its answer reads, after the number: *by eye: the bar covers the arithmetic
  between the ends, not the placing of them*. The command's report says the same.
- The canvas strokes it dashed and labels it *by eye* in the list. What that
  looks like has not been seen by the user.
- `contour measure --standing ID` says whether a span's number may be proposed,
  and as whose, with the reading beside it: the user's (drawn, adopted or
  corrected); the agent's own reading (snapped, unanswered); or not until the
  user answers it (by eye, unanswered). A rejected span may not be proposed.
  It reads `marks.json` only, so the launcher answers it without Blender.
- A corrected by-eye span loses the label, as a corrected snapped one loses its
  question: the ends are the user's.

## Blocked by

- [43](43-accept-adr-0022.md)
