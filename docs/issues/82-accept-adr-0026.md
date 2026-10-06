# 82 — `beaky` is updated, and ADR 0026 is accepted

**Type:** HITL · **Source:** ADR 0026, the tracer bullet — [update: a space's copies brought in step](../adr/0026-update-brings-a-space-in-step.md)

## What to build

ADR 0026 used by hand and given its verdict. `beaky` is behind. From the lobby,
update it: the preview names what will change and anything left alone, and the
row then says *updated, not saved yet*. Open a run in `beaky`'s console and hear
the agent speak issue 78's plain words. `contour check` is still green.

**Accept, amend or withdraw** ADR 0026 on what that shows.

## Acceptance criteria

- [x] `beaky` is updated from the lobby, the preview having been read first
- [x] Its agent speaks in plain words afterwards
- [x] `contour check` is green afterwards
- [x] ADR 0026's status says accepted, amended or withdrawn, with the evidence

## Blocked by

- [78](78-claude-speaks-plain-words.md)
- [81](81-update-from-the-lobby.md)
