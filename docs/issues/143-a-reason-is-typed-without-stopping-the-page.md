# 143 — A reason is typed without stopping the page

**Type:** AFK · **Source:** verifying 136, 2026-10-18

## What to build

*Wrong thing…* on the card, and *reject* in the list, asked for the reason
with the browser's `prompt()`. A browser stops a page's script while one of
those boxes is open, and the heartbeat stops with it. Ten seconds of
silence from a tab on screen is a closed tab to the console, so a reason
that took longer than that to type ended the console, and the answer
never arrived. Found when the console stopped under a person answering;
unseen until then because the headless checks answered `prompt()` themselves.

- **The reason is asked for in the page.** *Wrong thing…* opens a one-line
  field with *Reject* and *Cancel* on the card. The list's *reject* brings
  its span onto the card with the field open, as its *correct* brings Save
  and Cancel, so a list redrawn while it is typed cannot lose the reason.
  Enter sends it, Escape cancels.
- **Nothing blank is sent.** *Reject* waits for a reason, as the server's
  refusal already does.
- **No blocking dialog anywhere in the page**, so nothing stops the beat.

## Acceptance criteria

- [x] The page has no `prompt()`, `confirm()` or `alert()`
- [x] A reason is typed on the card or in the list, and sent as before
- [x] Reject waits for a reason; Cancel and Escape leave the span a question

## Blocked by

None - can start immediately
