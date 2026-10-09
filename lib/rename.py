"""Renaming a model space: everything it changes, shown before any of it is
done (ADR 0021, decisions 5, 7 and 8).

A space's name is its identity, so a rename is four changes made together —
the directory, `model:`, `revision:`, and the scaffolding that carries the
name — and two things left behind on the old path, which is the only key
anything outside the space has (open question 12).

The proposal is the argument rule 1 asks for, and the confirming flag is the
confirm: `propose` changes nothing, and `perform` does exactly what `propose`
says, so what the user read is what was written.
"""
import re

from . import git, lock, policy, presence, revision, update
from . import space as space_lib

MODEL = revision.MODEL
REVISION = re.compile(r"^revision:[^\n]*$", re.M)
"""The two lines a rename rewrites, as lines: `revision.FIELD` reads the number
and may run past the end of its line, which is right for reading and would eat
the newline of a spec whose last line it is."""


UNSEEN = presence.UNSEEN


def respelled(text, name):
    """`spec.yaml` naming `name`, one revision on. A spec that never had either
    field gains it, rather than being refused for predating it."""
    bumped = revision.of(text) + 1
    if MODEL.search(text):
        text = MODEL.sub(f"model: {name}", text, count=1)
    else:
        text = f"model: {name}\n" + text
    if revision.FIELD.search(text):
        return REVISION.sub(f"revision: {bumped}", text, count=1)
    return MODEL.sub(lambda m: f"{m.group(0)}\nrevision: {bumped}", text, count=1)


def rewritten(root, change, toolkit):
    """A scaffold file as it reads under the new name: the template's — the one
    it was written from, if the toolkit has moved on since, so a rename never
    brings newer rules in — or, for one the user has written in, theirs under
    the template's header."""
    if change.get("of"):
        return update.then(toolkit, change["of"], change["what"]).replace(
            "<NAME>", change["to"])
    now = space_lib.template(toolkit, change["what"], change["to"])
    if change["only"] != "header":
        return now
    mine = (root / change["what"]).read_text().split("\n", 1)
    return now.split("\n", 1)[0] + ("\n" + mine[1] if len(mine) > 1 else "")


def refusal(root, name, mine=None):
    """Why this rename may not happen, or None. `mine` is the hold `perform`
    took, which is not somebody else's run."""
    illegal = space_lib.illegal(name)
    if illegal:
        return illegal
    if name == root.name:
        return f"{name!r} is not a name to rename to: it is this space's name now"
    if (root.parent / name).exists() or (root.parent / name).is_symlink():
        return f"{root.parent / name} already exists; pick another name"
    unbumped = revision.unbumped(root)
    if unbumped:
        return (f"spec.yaml differs from HEAD, revision still {unbumped[1]}: confirm "
                f"or undo that change first, or this rename's bump would pass it "
                f"as confirmed (rule 1, ADR 0016)")
    occupied = presence.occupied(root, "rename", mine)
    if occupied:
        return occupied
    return None


