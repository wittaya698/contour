# 34 — Delete leaves a bundle

**Type:** AFK · **Source:** [ADR 0021](../adr/0021-the-lobby.md) decisions 6, 7, 8

## What to build

Deleting a model space: as a `contour` command, and as an action in the **lobby**
that runs it.

A space holds the one input nothing can regenerate, its `refs/`, and no backup of
it exists yet (open question 6). So a delete **leaves a bundle**: a `git bundle`
of every ref, written to a trash directory under `~/.contour/`, named for the
space and the date. The directory is removed only once the bundle has been
written and verified. Never a copy of the tree: a copy of a space is a space, and
would list as a live one (ADR 0015).

**It refuses, naming the reason, when anything would be lost that a bundle cannot
carry:**
- uncommitted changes, which it lists;
- a **working file** under `work/`;
- the space being held by a run;
- a live **presence** on the space.

It takes the space's hold while it works. It never commits to make a space
deletable (rule 5).

In the lobby, the user confirms by **typing the space's name**. The confirm says
the bundle is on the same disk, so it undoes a click, not a lost disk. It also
says that a terminal agent session cannot be seen.

## Acceptance criteria

- [ ] A deleted space leaves a bundle that clones to a byte-identical tree of everything tracked, `refs/` checksums included
- [ ] If the bundle cannot be written or verified, the space is untouched
- [ ] Each refusal (uncommitted changes, `work/`, held, present) is tested, and leaves the space untouched
- [ ] The trash is not walked by the space scan, so a deleted space never lists as live
- [ ] The page's delete is enabled only once the typed name matches
- [ ] The command has a machine-readable form, and the page shows its refusals as worded
- [ ] Tests run against throwaway spaces, with no Blender

## Blocked by

- [33](33-accept-adr-0021.md)
