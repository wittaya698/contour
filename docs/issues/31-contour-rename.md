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

- [x] Without the confirming flag, nothing on disk changes, and the proposal lists all four changes and both things left behind
- [x] With it, the directory, `model:`, `revision:` and the `CLAUDE.md` header all carry the new name, and `contour check` in the renamed space passes its revision check, including when `spec.yaml` already had an uncommitted change
- [x] `contour doctor` in the renamed space reports no scaffolding drift from the rename
- [x] Each refusal (held, present, taken, illegal name) is tested, and leaves the space untouched
- [x] The rename is atomic in effect: a failure partway leaves either the old space or the new one, never a directory whose name disagrees with its spec
- [x] No commit is made in the space
- [x] Tests run against a throwaway space, with no Blender

## What it came to

`contour rename <name>` proposes; `--yes` does it; `--json` says the same
proposal for slice 32. `lib/rename.py` holds both halves, `propose` and
`perform`, and `perform` re-proposes under the hold it takes, so what is written
is what the proposal would have said at that moment.

- **The scaffolding, not just `CLAUDE.md`.** The skills carry the name too, so a
  rename that touched only the header would read as drift to `contour doctor`.
  A file still as the template wrote it is rewritten from the template; a
  drifted one keeps its body and gets the header, when the header is where the
  name is; anything else drifted is listed as *untouched*. On this machine that
  is the norm, not the edge: all four spaces have drifted skills.
- **A fifth refusal, not in the issue:** a spec that differs from HEAD with no
  bump. `contour check` is red then, and the rename's own bump would turn it
  green — an unconfirmed change passing as a confirmed one (rules 1 and 2). One
  that was already bumped goes through: HEAD 2, file 3, rename writes 4. The
  rule moved out of `lib/cli.py` into `lib/revision.py`, so check and rename
  ask it the same way; it had no tests of its own until now.
- **A legal name** is letters, digits, `-` and `_`, starting with a letter or
  digit, at most 64. No dot, because Claude Code respells dots in the
  transcript path. `init` still accepts anything; nothing has asked it not to.
- **Atomic in effect:** files are written first, the directory moves last, and
  a failure anywhere writes back what was already written. Tested by making the
  parent read-only, so the move fails after the writes.
- **The hold is taken by the command, not by `main`** (`holds` is False in the
  table): the lock file moves with the directory and is released at the new
  path. It is taken as no run's member, so a rename inside `contour run` is
  refused rather than moving the directory under that run's own agent.
- **`spec-write`** is its intent, so under a console an agent reaching for it
  meets the spec's gate.
- The transcript directory moved from `tools/tokens.py` into `lib/space.py`,
  one definition of the second path key; `policy.names` says whether the
  ask-list has an entry for a path, which is the one it leaves behind.
- Found on the way: `revision.FIELD` ends in `\s*$`, which eats the newline
  when `revision:` is a spec's last line. Right for reading, wrong for
  rewriting, so the rename rewrites by line.

## Blocked by

- [30](30-an-open-page-leaves-a-presence.md)
