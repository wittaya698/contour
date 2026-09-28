# 27 — A terminated console lets go of the space

**Type:** AFK · **Source:** found running slice 17's suite, 2026-09-28 · ADR 0019 decisions 2, 34

## What to build

`contour-console` forwards `SIGINT` to its child and nothing else. `handover()`
catches `KeyboardInterrupt`, passes it on, waits ten seconds, and kills what is
left — and the comment beside it states the reason exactly:

> the console has a port to close and a run whose hold on the space has to be
> given back, and SIGKILL releases neither

**Every word of that is true of `SIGTERM`, which the shim does not handle.** The
default disposition kills the shim where it stands, and `python -m console.server`
is reparented to init and runs on: it keeps its port bound, and if a run was under
way it keeps the space's `run.lock`. That lock is judged by `lock.alive`, which
asks the kernel whether the pid is still there — and it is. So the space is held
by a process that has no terminal, no parent and no page, and the next `contour
check` in it is refused with a pid the user cannot go and look at.

This is not theoretical and it is not rare. `tests/test_console.py:finish` ends
every console it launches with `proc.terminate()`, which is the right thing for a
test to do. One `unittest discover -s tests` therefore leaves about **57**
orphaned servers behind. A working session that runs the suite a dozen times
accumulated **1050** of them, at which point the machine could not fork at all and
the suite failed with 94 errors that had nothing to do with the code under test —
the worst kind of red, because it accuses the change in flight.

**The fix is the one the existing comment already argues for.** The shim installs
a handler for `SIGTERM` (and `SIGHUP`, which is what a closed terminal sends) that
does what the `KeyboardInterrupt` path does: forward, wait, kill only if waiting
fails. The three signals want one piece of code, not three copies of it — what
differs is which signal arrived, and the child should be sent that same one.

**The server's own exit path already works** and is not what this slice changes.
`console/server.py:main` closes the port and releases the hold in a `finally`, on
every path out. The bug is that under `SIGTERM` it is never asked to.

**A second guard is worth considering and is not obviously worth having.** The
server could also notice its parent has gone — poll `os.getppid()`, or read a pipe
that closes when the shim dies — which would cover `SIGKILL` on the shim too, the
one case forwarding cannot reach. Weigh it against what it costs: a poll in the
console's own loop, and a new way for a console to decide to die. Decide it in the
slice, and record whichever way it goes.

No new vocabulary. **console** and **run** already say everything this touches.

## Acceptance criteria

- [x] `contour-console` forwards `SIGTERM` and `SIGHUP` to its child, waits, and kills only on timeout
- [x] The three signal paths are one piece of code, and the child is sent the signal that arrived
- [x] A test terminates a running console and asserts no `console.server` survives it
- [x] A test terminates a console with a run under way and asserts the space's hold is released — `contour check` in that space is not refused afterwards
- [x] `tests/test_console.py` leaks no processes: the suite's process count is the same before and after it
- [x] Whether the server also watches for a vanished parent is decided in this slice and written down here
- [x] `contour selftest` green, twice in a row on one machine

## What it came to

**The shim forwards all three, and they are one piece of code.** `SIGINT` was
handled and `SIGTERM` and `SIGHUP` were not, so the default disposition killed
`contour-console` where it stood and left `python -m console.server` reparented
to init with its port bound and, if a run was under way, the space still held.
The fix is the one the existing comment already argued for: the same forward,
the same ten-second wait, the same kill only on timeout — and the child is sent
the signal that arrived, so a console that was hung up on exits 129 and one
somebody typed Ctrl-C at exits 130.

**`lib/signals.py` is what the three paths have in common.** Two processes have
to stop well and both needed the same one step — turning a signal into
something that comes out of the wait it stopped, carrying which signal it was.
The interpreter already does that for `SIGINT` and calls it
`KeyboardInterrupt`; `Arrived` is the same thing for the other two, so the code
that ends a console catches both and asks `signals.number(which)` rather than
caring which it caught. Free half of `lib/`, because the shim is stdlib-only by
design and a server must not need Blender to shut down (ADR 0019, decision 32).

**The server had to be asked, not just told.** Forwarding on its own would have
fixed nothing that matters: `SIGTERM`'s default kills the server too, before
the `finally` that closes the port and gives the space back. So the server
installs the same three handlers and takes the path it already had for
`KeyboardInterrupt` — its exit path was never wrong, it was never reached.
It now says which signal stopped it, because a console that is gone cannot be
asked afterwards.

**The second guard is in, and here is the reasoning.** The server watches
whether the process that launched it is still there — `os.getppid()`, read once
at start and checked in the `watch` loop that was already ticking every quarter
second. It costs one comparison per tick and no new thread. It covers the one
case forwarding cannot reach, which is `SIGKILL` on the shim — nothing runs
after one — and that is not a hypothetical case: it is what a person reaches
for when a console will not go, and what Activity Monitor sends. Two details
were decided rather than fallen into. The check sits *before* the gate
suppression, because a console parked at a gate is exactly the one holding the
space, and a check a gate could postpone would miss the case that costs
something. And it is skipped when the parent was already init at startup, so a
server launched some other way never decides to die on the strength of a
question that had no answer. It is not a new way for a console to end: it ends
the same way the page closing ends it, through `canvas.finish()`.

**The bill, and the small sibling.** One `unittest discover -s tests` left about
57 orphaned servers behind; it now leaves none, twice measured, and
`contour selftest` — which runs the suite inside itself — leaves none twice in a
row. `tests/test_console.py` holds itself to that directly: a test launches a
console, ends it through the very `finish` every other test in the file ends
through, and asserts nothing of its own survives. Two smaller leaks in the same
family went with it: `tests/test_panel.py` killed a `contour canvas` without
ever waiting for it, and `tests/test_run_lock.py` left its pipes open, both of
which warned from inside `doCleanups` — which is the exact place a real leak
would have shown, and so the wrong place for noise.

**What was proven.** 367 → 372 tests, green; `contour selftest` PASS twice,
127.7s and 127.6s, `mutants 13/13` and `roundtrip 6/6` both times. Eight mutants
were run against the new code and all eight were caught: the shim handles only
the signal a person types / the shim passes on SIGINT whatever arrived / the
shim kills the console rather than asking it to close / the server handles only
the signal a person types / the server never notices its parent has gone / the
server checks its parent only when no gate is waiting / a signal that arrived is
always reported as SIGINT / the three ways to stop are two, and a closed
terminal is not one.

## Blocked by

None. Worth having before slice 24, which moves 803 lines of launcher and wants a
suite whose red means something.
