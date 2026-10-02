"""Entering a space: its console, started as if typed there (ADR 0021, decision 2).

The one lobby action that needs more than the standard library, so it is a
capability, granted only where the console's environment exists. Where to look
for that environment is `contour-console`'s own rule, kept here so the lobby and
the console cannot disagree about whether there is one.
"""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONSOLE = ROOT / "contour-console"
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


def console(space, begin=None, of=None):
    """Start `contour-console` in `space`, and return without waiting for it.

    Given nothing but where to stand, and `begin`, the name of a flow for its
    run to start on (ADR 0021, decision 4), and `of`, the space a variation
    varies. In a session of its own, so nothing that ends the lobby — a closed
    tab, a Ctrl-C, a closed terminal — reaches it: the console has its own
    lifetime, its own port and its own tab."""
    subprocess.Popen([str(CONSOLE), *(("--begin", begin) if begin else ()),
                      *(("--of", str(of)) if of else ())],
                     cwd=str(space), start_new_session=True,
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
