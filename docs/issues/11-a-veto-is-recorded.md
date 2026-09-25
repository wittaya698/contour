# 11 — A veto is recorded

**Type:** AFK · **Source:** ADR 0019 decisions 15, 25, 27

## What to build

A denial at a gate becomes a **veto**: a tracked record carrying the call, the
reason, the author and the build it happened against.

**A veto is not a mark.** A mark has a position, and position-less marks were
rejected because they collapse *the left of the beak* back to *the beak* and return
the conversation to prose. A veto is a third thing — not *the build is wrong* and
not *here is what I meant*, but *not this*. It is the user's authority against one
call, which is why only the user has it, exactly as only the user closes a mark.

**It lives in its own tracked file, not inside `marks.json`.** Their retention
policies are opposite: resolved marks older than the last release tag are pruned
and git holds the archive, which is coherent because a mark gets resolved and
closed. A veto is never resolved — it is a fact about a moment, already true when
it happened — so pruning one deletes the only record that something was prevented.
Two opposite retention rules in one file means the pruner must tell them apart, and
the first bug is that it does not. Their writers differ too: `marks.json` is written
by the agent through `contour mark` and by the user through the canvas, while a veto
is only ever written by the console at a gate.

**A veto about a part may be promoted to a sheet mark,** which is what gives it a
position and turns a fact about a moment into an open question about the model.

**It reaches git with the change it prevented.** Tracked is not committed, and an
uncommitted veto dies exactly as an ignored one would. The console does not commit
them itself — that is rule 5 flat — **nor does it propose a records-only commit at
run end**, because a veto-only commit describes no model state and would have to be
skipped past by anyone reading history to understand how the model got here. Riding
along is also semantically right: *I stopped you widening that tolerance* belongs in
the commit where the tolerance did not get widened. What the console adds is
visibility, on the page: *n vetoes uncommitted*.

**`contour check` gains no veto line.** Marks report one line when open and nothing
at zero; a veto is never open, so a veto line would never go away, and a status line
that is always present is furniture nobody reads.

The residual risk is stated rather than solved: a `git checkout .` with uncommitted
vetoes loses them, which is already true of `marks.json`.

## Acceptance criteria

- [ ] Denying at a gate writes a veto carrying call, reason, author and build fingerprint
- [ ] The veto file is tracked and diffs readably
- [ ] Only the console writes it; no agent command can
- [ ] A veto naming a part can be promoted to a sheet mark and gains a position
- [ ] `marks.json`'s pruner never sees a veto
- [ ] The page shows *n vetoes uncommitted* and the count goes to zero on commit
- [ ] `contour check` output is byte-identical whether or not vetoes exist
- [ ] Nothing in the console commits, proposes a records-only commit, or bypasses rule 5

## Blocked by

- [08 — A gated run, end to end](08-a-gated-run-end-to-end.md)
