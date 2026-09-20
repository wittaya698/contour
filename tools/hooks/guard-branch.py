#!/usr/bin/env python3
"""PreToolUse guard: shared files are edited on `master` only (ADR 0003).

A variant branch adds `models/<v>/` and nothing else. That is what makes
`git merge master` conflict-free by construction, so a shared file changed on
a variant is not untidiness — it is the one thing that breaks the merge
guarantee every other branch depends on.

    on master            -> allow everything.
    on a variant, under models/  -> allow. That is the branch's own work.
    on a variant, anywhere else  -> deny. Fix it on master and merge forward.

The rule was prose until now, and prose caught it late: a README edit made on
a variant branch was noticed at the staging step rather than at the keystroke.

This sees only what the Write and Edit tools do. Git's own writes during a
merge or a checkout do not pass through here, and do not need to — a merge is
how shared change is *supposed* to reach a variant.

stdin: the PreToolUse JSON. Exit 2 denies and shows stderr to the agent.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

TOOLKIT_BRANCH = "master"
OWN_WORK = "models"


def branch(root):
    """Current branch, or "" when detached or git cannot say. Unknown is not a
    licence: an empty answer never matches master, so the guard stays on."""
    try:
        r = subprocess.run(["git", "-C", str(root), "branch", "--show-current"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        return 0
    path = (ev.get("tool_input") or {}).get("file_path")
    if not path:
        return 0
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ev.get("cwd") or ".").resolve()
    try:
        rel = Path(path).resolve().relative_to(root)
    except ValueError:
        return 0                                  # outside the repo: not ours
    here = branch(root)
    if here == TOOLKIT_BRANCH or rel.parts[0] == OWN_WORK:
        return 0
    print(f"refused: {rel} is a shared file and you are on branch "
          f"{here or '(unknown)'!r} (ADR 0003, CLAUDE.md repo shape).\n"
          f"  A variant branch adds models/<v>/ and nothing else; that is what keeps\n"
          f"  git merge master conflict-free for every other variant.\n"
          f"  Fix it on {TOOLKIT_BRANCH}, then merge forward:\n"
          f"    git checkout {TOOLKIT_BRANCH}  ->  edit  ->  commit\n"
          f"    git checkout {here or '<variant>'}  ->  git merge {TOOLKIT_BRANCH}",
          file=sys.stderr)
    return 2


sys.exit(main())
