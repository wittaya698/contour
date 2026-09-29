# 31 — `contour rename`: it proposes, then does the rename

**Type:** AFK · **Source:** [ADR 0021](../adr/0021-the-lobby.md) decisions 5, 7, 8

## What to build

A command that renames a model space, usable from a terminal alone. A space's
name is its identity, so renaming changes four things together:
- the directory;
- `spec.yaml`'s `model:` field;
- `spec.yaml`'s `revision:`, bumped;
- the space's `CLAUDE.md` header.

**It proposes before it acts.** Without a confirming flag it changes nothing and
prints the proposal: each of the four changes, from what to what. It also names
what the rename will leave behind:
- the ask-list entry for the old path, when there is one; the renamed space then
  fails closed to the strictest list (open question 12);
- the Claude Code transcripts filed under the old path, and with them the space's
  **spend** history.

A machine-readable form of the proposal serves the lobby (slice 32). With the
confirming flag, it performs the proposal it would have printed.

**It refuses, naming the reason, when:**
- the space is held by a run;
- the space has a live **presence** (slice 30);
- the new name is taken, or is not a legal space name.

A terminal agent session in the space cannot be detected, and the proposal says so
rather than implying it checked.

**It takes the space's hold** while it works, so no run can start halfway through.

**It does not commit** (rule 5). The rename is a spec write, and rule 1's propose →
confirm is met by the proposal and the confirming flag. The user starts it, and
the launcher writes it, not the agent.

## Acceptance criteria

- [ ] Without the confirming flag, nothing on disk changes, and the proposal lists all four changes and both things left behind
- [ ] With it, the directory, `model:`, `revision:` and the `CLAUDE.md` header all carry the new name, and `contour check` in the renamed space passes its revision check, including when `spec.yaml` already had an uncommitted change
- [ ] `contour doctor` in the renamed space reports no scaffolding drift from the rename
- [ ] Each refusal (held, present, taken, illegal name) is tested, and leaves the space untouched
- [ ] The rename is atomic in effect: a failure partway leaves either the old space or the new one, never a directory whose name disagrees with its spec
- [ ] No commit is made in the space
- [ ] Tests run against a throwaway space, with no Blender

## Blocked by

- [30](30-an-open-page-leaves-a-presence.md)
