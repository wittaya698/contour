#!/usr/bin/env python3
"""PreToolUse guard: the user's references are read-only, always (ADR 0012).

This guard once covered `spec.yaml` too, denying every write to a tracked one.
ADR 0016 ended that: a spec may be revised once the user has confirmed the
change, so a blanket deny would now refuse the sanctioned path. The spec is
still guarded, but by a different mechanism in a different place — `contour
check` compares it against HEAD and fails when the content moved and
`revision:` did not. Prevention became detection, knowingly.

What is left here is the half that has no sanctioned write at all. In a model
space (ADR 0015) it sits at the root:

    refs/**

    tracked   -> deny.  Photographs the user supplied; no measurement argument
                        justifies the agent rewriting one.
    untracked -> allow. Saving new references is how a space starts.

Anything else is none of this guard's business and is allowed without asking
git anything.

A model space never copies this file. Its settings.json runs `contour hook
spec`, so the guard is always the installed version (ADR 0015).

stdin: the PreToolUse JSON. Exit 2 denies and shows stderr to the agent.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

PROTECTED = ("refs",)


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
    print(f"refused: {rel} is one of the user's reference images and git tracks it\n"
          f"  (rule 1, ADR 0012). It states what the model must be, in pictures.\n"
          f"  Unlike spec.yaml, there is no confirmed path to rewriting one:\n"
          f"  measure it and propose a spec revision instead.", file=sys.stderr)
    return 2


sys.exit(main())
