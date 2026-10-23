# 150 — A chat fills the form

**Type:** AFK · **Source:** ADR 0034, decision 5 — [The agent's questions are a form](../adr/0034-questions-are-a-form-the-chat-can-fill.md)

## What to build

The relay: a Desktop chat reads a waiting form's questions and fills its
fields. It never approves.

- **`status` carries a waiting form**: its id and each question's id and text.
  Never `suggested` or `basis`.
- **`answer`, the connector's eleventh tool**: space, form id, and one text per
  question id. It fills fields as *from the chat*, never over a field the user
  edited, and a later relay replaces an earlier one. A form already approved,
  or not there, refuses it in plain words. It starts nothing.
- **Its description says the user approves on the page**, so a chat does not
  tell the user the questions are answered.
- **The connector's instructions** say a chat may relay the questions and fill
  answers the user gave it, and never invents one.
- README's connector paragraph says so.

## Acceptance criteria

- [x] `status` on a space with a waiting form lists its questions and no suggestion
- [x] `answer` fills fields labelled *from the chat*, and the form still waits for Approve
- [x] `answer` never overwrites a field labelled *yours*
- [x] `answer` on an approved or missing form is refused, and nothing changes
- [x] Looked at from Desktop: questions relayed, answered in the chat, and seen filled on the page

## Blocked by

- 147

## Found on Desktop (2026-10-23)

Questions were relayed, answered in the chat, and seen filled on the page.
Told only *300 mm long*, the chat filled the size field with that, plus a
diameter of its own and a note saying the user gave only the length. It kept
doing so after `answer`'s description and the instructions were tightened:
no notes or sources, no value the user did not say, and only the part they
answered.

**Left as a known limit.** The console never sees the chat, so it cannot check
a relayed text against what the user said. What protects against it is the
same as for Claude's guesses (ADR 0034): the text is on screen, labelled
*from the chat*, before the one Approve; the agent is told *from the chat* and
never *yours*; and a number reaches the spec only through a spec write that
names its source. The risk is an Approve given without reading, which ADR 0034
already accepted for guesses.

**If a chat ever relays a wrong size**, the size question's `answer` should
take a value, `{"dimension", "mm"}` as `create`'s anchor does, and the console
words the field itself. A value cannot carry a second number or a note.
