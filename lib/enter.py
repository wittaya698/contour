"""Entering a space: its console, started as if typed there (ADR 0021, decision 2).

The one lobby action that needs more than the standard library, so it is a
capability, granted only where the console's environment exists. Where to look
for that environment is `contour-console`'s own rule, kept here so the lobby and
the console cannot disagree about whether there is one.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONSOLE = ROOT / "contour-console"
CONTOUR = ROOT / "contour"
VENV = ROOT / ".venv"
MAKE_IT = ("python3 -m venv .venv && "
           ".venv/bin/pip install -r console/requirements.txt")


def interpreter():
    """The Python the console runs under. `$CONTOUR_CONSOLE_PYTHON` overrides,
    the way `$BLENDER` does for the launcher: one escape hatch, named after the
    thing it replaces, so a test never has to build an environment to prove
    something that is not about environments."""
    told = os.environ.get("CONTOUR_CONSOLE_PYTHON")
    return Path(told) if told else VENV / "bin" / "python"


def environment():
    """None where the console can run; otherwise the line that makes its
    environment, as `contour-console` prints it."""
    return None if interpreter().exists() else MAKE_IT


def into(space, presence):
    """Start a console on `space`, or the refusal that says why not, in the
    words the lobby and the connector both say (ADR 0024, decision 5).
    `presence` is the space's, as `contour spaces --json` lists it. A space a
    console already serves gets no second one: neither caller sees a console's
    URL, which carries its secret, so neither can send anybody there."""
    consoles = [p for p in presence if p["kind"] == "console"]
    if consoles:
        return ("already open in a console (pid "
                + ", ".join(str(p["pid"]) for p in consoles) + "); its tab is the way in")
    missing = environment()
    if missing:
        return f"no console environment; make one, from {ROOT}: {missing}"
    console(space)
    return None


def console(space, begin=None, of=None):
    """Start `contour-console` in `space`, and return without waiting for it.

    Given nothing but where to stand, and `begin`, the name of a flow for its
    run to start on (ADR 0021, decision 4), and `of`, the space a variation
    varies. In a session of its own, so nothing that ends the lobby — a closed
    tab, a Ctrl-C, a closed terminal — reaches it: the console has its own
    lifetime, its own port and its own tab."""
    detached(space, str(CONSOLE), *(("--begin", begin) if begin else ()),
             *(("--of", str(of)) if of else ()))


def page(where, command):
    """Start `contour <command>` in `where`, and return without waiting for it:
    a page whose Done is the user's, on the page (ADR 0024, decision 5)."""
    detached(where, sys.executable, str(CONTOUR), command)


def detached(where, *argv):
    """In a session of its own, with nothing to say to its starter."""
    subprocess.Popen(argv, cwd=str(where), start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)


def reveal(space):
    """Open the space's directory in Finder: the escape hatch for anything the
    lobby does not do. Returns None, or what went wrong."""
    try:
        r = subprocess.run(["open", str(space)], capture_output=True, text=True,
                           timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"could not open {space}: {e}"
    return None if r.returncode == 0 else f"could not open {space}: {r.stderr.strip()}"
