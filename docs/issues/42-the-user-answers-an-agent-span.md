# 42 — The user answers an agent span

**Type:** AFK · **Source:** ADR 0022 decision 5 — [the agent reads the references in spans](../adr/0022-the-agent-reads-the-references-in-spans.md)

## What to build

An **agent span** is a question: *is this what you meant?* This slice gives the
user the three answers, on the canvas, wherever the canvas is served.

- **Adopt.** It is right. The span is the user's from then on.
- **Correct.** The user drags an end. The span becomes theirs, keeps the fact
  that the agent drew it first, and is measured again from where the ends now
  are. It is no longer **snapped**: the user placed it, and a user's span is
  their intent.
- **Reject.** It measured the wrong thing. The user gives one line of why; the
  span is closed, and its number is marked as not to be used.

Each answer is a named transition on the mark record, beside the ones that exist,
so the lifecycle stays enforced in one place. Only the user can give one. The
agent has no spelling for any of the three, as it has none for closing a mark.

An unanswered agent span looks unanswered on the page, and an answered one shows
which answer it got.

## Acceptance criteria

- [ ] Each of the three answers can be given from the canvas, under the launcher and under the console
- [ ] An adopted span records that the user adopted it, and who drew it
- [ ] A corrected span has the user's ends, a fresh answer in millimetres, and the record that the agent drew it first
- [ ] A rejected span is closed, carries the user's reason, and says its number is not to be used
- [ ] Reject without a reason is refused
- [ ] No agent-side command can adopt, correct or reject; this is tested
- [ ] The page distinguishes unanswered, adopted, corrected and rejected spans
- [ ] Marks written before this slice load unchanged

## Blocked by

- [40](40-a-snapped-agent-span-from-a-scanline.md)
