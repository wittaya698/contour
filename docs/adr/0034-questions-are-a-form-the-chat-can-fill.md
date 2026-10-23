# 0034 — The agent's questions are a form, and a chat can fill it

**Status:** Accepted · 2026-10-23 · **amends ADR 0027 decision 12, ADR 0028 decisions 2 and 6, ADR 0024 decision 3, ADR 0033 decisions 3 and 4, and rule 1's sources** ([0027](0027-the-unattended-run.md), [0028](0028-approvals-wait-and-the-run-goes-on.md), [0024](0024-the-connector-desktop-reads-and-opens.md), [0033](0033-create-carries-a-said-anchor.md))

> **Accepted as drafted, 2026-10-23** (issue 146).

## Context

A new space's console opens by asking the user what the thing is, how big it
is, where it will be seen and what parts it has. On 2026-10-22 a run asked six
such questions as prose in its closing message, and stopped. Prose is one block
to the page: it cannot tell where one question ends, which part is a guess, or
where an answer goes, so the user retyped everything in one reply. Some of the
answers the agent could have guessed well: *the antenna is probably a separate
part*. One question asked the user for a tolerance, which the new-space skill
forbids.

The user is often not on that page. A space made from a Desktop chat opens its
console in a tab while the conversation goes on in the chat, and the chat cannot
see the questions or carry answers back. ADR 0027 decision 12 lets a chat read
a waiting question and never answer it, because an answer becomes intent. ADR
0033 found the way through for one number: what the chat says comes back as a
suggestion, and only what the user confirms on the page counts. This applies
the same rule to every question the agent asks.

## Decision

**1. Under a console, the agent asks with `ask`, and only with `ask`.** `ask`
is a console tool, as `spec_write` is (ADR 0029). Each question carries its
text, a suggested answer, the suggestion's basis, and optionally `is_size`,
which marks the question whose answer is the anchor's millimetres. A suggestion
with no basis is refused, as a spec write with no case is. `AskUserQuestion` is
refused with *under this console a question is asked with `ask`*, so no
question skips the form. A question left in a closing is a defect of the prompt
that let it, not something the page parses.

**2. The page shows the questions as a form, every field already filled, and
one Approve takes it all.** Each field is labelled with where its text came
from: *Claude's guess*, *from the chat*, or *yours*. Editing a field makes it
yours. Under an attended run the run waits at the form, and Approve hands it
the answers. Under an unattended one the form is set aside as a question is
(ADR 0028 decision 2), and approving it starts a run whose first message is the
questions and the answers. Nothing waiting times out.

**3. Yours beats the chat's, and the chat's beats Claude's guess.** A relay
never overwrites a field the user edited. A later relay replaces an earlier
one. A relayed answer identical to Claude's guess stays labelled *Claude's
guess*: the agreement says nothing the page can check.

**4. The size may be suggested, and an approved guess keeps its name.** The
approved answers are kept with their sources in the space's `.contour/`,
beside the approvals. When the anchor's millimetres came from an approved
guess, the anchor span's question says so: *is this the 150 mm height you
approved from Claude's guess?* Rule 1 gains a fourth source for a number,
*Claude's guess, approved*, beside a span, the user, and *not measurable*, and
a spec write's case names it.

**5. A chat reads the questions without the suggestions, and fills fields with
`answer`.** `status` carries a waiting form's questions and their ids, and
never Claude's guesses, so a chat cannot hand a guess back as the user's. A new
connector tool, `answer`, takes a space, a form's id and one text per question,
and fills fields as *from the chat*. It approves nothing and starts nothing.
A form already approved, or gone, refuses it in plain words. Its description
says the user approves on the page, so the chat never says the questions are
answered.

**6. A size the chat said is a field the chat filled.** ADR 0033's `--said`
stays on the launch line, since `create` comes before any form exists. The
console fills the `is_size` field from it, as *from the chat*, and the sentence
ADR 0033 decision 4 added to the new-space prompt is withdrawn.

## What this does not cover

- **Agent spans and directions** (ADR 0022, issues 139 and 140). Their answer is
  a place on a picture. They stay on the canvas.
- **Gates and approvals** (rule 1, rule 5, ADR 0028, ADR 0030). These confirm an
  act and its case. ADR 0028 decision 6 stands for them: a chat never answers
  one.

## Consequences

- A new space's questions are answered by reading a filled form and pressing
  one button, instead of retyping six answers in prose.
- A wrong guess can be approved without being read. For most answers the first
  render shows it. For the size it shows nowhere, because every dimension is
  wrong by the same factor and the checks stay green (ADR 0016), so the
  anchor span's question names it as a guess a second time.
- The connector has eleven tools.
- Rule 1 and the new-space skill stop saying the anchor is never guessed. They
  say a guessed anchor is the user's only once approved, and is named as a
  guess wherever it is used.

## Rejected

- **Suggestions beside the field, taken one click at a time.** Slower, and the
  user chose speed. The labels and decision 4's trace are what keep a guess
  visible instead.
- **A separate tick for a guessed size.** Rejected for one Approve. Decision 4's
  anchor span question is the second look.
- **Showing the chat Claude's guesses.** A chat would hand them back unasked,
  and the label that said *guess* would be lost.
- **Folding `answer` into `request`.** A tool that both answers and starts runs
  is one a model calls wrongly (ADR 0027 decision 5's reason for `stop`).
- **Extending `AskUserQuestion` by convention.** Its fields are fixed. A
  suggestion would be *the first option, marked Recommended*, nothing could
  require a basis, and nothing could mark the size.
- **Relaying spans, gates or approvals.** See *What this does not cover*.
