# 0026 — Update: a space's copies brought in step, where nobody edited them

**Status:** Accepted, amended · 2026-10-07 (proposed 2026-10-05) · **extends [ADR 0015](0015-model-spaces.md) (its copies gain a way back into step) and [ADR 0021](0021-the-lobby.md) (the lobby gains an action)**

> **Accepted on its tracer bullet, with decision 1 amended** (issue 82).
> Used by hand on 2026-10-07 over this machine's six spaces, every one of
> them behind, `beaky` on the rules of `72876fe`.
>
> - **The update:** `contour update` brought all six from their recorded
>   commits to `b20494a`, and left nothing alone.
> - **The lobby:** `beaky` was then put back on `72876fe`'s copies and
>   updated from its row. The preview was read first, it named the four copies
>   that had moved on, and the confirm replaced them. The row then said
>   *updated, not saved yet*, and the marker said `45faa31`, which only the
>   lobby's run could have written.
> - **The agent:** a run in `beaky`'s console afterwards spoke ADR 0025's
>   plain words. The user's verdict: "everything looks good".
> - **The model:** the row still said *matches the spec*, and `beaky`'s check
>   stayed green. Update changes rules, never the model (decision 5).
>
> **The amendment.** Decision 1 compared a copy against the template written
> for the space's *current* name. A space renamed before its template moved
> on breaks that: `rename` rewrites only what it must, so its untouched skill
> files still say the old name, and under the current name they read as
> edited. A copy is now unedited when it equals the old template written for
> **one name, used throughout**, whichever name that is. Two names in one file
> is still an edit.

## Context

ADR 0015 copies `CLAUDE.md` and `.claude/skills/` into each space, because the
agent reads them from the working directory, and names them as the only things
that can drift; `contour doctor` compares them against the toolkit. It reports.
Nothing brings a drifted space back: no command, no page.

Measured 2026-10-05: every space on this machine is behind. `contour spaces`
shows all six on an older toolkit commit than `master`, and `beaky`'s rules are
those of `72876fe`. Until now that cost nothing anybody noticed. ADR 0025
decision 2 changes the template's `CLAUDE.md` so the agent speaks in plain
words, and without a way to carry that into an existing space, the change
reaches only spaces made after it.

`lib/cli.py`'s `scaffold` says *drift* when a file differs from **today's**
template. That cannot tell a file the template moved on from apart from a file
somebody edited — and an edit to a space's own rules can be deliberate. But
`.contour/project` records the toolkit commit each space was made from, and the
toolkit's own git history holds the template as it was at that commit.

## Decision

**1. `contour update`, run inside a space, replaces only what nobody edited.**
A scaffold file is replaced when it still equals the template *as it was at the
toolkit commit the space records*, written for one name used throughout, as
`space.template` writes it today — read from the toolkit's git history, so
nothing new is stored. *(Amended: this said the space's current name; see the
status note.)* A file that differs from that was edited, and is named
and left alone. A missing file is written. The recorded toolkit commit moves to
the current one.

**2. A command first, the lobby second** (ADR 0021, decision 3). The lobby's
*needs an update* (ADR 0025, decision 10) calls `contour update`, and shows
what it will change, and what it will leave alone and why, before it does
anything.

**3. It refuses where a rename refuses.** While a page is open on the space,
read from its **presence**, and during a run, by taking the space's hold —
a page or an agent reading rules that change under it would be the same fault
ADR 0021 decision 8 exists to prevent.

**4. It lands unsaved, as a rename does.** The changed files sit uncommitted and
the next commit the user approves carries them (rule 5). The lobby's row says
*updated, not saved yet* until then.

**5. Only the copies.** `CLAUDE.md`, `.claude/settings.json` and the two
skills — the files `lib/space.py`'s `SCAFFOLD` already lists, so what `init`
writes, what `doctor` compares and what `update` replaces cannot disagree.
Never `spec.yaml`, `build.py`, `refs/` or anything the model is made of: update changes a space's rules, never its model, which is why it is not
a build and needs no `contour check` to follow it.

## Consequences

- A space whose rules were edited stays partly behind, and says which file and
  why. That is the chosen error: an update that can silently overwrite a
  deliberate rule is worse than one that leaves a file for somebody to merge.
- A toolkit commit that a space records but this clone no longer has — a
  rewritten history, a space from another machine — leaves no template to
  compare against. Then every differing file counts as edited, and nothing is
  overwritten.
- Open question 13 — a space outside the toolkit sees no rules — is not solved
  by this, but its fix, a space-level `CLAUDE.md`, becomes one an update can
  carry.

## Rejected

- **Overwrite every drifted file, after a diff.** For the person ADR 0025 is
  for, a diff is a page of text clicked through, and the edit is lost.
- **Refuse if anything was edited.** Correct, and it leaves one changed setting
  blocking every later rule change, with nobody on that page able to fix it.
- **Not copying at all.** ADR 0015 copies because the agent reads these from the
  working directory; that has not changed.
