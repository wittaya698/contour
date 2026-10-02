# 37 — Create a space from the lobby

**Type:** AFK · **Source:** [ADR 0021](../adr/0021-the-lobby.md) decision 4

## What to build

The **lobby**'s create action, which is also the empty state's one real action:
*name your first model*.

It asks for a name and a location, defaulting to `project/`, and runs
`contour init` there. It then enters the new space (slice 36), with the
new-space flow as the console's first prompt: get the intent, save the
references, ask for the **anchor**, draft the spec with every self-chosen number
flagged.

The lobby **never drafts a spec itself**. A run belongs to one space, and a spec
drafted outside a space's gate is what rule 1 exists to prevent. The drafting
happens in the console, under its gates and its ask-list.

This needs the console to accept a first prompt it did not get from its own page.
Add that as narrowly as possible: the prompt is shown in the **transcript** as
the run's first line, like any other.

## Acceptance criteria

- [x] Create makes a space identical to what `contour init` makes by hand, then opens its console
- [x] The console's run starts with the new-space prompt, visible in its transcript
- [x] With no console environment, create still makes the space, and says how to continue from a terminal
- [x] An illegal or taken name is refused before anything is made
- [x] With no spaces, the empty state offers create as its primary action

## What it came to

- **The command is the contract (ADR 0021, decision 3).** The lobby runs
  `contour init <name> --to <dir> --new --json` and passes its answer back.
  `init` now refuses, before it writes anything: an illegal name (the rule
  `rename` already held, moved to `lib/space.py` so both read one copy); a
  name a live space already has, as `restore` already refused; and, with
  `--new`, a directory that exists. Without `--new`, `init` in a terminal
  still adopts an existing directory, as before. **The illegal-name refusal
  is new in the terminal too:** `contour init "Oak Chair"` used to succeed.
- **`--to <dir>`** makes the folder only after every refusal, since
  `project/`, the default, does not exist on a fresh clone. The lobby offers
  `project/` when it looks there, and otherwise the first place it does look.
  It refuses a location outside the places it looks, because the new space
  would never appear in its list.
- **The console's first prompt is a flow's name, never its text:**
  `contour-console --begin new-space`. The prompt lives in
  `console/server.py`; an unknown flow is refused before anything is served.
  It names the steps (intent, `refs/`, the anchor, `spec.yaml` with every
  self-chosen number flagged and proposed before it is written), and points
  at the toolkit's `new-space` skill, which is not copied into spaces. The run
  starts as the console starts, so the prompt is the transcript's first line.
- **With no console environment** the space is still made, and the answer's
  `next` gives the line that makes the environment, then the `--begin`
  command from inside the space.
- The empty state's first action is now the create form, with the
  `contour init` line kept beneath it; with spaces listed, the same form sits
  above the table.
- The test stand-in agent gained a `keep_prompt` step, because a console the
  lobby starts never tells anybody its URL, so its transcript cannot be read.

## Blocked by

- [36](36-enter-a-space.md)
