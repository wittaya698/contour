# 94 — The signal tests go red in the full suite

**Type:** AFK · **Source:** found timing the suite, 2026-10-09 · issue [27](27-a-terminated-console-lets-go.md)

## What to build

Three of `test_console.SignalTest`'s five tests go red in a full
`unittest discover -s tests`, and all five are green on their own:

| Test | Red as |
|---|---|
| `test_a_closed_terminal_ends_the_console_and_says_which_signal_did` | a pid not in `before` is alive after: *the server outlived the terminal it was hung up on* |
| `test_a_console_killed_outright_still_lets_go_of_the_space` | `lock.holder(space)` is a `console run` pid: *the run kept the space it was holding* |
| `test_the_cleanup_this_suite_runs_puts_back_what_it_launched` | `2 != 1`: *no server started* |

Measured 2026-10-09, Python 3.14.7: the full suite fails these three (1079
tests, 301 s); `-k SignalTest` alone passes 5/5 in 3.9 s; `test_console.py`
alone passes 88/88 in 81 s. **So the stray process comes from outside
`test_console.py`** — from one of the files that run before it or alongside it
and launch consoles or lobbies (`test_connector`, `test_canvas`, `test_always`
and others; `grep -l console.server tests/` is the list to start from).

**Why it shows here and nowhere else.** `ConsoleCase.servers` asks
`pgrep -f console.server` of the whole machine, by design — issue 27's failure
was a server that outlived its parent, which the parent cannot report. So every
`before`/`after` comparison in `SignalTest` counts *any* `console.server` that
starts or is still exiting during the test, including another file's. One of
two things is true, and the slice finds out which before it changes anything:

1. **Something still leaks.** An earlier test leaves a server — or a process
   that later starts one — running into `SignalTest`. Then issue 27's
   *"the suite leaks no processes"* criterion no longer holds, and the leak is
   the bug. Find the test that leaves it, and fix that test or the code it
   exposes.
2. **Nothing leaks, but shutdown is late.** An earlier test's server is still
   on its way out when `SignalTest` takes `before`, and is counted on one side
   of the comparison and not the other. Then the comparison is what is wrong.

The second failure is the one to read first: a `console run` still holding a
space after `SIGKILL` is the exact case issue 27's parent-watch was built for,
and if it holds only in isolation, that guard is weaker than 27 recorded.

**Not a fix:** dropping these assertions, retrying them, widening their
timeouts until they pass, or narrowing `servers()` to the shim's own children —
that last one would stop seeing the very orphan issue 27 is about. Rule 2: a red
check is a finding. A narrower count is fine only if it still catches a server
reparented to init, e.g. by marking each server a test launches (an env var or
argument visible to `pgrep -f`) and counting those.

No new vocabulary.

## Acceptance criteria

- [ ] Which test leaves the process behind, or that none does, is found and written down here
- [ ] If something leaks: it no longer does, and the suite's `console.server` count is the same before and after a full run
- [ ] `SignalTest` sees only servers this suite launched, and still sees one that outlived its parent
- [ ] Full `unittest discover -s tests` green twice in a row on one machine, with `SignalTest` unchanged in what it asserts
- [ ] `contour selftest` green

## Blocked by

None. Worth having before any work on suite speed (shared servers per class,
parallel runs), which would make cross-test leaks more likely and harder to see.
