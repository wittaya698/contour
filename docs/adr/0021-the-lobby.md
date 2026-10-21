# 0021 — The lobby: a page above the spaces

**Status:** Accepted · 2026-10-02 · **decision 4 amended by [ADR 0033](0033-create-carries-a-said-anchor.md)** (a new-space console may be begun with a said anchor, as a value)

> **Accepted on its tracer bullet, as drafted** (issue 33). `contour lobby`
> listed the spaces on this machine. A throwaway space was renamed end to end
> from the page: the proposal shown, the confirm, the row back as
> renamed-uncommitted, and `contour check` green afterwards with `revision:`
> bumped. A page left open on it made the same rename refuse, worded as
> `contour rename` words it. No decision moved.
>
> Two things the run showed, neither an amendment:
> - The page held open was `contour canvas`. `contour-console` writes the same
>   presence record through the same `presence.present`, so decision 8 covers
>   both, but only the canvas's was watched refusing.
> - `contour init` gives a space with no `spec.yaml` and no `build.py`, so a
>   fresh space has nothing to rename's bump or `contour check`'s build. The
>   bullet borrowed the smoke fixture's. That is decision 4 as drafted: the
>   spec is drafted in the space's own console, never by the lobby.
>
> Drafted as: *accept on a tracer bullet — `contour lobby` listing the spaces
> on this machine, and renaming a throwaway space end to end, the proposal
> shown, the confirm, a green `contour check` afterwards with `revision:`
> bumped, while a console left open on it makes the rename refuse.*

## Context

Every page Contour serves belongs to one space. `contour canvas` and
`contour-console` both walk up for `.contour/project` and refuse without one
(ADR 0015, ADR 0019). The set of spaces has only `contour spaces`, which derives
the list from the markers so that there is no registry to go stale.

Wanted: one place to create, rename, delete and enter spaces, which is also what
a person with no spaces yet is shown. Three facts, measured in `beaky` on
2026-09-29, shape it:

- **A space's name is its identity,** so renaming is not cosmetic. The directory
  is the name, `spec.yaml`'s `model:` must equal it, and the space's `CLAUDE.md`
  is headed with it. A rename is therefore a spec write.
- **The path is a key in two places outside the space.** The ask-list is keyed by
  path, and fails closed (open question 12). Claude Code files transcripts under
  `~/.claude/projects/<path>`, and `tools/tokens.py` derives that directory from
  the space's path, so a renamed space's **spend** history is orphaned.
- **A console holds a space only during a run** (`console/run.py`). An idle
  console or an open canvas holds nothing, and would keep writing to a path that
  a rename or delete has moved out from under it.

## Decision

1. **The lobby is one page, whose empty state is onboarding.** There is no
   separate first-run page: someone with no spaces is standing where someone with
   ten is.

2. **The launcher serves it, as `contour lobby`,** from the canvas's server,
   inheriting issue 01's secret, loopback bind and origin check. Listing,
   creating, renaming and deleting need only the standard library, so the lobby
   works on a bare clone. Entering a space is the one exception: it is a
   **capability**, `enter`, granted only where the console's environment exists.
   Where it is missing, the page shows the line that makes one. Entering spawns
   `contour-console` in that space, on its own port and in its own tab. Closing
   the lobby ends none of the consoles it opened.

3. **The contract is the command line, not the lobby's server.** Every lobby
   action is a `contour` command with a machine-readable output. The page is one
   client among any others, and the guards live once, in the command. The
   server stays private to its page: a random port and a per-session secret are
   what issue 01 bought, and a stable port with a stored token would be a
   credential and a daemon. A network API, if one is wanted, is its own process
   wrapping the CLI, decided against a real consumer.

4. **Creating a space runs `contour init` and hands over.** The lobby makes the
   space, defaulting to `project/`, and opens that space's console with the
   new-space flow as its first prompt. It never drafts a spec: a run belongs to
   one space, and a spec drafted with no space's gate over it is exactly what
   rule 1 exists to prevent. *Create a variation of X* is the same thing, with a
   first prompt that points at X's `spec.yaml` and `build.py` for reference and
   copies neither.

5. **Renaming shows everything before it does anything.** The lobby shows:
   - the directory move;
   - `model:` from the old name to the new;
   - `revision:` from N to N+1;
   - the `CLAUDE.md` header.

   It also names what the rename leaves behind: the ask-list key and the
   transcripts. The user starts the rename and confirms that diff, which meets
   rule 1: the diff is the proposal and the click is the confirm. The launcher
   writes it, not the agent. The rename does not commit (rule 5), and the lobby
   lists the space as renamed-uncommitted until the user's next approved commit.

6. **Deleting leaves a bundle.** The lobby writes a `git bundle` of every ref
   into a trash directory under `~/.contour/`, and removes the directory only
   once that has succeeded. It refuses anything a bundle cannot carry:
   uncommitted changes, or a **working file**. The user confirms by typing the
   space's name. Deleted spaces are listed, and restoring one is a clone of its
   bundle.

7. **Rename and delete take the space's hold,** so both refuse during a run and
   no run can start halfway through either.

8. **An open page announces itself.** A console or canvas session writes a
   **presence** record while it serves a space, with the same pid and host shape
   as the hold, and judged alive the same way. Presence stops nothing, so it is
   not the hold open question 11 declined to give a canvas. Only the lobby reads
   it, and refuses to rename or delete a space that a page is still open on. A
   terminal agent session leaves no presence, and the confirm says so rather
   than implying that the lobby checked.

9. **The first version is:** the list, with the health `contour spaces` and
   `contour doctor` already compute; create; create a variation; rename; delete;
   restore; enter; and open in Finder.

## Consequences

- Renames become easy, which is when paths-as-identity starts to cost something.
  The lobby makes that loss visible; it does not prevent it. An id in
  `~/.contour` that points at the path remains the fix (open question 12).
- The trash is on the same disk. It undoes a click, not a lost disk, so open
  question 6 is untouched.
- Refusing on `work/` will sometimes refuse a scratch file. That is the chosen
  error: a delete that can quietly lose work is worse than one that asks you to
  move a file first.
- The launcher gains `lobby`, a rename command and a delete command, and
  `contour spaces` gains a machine-readable output.

## Rejected

- **Hosting the lobby in `contour-console`**, run outside a space. The empty
  state would become the error screen, which is appealing. Rejected because
  listing spaces would then need the venv, and a console would stop meaning one
  session over one space.
- **Rename as a display label kept in `~/.contour`.** It is a second name that
  can disagree with the directory: the registry ADR 0015 rejected.
- **Deleting to the macOS Trash.** It keeps everything, but a tree copy is a
  space and lists as a live one (ADR 0015), and it works only on macOS.
- **Moving a space, exporting and bulk actions, from the lobby.** A move carries
  every problem a rename has, plus open question 13: outside `project/`, a space
  stops seeing the toolkit's rules. Export belongs inside a space, and rule 8
  keeps handing over a `.glb` a deliberate act. A bulk delete defeats typing the
  name.
- **Updating a space's scaffolding from the lobby.** The list says *behind*, and
  a button that rewrites a space's `CLAUDE.md` is a design of its own.
