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

- [ ] `contour-console` forwards `SIGTERM` and `SIGHUP` to its child, waits, and kills only on timeout
- [ ] The three signal paths are one piece of code, and the child is sent the signal that arrived
- [ ] A test terminates a running console and asserts no `console.server` survives it
- [ ] A test terminates a console with a run under way and asserts the space's hold is released — `contour check` in that space is not refused afterwards
- [ ] `tests/test_console.py` leaks no processes: the suite's process count is the same before and after it
- [ ] Whether the server also watches for a vanished parent is decided in this slice and written down here
- [ ] `contour selftest` green, twice in a row on one machine

## Blocked by

None. Worth having before slice 24, which moves 803 lines of launcher and wants a
suite whose red means something.
