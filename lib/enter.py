"""Entering a space: its console, started as if typed there (ADR 0021, decision 2).

The one lobby action that needs more than the standard library, so it is a
capability, granted only where the console's environment exists. Where to look
for that environment is `contour-console`'s own rule, kept here so the lobby and
the console cannot disagree about whether there is one.
"""
import os
import socket
import subprocess
import sys
from pathlib import Path

from lib import signals

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
    URL, which carries its secret, so neither can send anybody there — except
    that a console running a requester's run, which has no person's tab, is
    asked to open its own page (ADR 0027, decision 7)."""
    here = socket.gethostname()
    consoles = [p for p in presence if p["kind"] == "console" and p.get("host") == here]
    if consoles:
        # Not refused, and not a second console: the one there opens its own
        # page, and nothing passes through the caller (ADR 0027, decision 7).
        # Any console, and not only an unattended one: a person whose tab is
        # lost is given the way back in (ADR 0031, decision 1).
        for p in consoles:
            os.kill(p["pid"], signals.SHOWING)
        return None
    refused = unopenable(presence, Path(space).name)
    if refused:
        return refused
    console(space)
    return None


def unopenable(presence, name):
    """Why no console can be started on a space with this presence, or None:
    one is open already, or there is no environment to run one in. Said once,
    for the lobby, the connector and a request (ADR 0027, decision 6), with
    the ways back to one whose tab may be lost (ADR 0031, decisions 1 and 2).
    One on another machine is named there: this one cannot reach it."""
    consoles = [p for p in presence if p["kind"] == "console"]
    pids = ", ".join(str(p["pid"]) for p in consoles)
    away = sorted({p.get("host") for p in consoles} - {socket.gethostname()})
    if away:
        return (f"already open in a console on {', '.join(away)} (pid {pids}); "
                f"its page is there")
    if consoles:
        return (f"already open in a console (pid {pids}); Open in the lobby brings "
                f"its page back, and contour stop {name} closes it")
    missing = environment()
    if missing:
        return f"no console environment; make one, from {ROOT}: {missing}"
    return None


def requested(space, prose, requester):
    """Start `contour-console` in `space` on a request, with no browser, and
    return the process: the caller waits for its run to take the space (ADR
    0027, decision 3). The prose is all a request carries."""
    return detached(space, str(CONSOLE), "--no-browser", "--request", prose,
                    "--requester", requester)


def console(space, begin=None, of=None, said=None):
    """Start `contour-console` in `space`, and return without waiting for it.

    Given nothing but where to stand, and `begin`, the name of a flow for its
    run to start on (ADR 0021, decision 4), and `of`, the space a variation
    varies, and `said`, a size the chat that made it said, as a value the
    console asks (ADR 0033). In a session of its own, so nothing that ends the
    lobby — a closed tab, a Ctrl-C, a closed terminal — reaches it: the console
    has its own lifetime, its own port and its own tab."""
    detached(space, str(CONSOLE), *(("--begin", begin) if begin else ()),
             *(("--of", str(of)) if of else ()), *(("--said", said) if said else ()))


def page(where, command, *args):
    """Start `contour <command> [args]` in `where`, and return without waiting
    for it: a page whose Done is the user's, on the page (ADR 0024, decision 5)."""
    detached(where, sys.executable, str(CONTOUR), command, *args)


def detached(where, *argv):
    """In a session of its own, with nothing to say to its starter."""
    return subprocess.Popen(argv, cwd=str(where), start_new_session=True,
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
