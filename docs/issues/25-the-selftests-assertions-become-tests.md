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

- [x] `contour` holds no domain assertions; only the fixture pipeline run remains
- [x] `mask_check`'s assertions run with no Blender
- [x] The Blender-backed ones skip cleanly, saying why, when `$BLENDER` is unset
- [x] `contour selftest` still fails on every condition it fails on today
- [x] `contour selftest`'s output stays within ADR 0005's budget on green
- [x] `agent_check`'s claim is verified once, in the place that can witness it
- [x] A mutant that passes still fails `contour selftest`

## What it came to

**`tests/test_fixture.py`, three classes.** `MaskFaultTest` runs the mask's
claims against masks painted by hand: a right stack, the pillar drawn over the
cap, a part missing from the column, a background pixel naming a part and a
table that is not the fixture's. It runs with no Blender. `FixtureTest` skips
without `$BLENDER`, saying why. With it, the class builds and renders the
fixture itself (a few seconds) and holds six claims against the render: the
mask, the four views and the build they name, a cap click anchored on the cap's
30 mm surface, a background click anchored to nothing, the badge back within
3 px, and an agent finding drawn on the part it names. `SelftestTest` is the
third, below.

**`selftest` calls `FixtureTest` itself.** `fixture_tests` in `lib/cli.py`
loads the file by path, because an import of it would put a non-stdlib name in
the launcher and `test_lib_split` refuses that. It counts a skip as a failure,
since the point of running the tests there is that they cannot be left out.
`unit_tests` withholds `$BLENDER`, so the suite skips them and the render is
paid for once. On green the `mask` and `anchor` lines (~70 tokens) became one:
`ok   fixture   6/6 held against its render`.

**The agent's claim is made once.** The fixture test writes the finding
straight to the store: whether `contour mark` accepts one is
`test_agent_marks.py`'s business, and so is which pixel of a part is right (the
L). All the fixture witnesses is that the render put the badge on the part the
mask names. Filing it beside the two clicks also removed one of the two
re-renders.

**One check dropped as dead.** "Two parts share one index" compared the keys of
a dict parsed from JSON with themselves, so it could never fail.

**Eleven mutants against the render, resolve, the store and the wiring.**
They covered world coordinates stored as part-local, the wrong part named, a
pixel kept after anchoring, a lit mask, an unflipped mask, a badge 8 px out, an
agent badge on another part, views out of order, resolve crashing on
background, the fixture allowed to skip, and the fixture's line not counted.
The first ten were caught, each by the test written for it. The last survived:
on a green fixture, nothing noticed that `selftest` no longer counted the
fixture's line, and the old `ok &= mk["ok"]` had the same gap. `SelftestTest`
now stubs Blender and the unit suite, the two processes `selftest` spawns, and
holds that a failing claim fails the selftest.

A first mutation pass reported nonsense, because `py_compile` had left a
mutant's bytecode behind, the same size and written in the same second as the
restored source. Clearing `__pycache__` after each restore fixed it.

## Blocked by

- [24 — The launcher becomes a table and a shim](24-the-launcher-becomes-a-table-and-a-shim.md)
