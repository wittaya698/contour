# 0035 — A run waits on its by-eye spans

**Status:** Accepted · 2026-10-23 · **amends ADR 0022 decision 8 (the checkpoint waits for the user), and adds to ADR 0034 (a second place a run waits on the user's answers)** ([0022](0022-the-agent-reads-the-references-in-spans.md), [0034](0034-questions-are-a-form-the-chat-can-fill.md))

## Context

On 2026-10-23 a new-space run, checking issue 151, measured a photo of a
walkie-talkie. Nothing snaps on a photo, so it placed all seven spans by eye.
It looked at them once on the worksheet, as ADR 0022 decision 8 asks, and went
straight on to propose the spec.

ADR 0022 decision 6 says a by-eye span argues nothing until the user has
answered it, so the spec could carry only the height, the size the user had
approved. Its case held back the width, the grille, the knobs, the antenna base
and the button strip: *not proposed until you answer m3 on the canvas*. The
seven questions that would have unlocked them were in the picture panel above
the transcript, where the user had to scroll to find them. Meanwhile the run
waited at the bottom, on a spec gate that was half the spec. Answering the
spans afterwards means a second spec write and a second confirm, for numbers
the run could have had before the first.

The form (ADR 0034) already solved this for words: the run stops where the
user is, and goes on with the answers. Spans are the same kind of question with
a different answer, a place on a picture, and nothing made the run wait for
them.

## Decision

**1. Under an attended console, the worksheet checkpoint waits on the run's
by-eye spans.** `contour worksheet` called while by-eye agent spans are
unanswered does not run yet. The run parks, as it does at a form. The
checkpoint is the one ADR 0022 decision 8 already places *when the agent
believes its reading is finished, and before it proposes a number*, so no new
tool is needed, and the agent does not have to remember to ask.

**2. Only by-eye spans park the run.** A snapped span's number may be proposed
unanswered, named as the agent's reading (ADR 0022 decision 6). Making the run
wait for it is the second gate that ADR 0022 rejected, so snapped spans stay
answerable on the canvas as they are.

**3. The span's card is shown where the run waits.** It is the canvas's own
card, in the transcript at the park: the picture zoomed on the span, its
question, *Yes, that's it*, *Let me move it*, *Wrong thing…* and *skip for
now*, one span at a time. The panel shows the same state, and an answer in
either place is the answer in both.

**4. The park ends when each span it asked about is answered or skipped.**
Then the worksheet runs, and its output tells the agent each answer: adopted,
moved with its new number, rejected with the user's line of why, or skipped. A
skipped span stays unanswered, so its number still cannot be proposed.

**5. A park asks about each span once per run.** A later worksheet in the
same run parks only on by-eye spans drawn since. A skipped span is still
answerable on the canvas, and a new run asks about it again.

**6. An unattended run does not park.** Nobody is there to answer, and a span
already waits in `marks.json` without being set aside. The worksheet runs as
it does today and says which spans are unanswered, and the agent proposes
only what it can argue (ADR 0028: the run goes on).

**7. A spec gate names the by-eye spans still unanswered.** The gate shows a
line such as *2 of Claude's spans are still unanswered: width (m3), grille
(m5). Their numbers are not in this spec*, with a way to their cards. It does
not stop Allow: rule 1's confirm is still the user's to give.

## What this does not cover

- **Snapped spans and directions.** See decision 2. A direction is answered
  on the canvas, as ADR 0032 has it.
- **A chat relaying spans.** ADR 0034's *What this does not cover* stands: an
  answer that is a place on a picture is given on the page.
- **The worksheet in a terminal session.** There the agent asks the user
  itself, in the conversation, and `contour canvas` already waits for them.

## Consequences

- A new space on a photo proposes its spec once, with every size the user has
  answered, instead of once without them and again after.
- The user answers spans where they are already looking, at the moment the
  answers are needed.
- A run on a photo stops twice before its spec, at the form and at the
  spans. Both are questions only the user can answer.
- `contour worksheet` under a console can take as long as the user does. Its
  park is a wait like any gate, and ends with the run like any gate
  (ADR 0031).

## Rejected

- **Proposing now and revising later.** Today's behaviour: two spec writes
  and two confirms for one contract, the first with half its numbers.
- **Ending the turn and saying so.** No mechanism needed, but the run ends,
  and the user has to restart it after answering.
- **A tool the agent calls to wait.** Explicit, but one more thing the agent
  can skip, as the run in issue 151 skipped the skill's rule.
- **Parking at the spec write.** It cannot be skipped, but the spec was
  already drafted without the answers, so it would have to be written again.
- **Parking on snapped spans too.** One stop for all of them, but it is the
  second gate ADR 0022 rejected, for the numbers least likely to be wrong.
- **A pointer in the transcript to the panel.** One place to answer, but the
  user still leaves the transcript to do it.
- **Parking again on a skipped span at every checkpoint.** Nothing slips by,
  but a span the user cannot judge yet would stop every worksheet.
