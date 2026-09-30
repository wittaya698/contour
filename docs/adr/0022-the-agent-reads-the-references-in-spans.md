# 0022 — The agent reads the references in spans

**Status:** Proposed · 2026-09-30 · **amends [ADR 0017](0017-scaffold-measured-from-references.md) and [ADR 0018](0018-marks-a-canvas-over-the-sheet.md)**

> **Accept on a tracer bullet:** agent-drawn **snapped** spans on `beaky`'s
> references reproduce the three numbers ADR 0017 measured — width 888, depth 597,
> legs 168 — within their error bars, and the user adopts one, corrects one and
> rejects one on the canvas.

## Context

ADR 0017 split the reading of a reference by competence: the agent supplies
meaning, code supplies arithmetic. It built `contour measure` and proved the
split on `beaky`, where careful reading by eye was 14% out on the leg spacing and
blamed the spec for a depth error that was the build's.

Three things were left open, found on 2026-09-30:

- **The agent's reading leaves no trace.** `scaffold.yaml`, which was to record
  it, was never built. No space has one. What the agent decided a picture showed
  lives in the conversation and in `NOTES.md` prose.
- **The agent can point at a reference, and cannot draw a distance on one.** An
  agent ref mark exists. A **span** — the two-ended mark `contour measure --span`
  reads — can only be drawn by the user.
- **"Measure, never recall" cannot be checked.** A proposed number looks the same
  whether it came from `contour measure` or from an impression.

The request was for the agent to do more of the interpreting. The constraint is
ADR 0017's evidence: the agent must not become the source of a number.

## Decision

1. **The agent does more inside a run, and nowhere else.** No command calls a
   model. `console/agent.py` stays the only file that does, so every reading the
   agent makes happens under a space's rules, gates and **spend** accounting.

2. **An agent span's ends are snapped.** The agent never types a pixel for an
   end. It names a measurement and picks from what that measurement found: *the
   gap between these two runs*, *this colour's left edge to its right*. Code
   places the ends. A scanline finds runs and cannot know which two the question
   was about (ADR 0018); the agent answers *which*, and nothing else.

3. **By eye is the labelled fallback.** Where nothing can be snapped to — a
   photograph of a real object, a soft gradient — the agent may place an end
   freely. The span says it was placed **by eye**, and its error bar does not
   pretend to cover the placing.

4. **Spans are the record, until a scaffold exists.** ADR 0017's `scaffold.yaml`
   stays unbuilt. A snapped span stores the question that placed it, not only
   where it landed. That is ADR 0017's re-runnable basis, and it lets a scaffold
   be generated from the spans later without re-measuring.

5. **An agent span is a question, and the user answers it.** A user's ref mark
   says *here is what I meant*; an agent span asks *is this what you meant?*
   Three answers:
   - **Adopt**: it is right, and it is the user's from then on.
   - **Correct**: the user moves its ends. It becomes their span, and keeps the
     fact that the agent drew it first.
   - **Reject**: it measured the wrong thing. It is closed with the user's one
     line of why, and its number is not used.

   Drawing one needs no gate: it is appended to `marks.json` and never touches
   `refs/`, so rule 1 is not engaged by the asking.

6. **An unanswered span's number is the agent's.** A number from a snapped agent
   span may be proposed for the spec, named as the agent's own reading, beside
   the id of the span it came from. A number from a by-eye span may not be
   proposed until the user has answered that span. This extends the rule the
   new-space flow already has: every number the agent chose is listed back as the
   agent's.

7. **A number from a reference names its source.** There are three:
   - a span, the user's or the agent's;
   - the user, who gave it;
   - *not measurable*, said plainly, as for a depth hidden behind the body.

   A number claimed from the references with no span behind it is not a valid
   proposal. This holds when a spec is drafted, and when a revision is argued.

8. **The agent sees its spans once, on the worksheet.** `contour worksheet`
   draws the spans onto the references as one combined image. It enters the
   conversation at a **checkpoint**: when the agent believes its reading is
   finished, and before it proposes a number from it. It is a new file, and never
   a write to `refs/`.

9. **Rule 1 gains a clause when the mechanism lands, not before.** The wording
   the user approved on 2026-09-30:

   > A measurement read off a reference is a **span** — the user's, or an agent
   > span — and the proposal names it. A number from a reference with no span
   > behind it is not an argument, and a by-eye agent span argues nothing until
   > the user has answered it.

   It is written into `CLAUDE.md`, and into the space template, in the slice that
   makes agent spans drawable. Until then an agent cannot draw a span at all, and
   a rule naming a mechanism that does not exist would stop every agent proposing
   anything.

## Consequences

- The agent's semantic mistakes become visible, not impossible. A span snapped
  hand to hand and labelled *leg spacing* is exact arithmetic on the wrong thing.
  What changes is that the user can see it: the proposal names the span, and the
  span is on the picture.
- ADR 0017's scaffold is set aside, and its worksheet is revived with a
  different input: spans, where ADR 0017 had scaffold entries.
- Values that nothing can measure still live in `NOTES.md`. The scaffold was to
  hold them as `assumed`. Decision 7's third source makes them visible in a
  proposal, and nowhere durable.
- The worksheet costs about what a sheet costs, once per reading. That is the
  price of the agent checking its own spans, and the user chose to pay it.
- A closed span is pruned from `marks.json` after a release, as any closed mark
  is. Git holds it under the tag. A reading that must outlive that is the case
  for the scaffold.

## Rejected

- **Free pixel coordinates for every span.** Flexible, and it works where nothing
  snaps. Rejected as the default because the error bar would cover the arithmetic
  and not the placing, which is the step ADR 0017 measured at 14% out.
- **Snapped ends only, with no fallback.** Rejected on ADR 0017's own note: on a
  photograph of a real chair the colour queries do not work.
- **The user's answer required before any agent number is proposed.** Safest.
  Rejected as a second gate in front of rule 1's confirm, for the numbers least
  likely to be wrong.
- **The agent never sees its spans.** Free, and it keeps pictures with the user,
  who is the better judge of them. It was the recommendation. The user chose the
  checkpoint worksheet instead, accepting its cost.
- **The worksheet after every span.** Rejected on cost, and because it asks the
  part that errs to check itself repeatedly.
- **Building the scaffold now, fed by spans.** Durable and complete. Rejected for
  now as a second artifact and a second write path before anything needs the
  values a span cannot hold.
- **A command that calls a model to read a reference.** Rejected: it puts a model
  call in the launcher for the first time, outside every gate and every spend
  record, and the numbers a model reads off a picture are what ADR 0017 found
  wrong.
- **Guessing the anchor, spans on the sheet, and a build-against-references
  report.** The anchor is never guessed (ADR 0016). The build is geometry, and
  verify measures it exactly. The report needs each span tied to a named
  dimension, which is the scaffold.
