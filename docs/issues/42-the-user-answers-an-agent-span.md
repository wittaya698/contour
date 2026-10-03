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

- [x] Each of the three answers can be given from the canvas, under the launcher and under the console
- [x] An adopted span records that the user adopted it, and who drew it
- [x] A corrected span has the user's ends, a fresh answer in millimetres, and the record that the agent drew it first
- [x] A rejected span is closed, carries the user's reason, and says its number is not to be used
- [x] Reject without a reason is refused
- [x] No agent-side command can adopt, correct or reject; this is tested
- [x] The page distinguishes unanswered, adopted, corrected and rejected spans
- [x] Marks written before this slice load unchanged

## What it came to

- Three named transitions in `lib/marks.py`, beside `close`: `adopt`,
  `correct`, `reject`. One gate in front of all three: only an open agent span
  with no answer yet is a question. Anything else is refused as
  `{"refused": why}` and nothing is written. An adopted or corrected span is the
  user's, so it cannot be answered twice; a rejected one is closed.
- The canvas serves them as `POST /adopt {id}`, `/correct {id, pixel, to}` and
  `/reject {id, why}`, in its own routes, so the console has them too: it serves
  the same canvas.
- The record:
  - adopted: `author: user`, `drawn_by: agent`, `answer: adopted`;
  - corrected: the user's ends, `agent_ends` holding the agent's, `drawn_by:
    agent`, `answer: corrected`, and no `placed` or `question` — the user placed
    it, so `--again` refuses it;
  - rejected: `status: closed`, `answer: rejected`, `why`, `unused: true`.
- A snapped span now keeps `scale` (mm per pixel, or None with no anchor) and
  `reading`, the id of the agent mark carrying its number. `marks.spanned`
  writes the two together in one save. A correction is read afresh at that
  scale, with no image read and no anchor asked again; its old reading is
  closed. A rejection closes the reading and marks it `unused` too.
- A span drawn before this slice has neither. It can still be answered; its
  reading is left alone, and a correction is answered in pixels, naming
  `contour measure --span` for millimetres.
- On the page an agent span is dashed and asks *is this what you meant?* with
  adopt, correct and reject beside it. Correct arms the next drag on that
  reference. Reject asks for one line. An answered span says which answer it
  got and who drew it; a rejected one says why, and that its number is not to
  be used. What these look like is a HITL check.
- The agent has no spelling: `contour mark` and `contour measure` take none of
  the three, and `lib/agent` and `lib/span` hold no name that answers. The
  correction's arithmetic lives on the canvas, not in `lib/span`, for that
  reason.

## Blocked by

- [40](40-a-snapped-agent-span-from-a-scanline.md)
