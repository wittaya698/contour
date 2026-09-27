"""The veto store: a denial, kept (ADR 0019, decisions 15, 25).

Above `lib/` on purpose, and the only store that is. Every other one — marks,
refs, the panel's verdict — is written by the pipeline and lives where the
pipeline can reach it. A veto has exactly one writer: the user, at a gate, which
is to say the console. Putting the file's only door up here means no `contour`
subcommand can write one even by mistake, because `lib/` may not import upwards
and the launcher must never import the console at all.

It is not `marks.json`, and the reason is retention. A mark gets resolved and
closed, so ADR 0018 prunes closed ones the last release tag already holds and
leaves the archive to git. A veto is never resolved — it is a fact about a
moment, already true when it happened — so pruning one would delete the only
record that something was prevented. Two opposite rules in one file means the
pruner has to tell them apart, and the first bug is that it does not.
"""
import json
import re
import subprocess
from pathlib import Path

from lib import agent, anchor, marks

NAME = "vetoes.json"
"""Beside `marks.json` at the space's root, and tracked for the same reason.

Not in `.contour/`, which a space gitignores whole but for its marker: a veto
that vanished on a clean checkout would be exactly the log decision 15 refused
to make it.
"""

_ID = re.compile(r"^v(\d+)$")


def load(space):
    path = Path(space) / NAME
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def save(space, vetoes):
    """Indented, one field per line, in the order they happened.

    Shaped to be read in a diff rather than by a parser: a veto arrives at the
    bottom and nothing above it moves, so `git diff` shows the sentence that was
    added and not a reformatted file.
    """
    Path(space).joinpath(NAME).write_text(
        json.dumps(vetoes, indent=2) + "\n", encoding="utf-8")


def next_id(vetoes):
    """One past the highest ever used, the way a mark's id is. Nothing here is
    ever deleted, so this is also one past the count — but it is written as the
    highest, because an id that could be reused would point at two moments."""
    used = [int(m.group(1)) for m in
            (_ID.match(str(v.get("id", ""))) for v in vetoes) if m]
    return f"v{max(used, default=0) + 1}"


def record(space, category, tool, call, reason):
    """Keep one denial. Returns it.

    The build is named because a veto is a fact about a moment, and the moment a
    denial belongs to is the geometry the user was looking at when they gave it.
    The fingerprint is the one `views.json` and the panel already use, so there
    is no second answer to *which build was this*.
    """
    space = Path(space)
    # The space's own build, by the convention ADR 0015 set: `out/<name>.blend`.
    blend = space / "out" / f"{space.name}.blend"
    vetoes = load(space)
    kept = {"id": next_id(vetoes), "category": category, "tool": tool,
            "call": dict(call), "reason": reason, "author": "user",
            "build": anchor.fingerprint(blend)}
    save(space, vetoes + [kept])
    return kept


def promote(space, veto_id, part):
    """Turn one veto into a sheet mark about a part. Returns the mark, or None.

    The mark names the part and no point on it, which is the shape the render
    already badges from the identity mask — so a promoted veto gains a position
    on every view that can see the part, and gains it without any new placement
    machinery (ADR 0018). The author is the user: they wrote the sentence, and a
    veto is theirs exactly as the question it becomes is.

    The part comes from the caller and is never inferred from the call's text.
    Guessing which part *widen the neck tolerance* was about would attribute a
    claim to the user they did not make, in the one file that records what they
    personally refused.
    """
    space = Path(space)
    kept = load(space)
    found = next((v for v in kept if v.get("id") == veto_id), None)
    if found is None or found.get("promoted"):
        # Nothing, and nothing said: a moment that happened once becomes one
        # question, and a veto nobody recorded has no sentence to carry.
        return None
    # The build's own list of parts, which is what `contour mark` is held to as
    # well — a mark naming a part no view can see is a badge that never draws.
    here = agent.known(space / "out" / "parts.json")
    if here is not None and part not in here:
        return None
    mark = marks.append(space / marks.NAME,
                        {"anchor": {"part": part}, "text": found["reason"],
                         "from": found["id"]})
    # Which mark it became, on the veto. Not a resolution — a veto is never
    # resolved — but the page has to be able to say a question was already asked,
    # and a reader following one backwards has to land on the moment it came from.
    found["promoted"] = mark["id"]
    save(space, kept)
    return mark


def _git(space, *args):
    """Git in this space, or nothing. A space that is not a repository yet, or a
    machine with no git, is not an error to raise at the page — it is a space
    where no veto is committed, which is what the count then says."""
    try:
        done = subprocess.run(("git",) + args, cwd=str(space),
                              capture_output=True, text=True)
    except OSError:
        return ""
    return done.stdout if done.returncode == 0 else ""


def committed(space):
    """The veto ids `HEAD` already holds.

    Asked of git rather than stamped on the veto as it is written: a stamp would
    be a claim about a commit that had not happened, and the thing that makes it
    true or false afterwards is `git checkout`, which does not come past here.
    """
    blob = _git(space, "show", f"HEAD:./{NAME}")
    try:
        return {v.get("id") for v in json.loads(blob)} if blob.strip() else set()
    except json.JSONDecodeError:
        return set()


def exposure(space):
    """What the page says about vetoes: all of them, and how many are at risk.

    The count is the console's whole contribution to decision 27. It does not
    commit them — that is rule 5 flat — and it does not propose a records-only
    commit at run end either, because a veto-only commit describes no model state
    and would have to be skipped past by anyone reading history to understand how
    the model got here. *I stopped you widening that tolerance* belongs in the
    commit where the tolerance did not get widened.
    """
    space = Path(space)
    kept = load(space)
    held = committed(space)
    return {"vetoes": kept,
            "uncommitted": sum(1 for v in kept if v.get("id") not in held)}
