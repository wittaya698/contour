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

- [ ] Create makes a space identical to what `contour init` makes by hand, then opens its console
- [ ] The console's run starts with the new-space prompt, visible in its transcript
- [ ] With no console environment, create still makes the space, and says how to continue from a terminal
- [ ] An illegal or taken name is refused before anything is made
- [ ] With no spaces, the empty state offers create as its primary action

## Blocked by

- [36](36-enter-a-space.md)
