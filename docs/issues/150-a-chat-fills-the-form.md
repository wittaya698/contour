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

- [ ] `status` on a space with a waiting form lists its questions and no suggestion
- [ ] `answer` fills fields labelled *from the chat*, and the form still waits for Approve
- [ ] `answer` never overwrites a field labelled *yours*
- [ ] `answer` on an approved or missing form is refused, and nothing changes
- [ ] Looked at from Desktop: questions relayed, answered in the chat, and seen filled on the page

## Blocked by

- 147
