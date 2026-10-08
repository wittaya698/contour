# 83 — One answer to how a copy stands

**Type:** AFK · **Source:** architecture review, 2026-10-08; ADR 0026, second amendment — [update: a space's copies brought in step](../adr/0026-update-brings-a-space-in-step.md); CONTEXT.md, **update**

## What to build

Two modules judge whether a space's copies are in step, and they disagree.
`lib/cli.py`'s `scaffold` calls any copy that differs from *today's* template
`drift`; `lib/update.py` asks ADR 0026's sharper question, whether the copy
still equals the template as it was at the toolkit commit the space records.
`doctor`, `spaces`, the lobby's row and the connector's `status` all repeat the
first. So a space whose owner edited `CLAUDE.md` on purpose, on the current
toolkit, shows *needs an update* with an *Update…* button, and the update —
rightly — leaves the edited file alone, and the row says it again. Forever.
`rename.propose` is a third judge, against today's template under the old name,
so a copy that only fell behind lands in its *untouched* list.

`lib/update.py` gains the one answer: for each file `SCAFFOLD` lists, whether it
is *in step*, *behind* (unedited, and the template has moved on), *edited*, or
*missing*, judged as decision 1 judges it — the template at the recorded commit,
written for one name used throughout. A recorded commit missing from this
clone's history makes every differing copy *edited*, with that as its reason.
`update.propose` becomes a fold over it. `cli.scaffold` is deleted, and the
`toolkit:` marker line is parsed in one place, `update.named`.

Everything that reported drift reads the answer instead. `spaces --json`'s
`scaffold` becomes `{behind, edited, missing}`. The lobby's row says *needs an
update* only when an update would change something — a copy behind or missing,
the recorded commit moved, or rules the agent cannot see — and says nothing of an
edited copy, which is the user's and not something the space needs. `doctor`
still names an edited copy, for a developer, and says it is theirs.
`rename.propose` rewrites a copy that is in step or behind whole, and only the
header of an edited one.

## Acceptance criteria

- [ ] The four states, tested on the one function over a temp space and a temp toolkit repository with two commits
- [ ] A space with only an edited copy, on the current toolkit, shows no *needs an update* on its row
- [ ] A copy that is behind shows *needs an update*, and after the update the row says nothing
- [ ] `doctor` says `EDITED` for an edited copy and `BEHIND` for a behind one; no `DRIFT` remains
- [ ] The connector's `status` reports `{toolkit, behind, edited, missing}`
- [ ] `rename` rewrites a behind, unedited copy whole rather than listing it as untouched
- [ ] `cli.scaffold` is gone, and `toolkit:` is parsed only by `update.named`

## Blocked by

None - can start immediately
