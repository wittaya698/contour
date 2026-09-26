"""A scripted agent, for the tests that are not about the Claude Agent SDK.

`$CONTOUR_CONSOLE_AGENT` points the console at this file the way `$BLENDER`
points the launcher at an interpreter: one hatch, named after the thing it
replaces. What it buys is that gating, denial, the indefinite wait and the lock
are provable on a bare clone — `console/requirements.txt` is the one dependency
in Contour, and `contour selftest` exists to prove a clone with none of it works.

The script is JSON in `$CONTOUR_AGENT_SCRIPT`, one step per thing the agent
does. It is deliberately not a fake of the SDK: it drives the same seam the real
driver drives, so what these tests exercise is the console's run and not a
rehearsal of one.
"""
import json
import os


def drive(prompt, options, gate, say):
    for step in json.loads(os.environ.get("CONTOUR_AGENT_SCRIPT") or "[]"):
        if "say" in step:
            say("text", text=step["say"])
        if "limit" in step:
            # What the harness says when it compacts. Said and not acted on: a
            # limit the user did not choose must not interrupt work they were
            # watching (ADR 0019), which is the same reason a timeout does not.
            say("limit", text=step["limit"])
        if "call" in step:
            # Asked for, then reported — the two halves an agent actually has.
            # What comes back from the gate is a verdict and a sentence, never an
            # edited call: the user says a sentence and the agent writes the code
            # (ADR 0019, decision 13).
            wanted = dict(step["call"])
            allow, reason = gate(wanted.pop("tool", "Bash"), wanted)
            # `ran` is what the agent was actually left holding, so a gate that
            # had quietly rewritten the call would be visible from outside.
            say("result", allowed=allow, text=reason or "done", ran=wanted)
