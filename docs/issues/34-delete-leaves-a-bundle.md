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

- [x] A deleted space leaves a bundle that clones to a byte-identical tree of everything tracked, `refs/` checksums included
- [x] If the bundle cannot be written or verified, the space is untouched
- [x] Each refusal (uncommitted changes, `work/`, held, present) is tested, and leaves the space untouched
- [x] The trash is not walked by the space scan, so a deleted space never lists as live
- [x] The page's delete is enabled only once the typed name matches
- [x] The command has a machine-readable form, and the page shows its refusals as worded
- [x] Tests run against throwaway spaces, with no Blender

## What it came to

- `contour delete <name>` proposes and writes nothing; `--yes` deletes;
  `--json` says either for a client. The name is the confirm, the command
  line's spelling of typing it, and the command checks it: always the first
  word, so a typed `--yes` is a wrong name and never a confirm.
- The bundle goes to `~/.contour/trash/<name>-<date>.bundle` (`-2`, `-3` on a
  second delete that day). `git bundle create --all`, then proved twice: git
  verifies the file, and its heads must be every ref the space has. Only then is
  the tree removed. A removal that stops partway says where the bundle is.
- Refuses, naming the reason: not the space's name; held by a run; a page
  open (the held and open wording is now one function in `presence`, shared
  with `rename`); uncommitted changes, listed, untracked files included; a
  working file under `work/`; git unable to say whether anything is
  uncommitted.
- The trash holds only files, so the space scan never takes one for a space,
  even pointed at the trash itself.
- The lobby offers `delete` as a capability; `/delete` with no name returns the
  proposal, and with the typed name runs `--yes`. The page's button stays
  disabled until the typed value matches exactly, and shows the bundle, the
  same-disk caveat, what is not kept (`out/`, `exports/`) and the terminal
  session it cannot see, before the button.
- The console's gate reads it as `ref-write`, because a delete removes `refs/`.
  During a console run it is refused anyway, since the run holds the space.

## Blocked by

- [33](33-accept-adr-0021.md)
