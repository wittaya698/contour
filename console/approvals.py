"""Approvals waiting: what an unattended run's gates set aside (ADR 0028,
decisions 1 and 3).

Above `lib/` for the veto store's reason: a gate is the console's, so the one
door that writes an approval is here, and no `contour` subcommand can write one.
Only a console reads it either: it holds the call and the diff, which the survey
and the connector must never hand a requester (ADR 0027, decision 8).

In the space's `.contour/`, which a space git-ignores whole but for its marker:
an approval is this machine's business until somebody answers it, and a veto it
becomes is kept where vetoes are.
"""
import json
import os
import subprocess
import time
from pathlib import Path

from console import last_run, launcher, vetoes
from lib import intent, lock, marks, space as space_lib, store

TOOLKIT = Path(__file__).resolve().parent.parent

LATER = "answer the one set aside before it first"

NAME = "approvals.json"

PREFIX = "a"

QUESTION = "question"
"""The category a question is kept under, beside the gates' (ADR 0028,
decision 2)."""

NO_CASE = "Claude gave no case for this."
"""What the page says under a spec write the agent made no case for."""


def path(space):
    return space_lib.layout(space).dot / NAME


def load(space):
    """Every approval waiting in this space, oldest first: the order they are
    answered in (ADR 0028, decision 3)."""
    return store.load(path(space), [])


def set_aside(space, run, category, tool, call, said, case):
    """Keep one call a gate could not pass, with what the gate would have shown:
    the act and the diff in `said`, and the agent's `case` for it. Returns it.

    The call as the agent wrote it, copied: what is applied later is what the
    person reads, and nothing the agent still holds can change it.
    """
    kept = load(space)
    approval = {"id": store.next_id(kept, PREFIX), "run": run, "at": time.time(),
                "category": category, "tool": tool, "call": dict(call),
                "said": said, "case": case}
    save(space, kept + [approval])
    return approval


def acts(space):
    """What waits, as the run record says it: each act in its plain words, or
    a question's text, and never the call, the diff or the case (ADR 0028,
    decision 5)."""
    return [" ".join(q.get("question", "") for q in a["call"].get("questions") or ())
            if a["category"] == QUESTION else a["said"]["act"] for a in load(space)]


def save(space, approvals):
    """Written beside and moved into place: a console reads it while a run in
    another may still be adding to it."""
    where = path(space)
    where.parent.mkdir(parents=True, exist_ok=True)
    beside = where.with_name(where.name + ".new")
    store.save(beside, approvals)
    os.replace(beside, where)


def shown(space):
    """Every approval waiting, as the page shows it: what its gate would have
    shown, the agent's case, and whether it is the next to answer. Only the
    oldest is, because a save set aside after a spec write must not be answered
    before it (ADR 0028, decision 3)."""
    return [{"id": a["id"], "category": a["category"], "tool": a["tool"],
             "call": a["call"], **a["said"], "case": case(a), "next": n == 0,
             **({"changes": unsaved(space)} if a["category"] == "commit" else {})}
            for n, a in enumerate(load(space))]


def case(approval):
    """The agent's case for an approval, or, for a spec write, plainly that it
    gave none: rule 1 asks one of a spec write and of nothing else (issue
    101)."""
    if approval["case"] or approval["category"] != "spec-write":
        return approval["case"]
    return NO_CASE


def unsaved(space):
    """What a save would take in, as the tree stands now: read when shown and
    not kept when set aside, because what is saved is the tree the person
    answers on, after whatever was ahead of it went in."""
    said = subprocess.run(["git", "-C", str(space), "status", "--short"],
                          capture_output=True, text=True).stdout
    return [" ".join(line.split()) for line in said.splitlines() if line.strip()]


