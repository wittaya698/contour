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

- [ ] The agent can create a span with two free ends, only through the by-eye spelling
- [ ] The record, the pinned answer and the canvas each say the span is by eye
- [ ] The answer's wording states what its error bar does not cover
- [ ] An unanswered by-eye span reports that its number may not be proposed; an adopted or corrected one reports that it may
- [ ] An unanswered snapped span reports that its number may be proposed as the agent's own
- [ ] Nothing under `refs/` is written

## Blocked by

- [43](43-accept-adr-0022.md)
