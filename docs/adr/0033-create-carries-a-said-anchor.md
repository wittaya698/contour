# 0033 — `create` carries what the chat said the anchor is, and the console asks it

**Status:** Accepted, amended · 2026-10-22 · amended by [ADR 0034](0034-questions-are-a-form-the-chat-can-fill.md) (the said size fills the form's size field) · **amends ADR 0024 decision 10 (`create` writes nothing else) and ADR 0021 decision 4 (a console is begun on a flow's name, never on words)** ([0024](0024-the-connector-desktop-reads-and-opens.md), [0021](0021-the-lobby.md))

> **Accepted as drafted, 2026-10-22** (issue 144).

## Context

A Desktop chat that makes a space from pictures usually already knows how big
the thing is: the user said so while asking. *Make a model of this megaphone,
it's about 300 mm wide.* `create` takes a name and reference paths, and nothing
else (ADR 0024 decision 10), so the number stays in the chat. The console opens
on the new-space flow and asks *How big is it in real life?* again, and the user
types again what they already said.

The obvious fix would be for `create` to take the size, and to note who
approved it, so the console could treat it as settled. That fails on where the
number comes from. A tool argument is text the Desktop model wrote, which is
the same reason a picture pasted into the chat is never a reference (ADR 0024
decision 10). *About two metres* can arrive as `2000`, or as `height` where the
user meant length. A field saying the user approved it is the model vouching
for the user, and nothing downstream can check that. Desktop's per-call Allow
approves the call as a whole, and is often clicked without reading the
arguments. ADR 0027 decision 12 already turned down the same thing from the
other side: *the anchor is 300 mm*, given by an agent, reaches a spec write
whose gate shows the diff and not where the number came from. Rule 1 says
scale needs an anchor the user gives.

The number is also only half of an anchor. Since issue 139, an anchor is one
real dimension *and* the span on each reference that it is the length of. That
span is proposed and answered on the canvas. The console has to ask whatever
`create` passes in, so the useful thing `create` can carry is a suggestion that
question opens with.

## Decision

**1. `create` takes an optional `anchor`: a dimension and its millimetres.**
`{"dimension": "width", "mm": 300}`. The dimension is one of the overall three
the schema names: `height`, `width`, `depth`. The millimetres are a positive,
finite number. Anything else is refused before anything is made, as a bad
reference path is, so a bad anchor never leaves half a space. A part's
dimension, such as `seat_height`, is not taken: before a spec exists there are
no named parts for it to belong to.

**2. It is what the chat said, never what the user stated.** Nothing about it
says who approved it, because nothing could make that true. `create` still
writes nothing but `refs/`. The anchor is not written into `spec.yaml`,
`marks.json` or any file in the space. It is carried only on the console's
launch line.

**3. The launch line carries it as a value, and the toolkit writes the words.**
`--begin new-space --said width:300`. `lib/enter.console` passes it on; the
launcher parses it back to a dimension from the fixed three and a number, and
refuses anything else. `console/server.py` turns it into the toolkit's own
sentence, added to `NEW_SPACE` step 1. This keeps what ADR 0021 decision 4
protects: no launch line carries words someone else wrote into the prompt. A
dimension from a fixed set and a number are not words.

**4. The console asks the question with that number as the suggestion.** The
sentence it adds tells Claude what the chat said and how to treat it: *In the
Desktop chat that made this space, the user was understood to say it is 300 mm
wide. That is what another model wrote, not something the user told you. Ask
whether it is right — "Is it 300 mm wide, as you said in the chat?" — and take
only their answer here as the anchor.* Only the user's answer in the console
counts as the anchor's millimetres. The anchor span is then proposed and
answered as any agent span is (issue 139). A user who corrects it, *no, 320*,
has stated 320, and the chat's 300 is gone.

**5. With no console environment, the terminal instruction carries it too.**
`create` already says how to go on from a terminal when it cannot start a
console. That instruction includes `--said`, so the suggestion is not lost.

## Consequences

- The user is asked once more than strictly necessary, and answers with one
  word instead of retyping a size. Typing it twice is what this saves; the
  question itself is the point and stays.
- No chat can set a scale. The worst a misheard number does is suggest a
  wrong size, which the user sees in plain words and corrects.
- The connector's tool list grows by one optional argument, not a tool, and
  stays inside ADR 0024 decision 3's budget.
- `create`'s answer says the anchor was passed on as a suggestion, so the chat
  does not tell the user the size is set.

## Rejected

- **An `approved_by` field, or any other provenance.** The model would be
  vouching for the user. Nothing can check it, and it would make a guess look
  confirmed.
- **Writing a draft `dimensions` block at create.** That would be the spec
  write ADR 0024 decision 10 refuses, from a number nobody here has confirmed.
- **Desktop's Allow prompt as the confirmation.** It approves the call, not
  each argument, and it happens in a place where `contour` can't see who
  clicked it.
- **Free text on the launch line, such as *"the user said about 30 cm across"*.**
  That would be words someone else wrote going straight into the prompt, which
  ADR 0021 decision 4 rules out. A value the toolkit puts into its own
  sentence carries the same help.
- **Not deciding: the lobby's create form asking the size.** Typed on the
  lobby page it would be the user's own word, which is a different case from
  this one. Left for when someone wants it.
