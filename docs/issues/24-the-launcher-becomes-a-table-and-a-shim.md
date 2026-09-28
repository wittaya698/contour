# 24 — The launcher becomes a table and a shim

**Type:** AFK · **Source:** architecture review 2026-09-28 · ADR 0008, ADR 0019 decision 22, open question 11

## What to build

`contour` is 803 lines doing thirteen jobs, and it has no `.py` extension, so none
of it can be imported. Fourteen of its functions are pure — the revision reader,
the report helpers, the space walk, `mask_check` — and every test of them spawns a
process against a six-line `/bin/sh` script pretending to be Blender. Two tests
give up on that and read the launcher *as text*: `tests/test_intent.py` AST-walks
`main` to discover which subcommands reach `build_path`. That is a test asking a
question the code cannot answer.

Meanwhile `main` is a flat if-chain in which each arm re-derives three orthogonal
facts — does this need a space, does it take the hold, which `lib` modules to
import. `sys.path.insert(0, str(ROOT))` appears nine times inside function bodies,
after line 45 already did it. And open question 11 states as a *decision* that
`check`, `render`, `export` and `resolve` hold the space while `canvas` and `mark`
deliberately take nothing — a decision that exists in the code as four
`hold`/`finally: free` pairs and two absences you have to notice.

**`lib/commands.py` holds the table as data:** name, arity, needs-a-space,
holds-the-space, **category**, help, handler. The hold policy becomes a column, so
`canvas` not holding reads as a choice.

**The category column retires a third copy.** `lib/intent.py` hard-codes `BUILD =
("check", "render", "export")`, `contour` spells the same tuple again, and
`test_intent.py`'s AST-walk exists only to check the two agree. `intent` reads the
table instead, and that test becomes a plain assertion.

**The table is data-only, in its own module.** `intent` is deliberately three
imports wide because the console consults it; it must not acquire the launcher's
dispatcher. `lib/cli.py` resolves handlers against the table; `intent` imports the
table alone.

**`contour` becomes a shim** — put the toolkit on `sys.path`, call
`cli.main(argv)`. ADR 0008 is satisfied: it is about Blender only ever being run
through `contour`, not about where the code sits. `stage`, `init`, `doctor`,
`install_hooks` and the hold all become importable.

**Usage text is generated from the help column.** The docstring keeps its prose
about model spaces and Blender's stdout; the command list is rendered, so a new
command cannot be undocumented and a removed one cannot linger.

**Slice 03's launcher assertion follows the code:** the check that the launcher
imports no console module now points at `lib/cli*.py`, and the roster gains
`commands` and `cli`, both free — they spawn Blender, they never import it.

## Acceptance criteria

- [ ] `contour` is a shim of under a dozen lines
- [ ] `lib/commands.py` is data only and imports nothing from `lib/cli.py`
- [ ] Every command's space requirement and hold policy is a column, applied in one place
- [ ] `lib/intent.py` reads the table; no tuple of build commands exists anywhere else
- [ ] `tests/test_intent.py` asserts against the table and AST-walks nothing
- [ ] `sys.path.insert` appears once
- [ ] `contour --help` is generated from the table and matches it by test
- [ ] `tests/test_commands.py` asserts the hold policy per command with no subprocess
- [ ] `tests/test_lib_split.py` names `commands` and `cli` free, and checks `lib/cli*.py` imports no console module
- [ ] Every `contour` subcommand behaves identically, exit codes included
- [ ] `contour selftest` green; `tests/test_launcher.py` and `test_run_lock.py` green

## Blocked by

None strictly. Cheaper after [17](17-the-space-layout-is-a-function-of-a-space.md),
which already moves the space walk out, and after
[19](19-one-spelling-for-a-part.md), whose migration command would otherwise be
added to the if-chain and then moved again.
