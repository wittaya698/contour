#!/usr/bin/env python3
"""PreToolUse guard: the user's intent is read-only once accepted (ADR 0002).

Rule 1 has always been prose. ADR 0002 states its mechanical form — *"a spec
git already tracks is never written again"* — and this implements exactly that
predicate, no more. In a model space (ADR 0015) those are at the root:

    spec.yaml   and   refs/**

    tracked   -> deny.  It is the contract; propose changes in chat.
    untracked -> allow. Creation is not mutation (ADR 0002, amended).

Anything else is none of this guard's business and is allowed without asking
git anything. In the toolkit checkout nothing matches, which is correct: the
only spec there belongs to the fixture and is the toolkit's own test asset.

A model space never copies this file. Its settings.json runs `contour hook
spec`, so the guard is always the installed version (ADR 0015).

stdin: the PreToolUse JSON. Exit 2 denies and shows stderr to the agent.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

PROTECTED = ("spec.yaml", "refs")


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
    if rel.parts[0] not in PROTECTED or not tracked(root, rel):
        return 0
    kind = "spec" if rel.parts[0] == "spec.yaml" else "reference image"
    print(f"refused: {rel} is the user's {kind} and git tracks it (rule 1, ADR 0002).\n"
          f"  It states what the model must be; it is not yours to adjust to what it is.\n"
          f"  Propose the change in chat and let the user make it.", file=sys.stderr)
    return 2


sys.exit(main())
