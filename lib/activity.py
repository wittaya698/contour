"""What a tool call did, in plain words (ADR 0025, decision 8).

The transcript shows the agent's words as they are and each call as one line
of activity — *Changed the build script*, not `Edit /…/build.py` — with the raw
call one click away. One table, keyed by tool and, for `contour`, by command,
for the reason `lib/gate.py` and `lib/verdict.py` are one table each: a second
would be a second vocabulary.

Stdlib, and Blender-free: the console imports this to draw its transcript.
"""
import shlex
from pathlib import Path

FILES = {"build.py": "the build script", "spec.yaml": "the spec"}
"""A file the page has a name for, by its name in the space."""


CONTOUR = {
    "check": "Built the model",
    "render": "Drew the sheet",
    "export": "Exported the model",
    "filmstrip": "Drew an animation, frame by frame",
    "api": "Looked up how Blender does something",
    "measure": "Measured on a reference",
    "worksheet": "Drew the spans onto the references",
    "canvas": "Opened the sheet to mark on",
    "resolve": "Pinned the marks to the build",
    "mark": "Left a mark on the sheet",
    "run": "Ran a command",
    "selftest": "Tested Contour itself",
    "install-hooks": "Installed the safety checks",
    "init": "Made a new model",
    "doctor": "Checked this model is in step with Contour",
    "update": "Brought this model's rules up to date with Contour",
    "migrate-marks": "Rewrote the marks in the current spelling",
    "spaces": "Listed the models",
    "status": "Read how a model and its latest run stand",
    "stop": "Stopped the run in a model",
    "mcp": "Started the Claude Desktop connection",
    "lobby": "Opened the list of models",
    "rename": "Renamed the model",
    "delete": "Deleted the model",
    "restore": "Brought back a deleted model",
    "purge": "Removed a deleted model for good",
    "intents": "Listed what Claude asks before doing",
    "asks": "Looked at what runs without asking",
    "topics": "Looked at the words this model is found by",
    "request": "Asked for a run in a model",
    "ceiling": "Looked at what a run left alone may spend",
    "hook": "Ran a safety check",
}
"""`contour` command -> what it did. Every command `lib/commands.py` holds is
here (`tests/test_activity.py`), and in the page's tiers (ADR 0025, decision
1): *sheet*, *mark*, *span* and *reference* are shown, so they stay; a hold,
a toolkit and a commit are hidden, so they do not appear."""

QUIET = ("Read", "Grep", "Glob", "LS", "NotebookRead")
"""Tools that only read. Consecutive ones fold into one line, *Looked at 3
files*: a dozen reads between two edits is how an agent works, and a line
each would bury what it changed."""


def looked(n):
    """What `n` consecutive reads say, as one line."""
    return f"Looked at {n} file" + ("" if n == 1 else "s")


def line(tool, call):
    """One call, as one line of activity, or None when the table does not
    know it — and then the page shows the raw call, never nothing."""
    if tool in ("Edit", "Write", "MultiEdit"):
        return f"Changed {named(call.get('file_path', ''))}"
    if tool == "Bash":
        return contour(call.get("command", ""))
    return None


def contour(command):
    """A shell call that runs `contour`, however it is spelled — `./contour`,
    or after a `cd` into the space — as its act. None for anything else."""
    try:
        words = shlex.split(command)
    except ValueError:
        return None
    for at, word in enumerate(words[:-1]):
        if word.rsplit("/", 1)[-1] == "contour":
            verb, rest = words[at + 1], words[at + 2:]
            if verb == "run" and rest:
                return contour(shlex.join(rest)) or CONTOUR["run"]
            if verb == "measure" and rest and not rest[0].startswith("-"):
                return f"Measured the {Path(rest[0]).stem} picture"
            return CONTOUR.get(verb)
    return None


def named(path):
    """A file as the page calls it."""
    name = Path(path).name
    return FILES.get(name, name)
