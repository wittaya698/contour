"""The user's references, read-only on disk (ADR 0036).

Which of a script's calls write is guessing from its text (issue 152), so the
filesystem is asked to refuse instead: a picture without its write bits is one
a script can open and cannot overwrite. Every picture is locked, tracked or
not, since a new space's photo is not committed yet (ADR 0036, decision 1).
The folder stays writable, so a new picture can still be saved into it.

Git records only the executable bit of a file, so a locked picture is not a
change in the space.
"""
import json
import re
import stat
import subprocess
from pathlib import Path

WRITE = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH


def folder(root, named):
    """The `refs/` folder this path is in, inside the space, or None."""
    try:
        rel = Path(root, named).expanduser().resolve().relative_to(Path(root).resolve())
    except ValueError:
        return None
    parts = rel.parts
    if "refs" not in parts or ".git" in parts:
        return None
    at = len(parts) - 1 - parts[::-1].index("refs")
    return Path(root).resolve().joinpath(*parts[:at + 1])


def lock(root, named):
    """Take the write bits off every file in each `refs/` folder `named` is in."""
    for refs in {folder(root, n) for n in named} - {None}:
        if not refs.is_dir():
            continue
        for path in refs.rglob("*"):
            if path.is_file() and not path.is_symlink():
                mode = path.stat().st_mode
                if mode & WRITE:
                    path.chmod(mode & ~WRITE)


def changed(root, named):
    """The pictures git tracks in each `refs/` folder `named` is in that no
    longer match what git holds, relative to the space."""
    folders = sorted(str(f) for f in {folder(root, n) for n in named} - {None})
    if not folders:
        return []
    try:
        r = subprocess.run(["git", "-C", str(root), "diff", "--name-only", "-z", "--",
                            *folders], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        # No git to ask is no answer: nothing is put back, and the guard's own
        # question to git denies the call (ADR 0012).
        return []
    return sorted(p for p in r.stdout.split("\0") if p) if r.returncode == 0 else []


def before(root, call_id, named):
    """Keep which pictures already differed from git before this call ran, so
    that afterwards only what the call changed is put back: a change the user
    made and has not saved yet is theirs."""
    held = Path(root, ".contour", "refs-before")
    held.mkdir(parents=True, exist_ok=True)
    (held / f"{key(call_id)}.json").write_text(json.dumps(changed(root, named)))


def put_back(root, call_id, named):
    """The pictures this call changed, and whether git restored them all; each
    one restored is locked again."""
    held = Path(root, ".contour", "refs-before", f"{key(call_id)}.json")
    try:
        already = set(json.loads(held.read_text()))
        held.unlink()
    except (OSError, ValueError):
        already = set()
    back = [p for p in changed(root, named) if p not in already]
    if not back:
        return [], True
    try:
        restored = subprocess.run(["git", "-C", str(root), "checkout", "--", *back],
                                  capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        restored = False
    lock(root, named)
    return back, restored


def key(call_id):
    """A tool call's id as a file name."""
    return re.sub(r"[^\w-]", "_", str(call_id or "call"))
