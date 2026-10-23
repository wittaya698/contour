"""What a tool call did, in plain words (ADR 0025, decision 8).

The transcript shows the agent's words as they are and each call as one line
of activity — *Changed the build script*, not `Edit /…/build.py` — with the raw
call one click away. One table, keyed by tool and, for `contour`, by command,
for the reason `lib/gate.py` and `lib/verdict.py` are one table each: a second
would be a second vocabulary.

Stdlib, and Blender-free: the console imports this to draw its transcript.
"""
import re
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
    "release-glb": "Put the model's file into a release, with its topics",
    "request": "Asked for a run in a model",
    "ceiling": "Looked at what a run left alone may spend",
    "hook": "Ran a safety check",
}
"""`contour` command -> what it did. Every command `lib/commands.py` holds is
here (`tests/test_activity.py`), and in the page's tiers (ADR 0025, decision
1): *sheet*, *mark*, *span* and *reference* are shown, so they stay; a hold,
a toolkit and a commit are hidden, so they do not appear."""

TOOLS = {
    "mcp__contour__spec_write": "Proposed a change to the spec",
    "mcp__contour__topics_propose": "Suggested words to find this model by",
    "ToolSearch": "Looked up its tools",
}
"""A tool with one thing to say, whatever its call: the console's own, whose
call the page shows again as a gate, and the harness's lookup of them."""

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
    if tool == "mcp__contour__ask":
        # The form says the questions again, just under it (ADR 0034).
        n = len(call.get("questions") or ())
        return f"Asked you {n} question" + ("" if n == 1 else "s")
    return TOOLS.get(tool)


def split(command):
    """A shell line as its words, with `;`, `&&` and `|` words of their own
    even against the word before them: `contour worksheet;` is the worksheet
    (a live console, 2026-10-24). None for a line the shell could not read."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        return list(lexer)
    except ValueError:
        return None


def contour(command):
    """A shell call that runs `contour`, however it is spelled — `./contour`,
    or after a `cd` into the space — as its act. None for anything else."""
    words = split(command)
    if words is None:
        return None
    for at, word in enumerate(words[:-1]):
        if word.rsplit("/", 1)[-1] == "contour":
            verb, rest = words[at + 1], words[at + 2:]
            if verb == "run" and rest:
                return contour(shlex.join(rest)) or CONTOUR["run"]
            if verb == "measure" and rest and not rest[0].startswith("-"):
                picture = assigned(rest[0], words[:at])
                if any(c in picture for c in "$`*?["):
                    return "Measured a picture"     # shell, never shown as itself
                if Path(picture).suffix:
                    return f"Measured the {Path(picture).stem} picture"
                # A redirect's `2`, or a folder: no picture named.
            return CONTOUR.get(verb)
    return None


def verb(command):
    """The `contour` command a shell call runs, through `contour run` too, or
    None for anything else: what the console waits before (ADR 0035)."""
    words = split(command)
    if words is None:
        return None
    for at, word in enumerate(words[:-1]):
        if word.rsplit("/", 1)[-1] == "contour":
            found, rest = words[at + 1], words[at + 2:]
            if found == "run" and rest:
                return verb(shlex.join(rest)) or found
            return found
    return None


def assigned(word, before):
    """What `$R` or `${R}` holds, from an `R=…` earlier in the same line, or
    the word itself when it names no variable (issue 153)."""
    found = re.fullmatch(r"\$\{?([A-Za-z_]\w*)\}?", word)
    if found is None:
        return word
    for earlier in reversed(before):
        name, eq, value = earlier.rstrip(";").partition("=")
        if eq and name == found.group(1):
            return value
    return word


def named(path):
    """A file as the page calls it."""
    name = Path(path).name
    return FILES.get(name, name)