def propose(root, name, toolkit, mine=None):
    """What renaming the space at `root` to `name` would do. Writes nothing."""
    old, new = root.name, root.parent / name
    changes = [{"what": "directory", "from": str(root), "to": str(new)}]
    spec = space_lib.layout(root).spec
    if spec.exists():
        text = spec.read_text(encoding="utf-8")
        changes += [{"what": "model:", "from": revision.model(text), "to": name},
                    {"what": "revision:", "from": revision.of(text),
                     "to": revision.of(text) + 1}]
    untouched = []
    made_from = update.recorded(root)
    for rel, stands in update.standing(root, toolkit).items():
        if stands == "missing":
            continue
        if stands == "behind":
            # Unedited, so whole: as the template it was written from, under
            # the new name, wherever in the file the name is (issue 83).
            if "<NAME>" in update.then(toolkit, made_from, rel):
                changes.append({"what": rel, "from": old, "to": name, "only": None,
                                "of": made_from})
            continue
        was, now = (space_lib.template(toolkit, rel, n) for n in (old, name))
        if was == now:
            continue
        text = (root / rel).read_text()
        if stands == "in step":
            changes.append({"what": rel, "from": old, "to": name, "only": None})
        elif text.split("\n", 1)[0] == was.split("\n", 1)[0] != now.split("\n", 1)[0]:
            # Edited, so the user has written in it: the header is the name
            # and is the rename's, and everything under it stays theirs. A
            # header with no name in it has nothing to rename.
            changes.append({"what": rel, "from": old, "to": name, "only": "header"})
        else:
            untouched.append(rel)      # edited where the name is: the user's to settle
    leaves = []
    if policy.names(root):
        leaves.append({"what": "ask-list", "path": str(policy.ask_list()),
                       "why": f"its entry for {root} will govern nothing; the renamed "
                              f"space asks about every category until it is named "
                              f"there again"})
    if space_lib.transcripts(root).is_dir():
        leaves.append({"what": "transcripts", "path": str(space_lib.transcripts(root)),
                       "why": "Claude Code's sessions here, and with them the space's "
                              "spend history, stay filed under the old path"})
    return {"from": str(root), "to": str(new), "changes": changes,
            "untouched": untouched, "leaves": leaves, "unseen": UNSEEN, "refused": refusal(root, name, mine)}


def perform(root, name, toolkit):
    """Do what `propose` says, and return what it said. The directory moves
    last, so until it does the space is still where it was.

    Holds the space throughout, so no run can start halfway through (ADR
    0021, decision 7). Taken as no run's member: a rename from inside a run
    would move the directory out from under that run's own agent.
    """
    try:
        mine = lock.take(root, f"contour rename {name}")
    except lock.Held:
        return propose(root, name, toolkit)
    where = root
    try:
        proposal = propose(root, name, toolkit, mine)
        if proposal["refused"]:
            return proposal
        proposal["refused"] = moved(root, name, toolkit, proposal)
        if not proposal["refused"]:
            where = root.parent / name
        return proposal
    finally:
        lock.release(where, mine)


def moved(root, name, toolkit, proposal):
    """The writes, then the move. A failure anywhere puts back every file
    already written, so the space is the old one whole or the new one whole,
    never a directory whose name disagrees with its spec (issue 31). Returns
    None, or what went wrong."""
    spec = space_lib.layout(root).spec
    wanted = {}
    for c in proposal["changes"]:
        if c["what"] == "revision:":
            wanted[spec] = respelled(spec.read_text(encoding="utf-8"), name)
        elif c["what"] in space_lib.SCAFFOLD:
            wanted[root / c["what"]] = rewritten(root, c, toolkit)
    kept = {}
    try:
        for f, text in wanted.items():
            kept[f] = f.read_bytes()
            f.write_text(text, encoding="utf-8")
        root.rename(proposal["to"])
    except OSError as e:
        for f, was in kept.items():
            f.write_bytes(was)
        return f"could not rename {root.name} to {name}: {e}; nothing was changed"
    return None


def lines(proposal):
    """The proposal as a person reads it."""
    out = [f"rename {proposal['from']}", f"    -> {proposal['to']}", "", "changes:"]
    out += [f"  {c['what']:<11} {c['from']} -> {c['to']}"
            + ("   (its header only: the rest is yours)" if c.get("only") == "header" else "")
            for c in proposal["changes"]]
    if proposal["untouched"]:
        out += ["", "untouched (edited since it was written; may still say the old name):"]
        out += [f"  {rel}" for rel in proposal["untouched"]]
    if proposal["leaves"]:
        out += ["", "leaves behind:"]
        out += [f"  {l['what']:<11} {l['path']}\n              {l['why']}"
                for l in proposal["leaves"]]
    out += ["", proposal["unseen"], "", "nothing changed. to do it: contour rename "
            f"{proposal['to'].rsplit('/', 1)[-1]} --yes"]
    return out
