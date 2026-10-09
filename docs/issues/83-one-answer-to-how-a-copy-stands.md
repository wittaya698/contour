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
*missing*, judged as ADR 0026 decision 1 judges it — the template at the recorded commit,
written for one name used throughout. A recorded commit missing from this
clone's history makes every differing copy *edited*, with that as its reason.
`update.propose` becomes a fold over it. `cli.scaffold` is deleted, and the
`toolkit:` marker line is parsed in one place, `update.named`.

Everything that reported drift reads the answer instead. `spaces --json`'s
`scaffold` becomes `{behind, edited, missing}`. The lobby's row says *needs an
update* only when an update would change a copy — one behind or missing, or
rules the agent cannot see — and says nothing of an
edited copy, which is the user's and not something the space needs. `doctor`
still names an edited copy, for a developer, and says it is theirs.
`rename.propose` rewrites a copy that is in step or behind whole — a behind one
as the template was at the recorded commit, under the new name, so a rename
never brings newer rules in — and only the header of an edited one.

## Acceptance criteria

- [x] The four states, tested on the one function over a temp space, against the toolkit's own history
- [x] A space with only an edited copy, on the current toolkit, shows no *needs an update* on its row
- [x] A copy that is behind shows *needs an update*, and after the update the row says nothing
- [x] `doctor` says `EDITED` for an edited copy and `BEHIND` for a behind one; no `DRIFT` remains
- [x] The connector's `status` reports `{toolkit, behind, edited, missing}`
- [x] `rename` rewrites a behind, unedited copy as its old template under the new name, rather than listing it as untouched
- [x] A recorded commit that moved, with every copy in step, is not *needs an update*
- [x] `cli.scaffold` is gone, and `toolkit:` is parsed only by `update.named`

## Blocked by

None - can start immediately
