# 25 — The selftest's assertions become tests

**Type:** AFK · **Source:** architecture review 2026-09-28 · ADR 0009

## What to build

About two hundred lines of `contour` are domain assertions with nowhere else to
live: `mask_check`, `anchor_check`, `agent_check`, `marks_store_id`. They are
untested code that exists to test other code, inside a file nothing can import.
One of them says so itself — `agent_check`'s docstring admits the fixture cannot
witness the case it is checking and points at `tests/test_agent_marks.py`, so the
same claim is verified twice, once expensively.

**They move to `tests/`, skipping when Blender is absent.** `mask_check` is pure
and becomes a plain test immediately. The others become tests that skip without
`$BLENDER`, so they are things a developer can run and read rather than assertions
buried in a CLI.

**`contour selftest` still invokes them.** ADR 0009's guarantee is that *one
command* proves the verifier's teeth; if that becomes "someone remembers to run
pytest", the guarantee has been weakened rather than moved, and rule 2 covers a
check as much as a build. So `selftest` keeps running the fixture pipeline and
calls this subset, reporting in its own terse lines.

**The duplicated claim collapses.** `agent_check` and `tests/test_agent_marks.py`
stop being two verifications of one behaviour; the Blender-backed one keeps only
what the fixture can actually witness.

## Acceptance criteria

- [ ] `contour` holds no domain assertions; only the fixture pipeline run remains
- [ ] `mask_check`'s assertions run with no Blender
- [ ] The Blender-backed ones skip cleanly, saying why, when `$BLENDER` is unset
- [ ] `contour selftest` still fails on every condition it fails on today
- [ ] `contour selftest`'s output stays within ADR 0005's budget on green
- [ ] `agent_check`'s claim is verified once, in the place that can witness it
- [ ] A mutant that passes still fails `contour selftest`

## Blocked by

- [24 — The launcher becomes a table and a shim](24-the-launcher-becomes-a-table-and-a-shim.md)
