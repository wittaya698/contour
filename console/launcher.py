"""The console's one door onto `./contour` (ADR 0019, decision 31).

The console reads state by importing `lib/` and *acts* by spawning the launcher.
Both halves matter here. A Blender stage run in this process would put `bpy`
inside the process that serves the page, which is the thing
`tests/test_lib_split.py` exists to prevent; and a stage reimplemented here would
be a second copy of the pipeline, in the one layer allowed to carry dependencies.

So this file is small on purpose: it is the seam, not a wrapper with opinions.
"""
import os
import subprocess
from pathlib import Path

TOOLKIT = Path(__file__).resolve().parent.parent
TIMEOUT_S = 300           # the launcher's own ceiling on one Blender process


def run(space, *args, held_by=None):
    """One launcher command in this space: `(ok, the lines it printed)`.

    `held_by` is the run this call belongs to, passed as `$CONTOUR_RUN` the way
    the agent's own environment carries it — a console run already holds the
    space, and a child that did not say which run it was would be refused by the
    hold its own parent took (slice 02).

    Both streams are read, and neither is parsed: the launcher prints terse lines
    and a refusal goes to stderr, so a caller wanting to tell the user what
    happened needs both, and a caller wanting to know whether it worked has the
    exit code.
    """
    env = dict(os.environ)
    if held_by:
        env["CONTOUR_RUN"] = held_by
    done = subprocess.run([str(TOOLKIT / "contour"), *args], cwd=str(space),
                          capture_output=True, text=True, timeout=TIMEOUT_S,
                          env=env)
    said = (done.stdout + done.stderr).splitlines()
    return done.returncode == 0, [line for line in said if line.strip()]
