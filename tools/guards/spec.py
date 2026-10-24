#!/usr/bin/env python3
"""PreToolUse guard: the user's references are read-only, always (ADR 0012).

    a reference git tracks  -> deny.  Photographs the user supplied; no
                                     measurement argument justifies the agent
                                     rewriting one.
    a reference it does not -> allow. Saving new references is how a space starts.

Before judging, it locks every picture in each `refs/` folder the call names,
tracked or not, so a script that only reads one is not a write and runs; one
that writes fails on the lock (ADR 0036). Run again as the PostToolUse hook,
it puts back from git a tracked picture the call changed anyway.

Anything else is none of this guard's business and is allowed without asking git
anything. It once covered `spec.yaml` too; ADR 0016 sanctioned a confirmed spec
write and moved that half to detection, in `contour check`.

Which paths rule 1 is about is not decided here — `lib.intent` decides it, for
this guard and for the console's gate alike, because two copies of that rule
disagreed and the guard held the narrower one. What stays here is the policy,
next to the deny it explains.

This is the layer rule 1 rests on: a PreToolUse hook fires before the SDK
consults the console's `can_use_tool`, so the guard keeps denying while the
ask-list only asks (ADR 0019, decision 20).

A model space never copies this file. Its settings.json runs `contour hook
spec`, so the guard is always the installed version (ADR 0015).

stdin: the PreToolUse, PostToolUse or PostToolUseFailure JSON. Exit 2 denies,
or after the call says it was refused, and shows stderr to the agent.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lib import intent, locked


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


def inside(root, named):
    """`named` as a path relative to the space, or None if it is not in it.

    A reference copied in from outside — `cp ~/Downloads/side.jpg refs/` — names
    a source this space has no contract about, and git cannot be asked about a
    path it does not hold.
    """
    try:
        return Path(root, named).expanduser().resolve().relative_to(root)
    except ValueError:
        return None


def backstop(root, call_id, named):
    """After the call: a tracked picture it changed anyway, by a way round the
    lock that the text did not show, is put back from git (ADR 0036,
    decision 4). Exit 2 after a call shows stderr to the agent."""
    back, restored = locked.put_back(root, call_id, named) if named else ([], True)
    if not back:
        return 0
    one = len(back) == 1
    them = "it" if one else "them"
    which = "this picture is" if one else "these pictures are"
    done = (f"Put back as git has {them} and locked again." if restored else
            f"Git could not put {them} back: stop, and tell the user {which} changed.")
    print(f"refused: {', '.join(back)} {'is' if one else 'are'} the user's reference "
          f"{'image' if one else 'images'}, and this call changed {them}\n"
          f"  (rule 1, ADR 0012). {done}\n"
          f"  Measure a reference; never rewrite one.", file=sys.stderr)
    return 2


def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        return 0
    payload = ev.get("tool_input") or {}
    tool = ev.get("tool_name") or ""
    root = Path(os.environ.get(intent.ROOT) or ev.get("cwd") or ".").resolve()
    named = intent.references(tool, payload)
    # A call that failed has an event of its own, and a script can change a
    # picture before it fails.
    if ev.get("hook_event_name") in ("PostToolUse", "PostToolUseFailure"):
        return backstop(root, ev.get("tool_use_id"), named)
    # Before the call is judged: a script let through reads a picture it cannot
    # write (ADR 0036, decision 1).
    locked.lock(root, named)
    if named:
        locked.before(root, ev.get("tool_use_id"), named)
    try:
        category = intent.classify(tool, payload)
    except ValueError:
        # Unsplittable is not unreadable. `references` reads the call's text
        # rather than its words, so the references it names are known either way,
        # and a guard has to answer where a gate is right to raise. Read as a ref
        # write so that each one it names is judged; one that names none is
        # allowed, because the quoting in `echo it's fine` is none of this
        # guard's business.
        category = "ref-write"
    if category != "ref-write":
        return 0
    for named in intent.references(tool, payload):
        rel = inside(root, named)
        if rel is None or not tracked(root, rel):
            continue
        print(f"refused: {rel} is one of the user's reference images and git tracks it\n"
              f"  (rule 1, ADR 0012). It states what the model must be, in pictures.\n"
              f"  Unlike spec.yaml, there is no confirmed path to rewriting one:\n"
              f"  measure it and propose a spec revision instead.", file=sys.stderr)
        return 2
    return 0


sys.exit(main())
