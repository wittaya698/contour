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

- [x] `contour worksheet` writes one image showing every reference that has a span, with each span drawn and labelled as above
- [x] Rejected spans are drawn as rejected, not omitted, so the picture accounts for every span
- [x] No file under `refs/` changes; this is tested by checksum
- [x] A space with references and no spans says so, and writes nothing
- [x] The terse report names the file and the count of spans, and the command's cost is listed in the commands table of `CLAUDE.md`
- [x] Two runs over the same marks and references write identical images

## What it came to

- `contour worksheet` writes `worksheet.png` in the space, beside `sheet.png`,
  and a space's git sees it as a file to track. Every reference with a span is
  drawn 720 px tall, side by side, wrapping past 2160 px: `beaky`'s two came to
  1650x772.
- Each span is its line with a square at each end, coloured as the canvas
  colours it: blue for the agent's, red for the user's, grey when rejected. A
  by-eye span is dashed. Its id sits at the line's left end, and a label box
  carries the rest: `m5 610 mm ±3` over `agent, by eye, unanswered`. The label
  says *by hand* for a span the user placed, and *unanswered* for an agent span
  with no answer yet.
- A label moves off every span's line and every other label, so in a crowd it
  can land a little away from its own line; the id at the line's left end is
  what ties them together. Found on `beaky`'s side view, where one label
  first sat on the line drawn above its own.
- What each span says is `lib/worksheet.py`, standard library, so the launcher
  can use it. Where it goes and how it is drawn is `lib/worksheet_draw.py`:
  numpy and no bpy, testable without a scene, but in the Blender half of `lib/`
  because a bare clone has no numpy. Only reading the references and saving
  the PNG need Blender itself.
- With no spans on file the launcher says so and starts no Blender. A span
  whose reference is not in `refs/` is named in the report and left off.
- The row is in the toolkit's `CLAUDE.md`. It is not in the space template yet:
  slice 46 changes the template anyway, and one drift is better than two.

## Blocked by

- [43](43-accept-adr-0022.md)
