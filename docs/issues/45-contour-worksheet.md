# 45 — `contour worksheet`: the spans drawn onto the references

**Type:** AFK · **Source:** ADR 0022 decision 8 — [the agent reads the references in spans](../adr/0022-the-agent-reads-the-references-in-spans.md)

## What to build

The user sees agent spans on the canvas. The agent cannot see the canvas. This
command gives the agent the same picture, once: the **worksheet**.

`contour worksheet` draws every span in the space onto its reference and lays the
references out as one image, as the **sheet** lays out four views. For each span
the picture shows:
- the line, from end to end, and the span's id;
- its answer in millimetres;
- whether it is the user's or the agent's;
- whether it is **snapped** or **by eye**;
- which answer the user gave it, if any.

It is one image, so that it costs about what a sheet costs to look at. It is a
new file in the space, and **never a write to a reference**: an annotated
photograph is not the photograph, and rule 1 holds.

It is tracked, as `sheet.png` is, since ADR 0017 made the worksheet a shareable
artifact. It is regenerated whole each time, from the marks and the references.

When the agent looks at it is a matter for the skills, which slice 46 changes.
This slice makes the picture; it does not decide the moment.

## Acceptance criteria

- [ ] `contour worksheet` writes one image showing every reference that has a span, with each span drawn and labelled as above
- [ ] Rejected spans are drawn as rejected, not omitted, so the picture accounts for every span
- [ ] No file under `refs/` changes; this is tested by checksum
- [ ] A space with references and no spans says so, and writes nothing
- [ ] The terse report names the file and the count of spans, and the command's cost is listed in the commands table of `CLAUDE.md`
- [ ] Two runs over the same marks and references write identical images

## Blocked by

- [43](43-accept-adr-0022.md)
