# 126 — A spec gate shows all it changes

**Type:** AFK · **Source:** found in flight, issue 120; rule 1, issue [104](104-a-spec-write-is-the-whole-change.md)

## What to build

On `crate` the agent tried a spec change as a plain `Edit`. The gate listed the
two UV fields it moved and left the revision out on purpose, and *the exact call*
showed only `Edit <path>`. Read carefully, the write looked unbumped, and was
denied for it — wrongly: a write without the bump is refused before any gate.

The gate names the revision move among the changes, and an `Edit` shows the text
it replaces and the text it writes.

## Acceptance criteria

- [x] A spec write's gate lists *revision 1 → 2* with the fields it moves
- [x] An `Edit`'s exact call shows its old and new text
- [x] A write that moves the revision alone is still refused, as issue 104 has it

## Blocked by

None - can start immediately
