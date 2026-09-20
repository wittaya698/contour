#!/usr/bin/env python3
"""PreToolUse guard: the user's intent is read-only once accepted (ADR 0002).

Rule 1 has always been prose. ADR 0002 states its mechanical form — *"a spec
git already tracks is never written again"* — and this implements exactly that
predicate, no more:

    models/*/spec.yaml   and   models/*/refs/**

    tracked   -> deny.  It is the contract; propose changes in chat.
    untracked -> allow. Creation is not mutation (ADR 0002, amended).

Anything outside those two patterns is none of this hook's business and is
allowed without asking git anything.

stdin: the PreToolUse JSON. Exit 2 denies and shows stderr to the agent.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

PROTECTED = ("spec.yaml", "refs")


def protected(rel):
    """models/<v>/spec.yaml or models/<v>/refs/... — and nothing else."""
    parts = rel.parts
    return len(parts) >= 3 and parts[0] == "models" and parts[2] in PROTECTED


def tracked(root, rel):
    """True if git has this path in the index. An error is not an answer, so it
    denies rather than guessing — the blast radius is one model's contract."""
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", str(rel)],
                           capture_output=True, text=True, timeout=10)
    except Exception as e:
        print(f"cannot ask git whether {rel} is tracked ({e})", file=sys.stderr)
        return True
    return r.returncode == 0


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
        return 0
    if not protected(rel):
        return 0
    if not tracked(root, rel):
        return 0
    kind = "spec" if rel.parts[2] == "spec.yaml" else "reference image"
    print(f"refused: {rel} is the user's {kind} and git tracks it (rule 1, ADR 0002).\n"
          f"  It states what the model must be; it is not yours to adjust to what it is.\n"
          f"  Propose the change in chat and let the user make it.", file=sys.stderr)
    return 2


sys.exit(main())
