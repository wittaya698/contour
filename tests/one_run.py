"""One suite run per machine at a time, held by importing this (issue 94).

`SignalTest` counts every `console.server` on the machine, on purpose: an
orphan has no parent left to report it. So a second run's consoles look like
this run's leaks. Every test file that can start a console imports this, and
`test_one_run` checks that each one does; a full `discover` always imports one,
so a full run always holds it.

The lock is an `flock` and not a pid file: the OS lets go of it when the
process ends however it ends, so a killed run leaves nothing to clean up and
nothing stale to argue with. It is taken at import, which `discover` does for
every file before it runs a test, and is held until the process exits.
"""
import fcntl
import os
import tempfile
from pathlib import Path

PATH = Path(os.environ.get("CONTOUR_SUITE_LOCK")
            or Path(tempfile.gettempdir()) / "contour-suite.lock")
"""Per user, which is per machine for anyone who runs this suite. The env
hatch is for `test_one_run`, which proves the release on a lock of its own."""

_held = os.open(PATH, os.O_RDWR | os.O_CREAT, 0o644)
try:
    fcntl.flock(_held, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    holder = os.pread(_held, 32, 0).decode(errors="replace").strip() or "?"
    os.close(_held)
    raise RuntimeError(
        f"a test suite is already running on this machine (pid {holder}); "
        f"one run at a time, since its consoles would read as this run's "
        f"leaks (README, issue 94)") from None
os.ftruncate(_held, 0)
os.pwrite(_held, str(os.getpid()).encode(), 0)
