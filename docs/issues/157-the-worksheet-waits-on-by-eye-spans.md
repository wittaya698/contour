# 157 — The worksheet waits on by-eye spans

**Type:** AFK · **Source:** ADR 0035, decisions 1, 2, 4, 5 and 6 — [A run waits on its by-eye spans](../adr/0035-a-run-waits-on-its-by-eye-spans.md)

## What to build

The tracer bullet: under an attended console, a `contour worksheet` call made
while by-eye agent spans are unanswered parks the run, as a form does. It is
answered where spans are answered today, the canvas panel; 158 brings the card
to the transcript.

- **The park** is the console's, before the call runs, on the by-eye agent
  spans that are unanswered and not yet asked about in this run. Snapped spans
  never park it.
- **It ends** when each of them is answered or skipped. *skip for now* is
  recorded for the run, so the park can count it.
- **The worksheet then runs**, and its output names each span's answer:
  adopted, moved with its new number, rejected with the user's line, or
  skipped and still not proposable.
- **A later worksheet in the same run** parks only on by-eye spans drawn
  since.
- **An unattended run never parks**: the worksheet runs, and says which spans
  are unanswered.
- **The run's activity line** says it waits on the user's answers to its
  spans, in the words the page uses.
- `NEW_SPACE` and the new-space skill's worksheet paragraph say the worksheet
  waits for the user's answers under a console, so the agent expects it.

## Acceptance criteria

- [ ] An attended run's `contour worksheet` with a by-eye span unanswered waits until it is answered
- [ ] With only snapped spans unanswered it does not wait
- [ ] Answered or skipped, the worksheet runs and its output gives each answer
- [ ] A skipped span does not park a later worksheet in the same run; a new span does
- [ ] An unattended run's worksheet never waits
- [ ] Ending the run while it waits ends the park, as it ends any gate

## Blocked by

- 156
