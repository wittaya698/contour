# 33 — Accept ADR 0021

**Type:** HITL · **Source:** [ADR 0021](../adr/0021-the-lobby.md)

## What to build

Nothing, beyond the verdict.

ADR 0021 is Proposed, and gated on a tracer bullet:
- `contour lobby` listing the spaces on this machine;
- a throwaway space renamed end to end, with the proposal shown, the confirm, and
  a green `contour check` afterwards with `revision:` bumped;
- a console left open on that space making the same rename refuse.

Slices 28–32 are that bullet. Run it, watch it, and **accept, amend or withdraw**
on what it shows. The precedents are ADR 0017 and ADR 0020, both accepted on their
bullet's result, and both worth more where that result disagreed with the draft.

Things the bullet may turn up, which would amend rather than withdraw:
- the rename proposal is too long to read as a confirm;
- presence cannot be made reliable on some signal path;
- the split protected server needs a different seam from the one ADR 0021 decision 2
  assumes.

**Do not start slices 34–38 first.** Each cites a decision that can still move.

## Acceptance criteria

- [ ] The bullet was run on this machine, and the user watched the rename and the refusal
- [ ] ADR 0021 is Accepted, amended or withdrawn, with the result recorded in it
- [ ] `docs/adr/README.md` and the ADR state the same status
- [ ] The decision numbers cited by slices 28–38 still exist and still mean what those slices say

## Blocked by

- [32](32-rename-from-the-lobby.md)