def answer(space, at, allow, reason=None, answers=None):
    """The person's answer to the approval `at`, or None if none waits by that
    id. Only the oldest may be answered (ADR 0028, decision 3).

    Deny is a veto, kept as a gate's deny keeps one. Allow applies the call
    then, as it was written, and what became of it is the outcome: *applied*,
    *no longer applies* (the tree moved under it, so nobody considered what it
    would now do, and it is no veto), *refused* by the guard a live call meets,
    or *failed*. Whichever, it is answered, and no longer waits.

    A question has no allow: its `answers` are what answer it, and what comes
    back carries the `prompt` a new run starts on, because nothing resumes
    (ADR 0028, decision 2).
    """
    kept = load(space)
    found = next((a for a in kept if a["id"] == at), None)
    if found is None:
        return None
    if found is not kept[0]:
        return {"answered": False, "why": LATER}
    if found["category"] == QUESTION:
        if not answers:
            return {"answered": False, "why": "a question is answered with its answers"}
        dropped(space, at)
        return {"answered": True, "id": at, "outcome": "answered", "said": "",
                "prompt": asked(found["call"], answers)}
    if allow:
        try:
            outcome, said = applied(space, found)
        except lock.Held as e:
            return {"answered": False, "why": str(e)}
    else:
        vetoes.record(space, found["category"], found["tool"], found["call"], reason)
        outcome, said = "vetoed", reason or ""
    dropped(space, at)
    return {"answered": True, "id": at, "outcome": outcome, "said": said}


def dropped(space, at):
    """No longer waiting, here and in the run record, which is where the lobby,
    `status` and a request learn what waits: they never read this store."""
    save(space, [a for a in load(space) if a["id"] != at])
    last_run.amend(space, approvals=acts(space))


def asked(call, answers):
    """The first message of the run an answer starts: the question as it was
    asked, and the person's answer to it, in their words and nobody else's."""
    lines = ["In a run nobody was watching, you asked:"]
    for q in call.get("questions") or ():
        lines += [f"  {q.get('question', '')}",
                  f"The user answers: {answers.get(q.get('question', ''), '(no answer)')}"]
    return "\n".join(lines)


def applied(space, approval):
    """Make the call the agent made, now, holding the space while it runs.

    Through the guard the agent's own call would have met first: a reference
    git tracks is refused here exactly as the space's PreToolUse hook refuses
    it in a live run, because an allow at a gate never got past that either
    (ADR 0019, decision 20).
    """
    record = lock.take(space, "console approval")
    try:
        tool, call = approval["tool"], approval["call"]
        refused = guarded(space, tool, call)
        if refused:
            return "refused", refused
        if tool == "Edit":
            return edited(space, call)
        if tool == "Write":
            target = Path(space, call["file_path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(call.get("content", ""))
            return "applied", ""
        if tool == "Bash":
            return ran(space, approval["category"], call["command"], record["run"])
        return "failed", f"{tool} cannot be made later"
    finally:
        lock.release(space, record)


def guarded(space, tool, call):
    """What the space's guard says to this call, or None if it lets it by."""
    done = subprocess.run([str(TOOLKIT / "contour"), "hook", "spec"], cwd=str(space),
                          input=json.dumps({"tool_name": tool, "tool_input": call,
                                            "cwd": str(space)}),
                          capture_output=True, text=True, timeout=60,
                          env=dict(os.environ, **{intent.ROOT: str(space)}))
    return (done.stderr.strip() or "refused by the space's guard") \
        if done.returncode == 2 else None


def edited(space, call):
    """An `Edit`, as the tool makes one: its old text found once, or every
    time it was asked to replace all, and nothing written otherwise."""
    target = Path(space, call["file_path"])
    text = target.read_text() if target.is_file() else ""
    old, new = call.get("old_string", ""), call.get("new_string", "")
    found = text.count(old) if old else 0
    if found == 0 or (found > 1 and not call.get("replace_all")):
        return "no longer applies", f"{call['file_path']} no longer reads as it did"
    target.write_text(text.replace(old, new) if call.get("replace_all")
                      else text.replace(old, new, 1))
    return "applied", ""


def ran(space, category, command, run):
    """A shell call, in the space, with the environment a run's agent has: the
    toolkit on `PATH`, and the hold this answer took named as its run."""
    if category == "commit" and not unsaved(space):
        return "no longer applies", "there is nothing left to save"
    if category == "build" and marks.unresolved(marks.load(Path(space) / marks.NAME)):
        # What an allowed build always does first: pins cast against the
        # geometry they were clicked on (ADR 0019, decision 14).
        launcher.run(space, "resolve", held_by=run)
    done = subprocess.run(command, shell=True, cwd=str(space), capture_output=True,
                          text=True, timeout=launcher.TIMEOUT_S,
                          env=dict(os.environ, CONTOUR_RUN=run, PATH=os.pathsep.join(
                              [str(TOOLKIT), os.environ.get("PATH", "")])))
    if done.returncode != 0:
        said = (done.stdout + done.stderr).strip().splitlines()
        return "failed", "\n".join(said[-5:])
    return "applied", ""
