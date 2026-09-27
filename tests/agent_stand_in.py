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
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import anchor, marks


def drive(prompt, options, gate, say):
    for step in json.loads(os.environ.get("CONTOUR_AGENT_SCRIPT") or "[]"):
        if "say" in step:
            say("text", text=step["say"])
        if "limit" in step:
            # What the harness says when it compacts. Said and not acted on: a
            # limit the user did not choose must not interrupt work they were
            # watching (ADR 0019), which is the same reason a timeout does not.
            say("limit", text=step["limit"])
        if "mark" in step:
            # The agent's own return path, run for real: `contour mark` is on
            # `PATH` because `options` put the toolkit there, and it is the way an
            # agent attaches *addressed in this build* to a finding (ADR 0018).
            # Not gated and not routed through the gate, which is the point — the
            # console has to read the store to know what the run did to it.
            subprocess.run(["contour", "mark", *step["mark"]],
                           cwd=options["cwd"], env=options["env"],
                           capture_output=True, text=True)
        if "rebuilt" in step:
            # The build the run produced, as far as the marks are concerned: these
            # are the parts it has. `contour render` does this from inside Blender
            # with the build in front of it, which is the one thing the suite
            # cannot run — so the effect on the store is produced here instead,
            # and what is under test stays the console's reading of it.
            anchor.orphan(Path(options["cwd"]) / marks.NAME, set(step["rebuilt"]))
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
