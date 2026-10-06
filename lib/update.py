"""Updating a model space: its copies brought in step with the toolkit, where
nobody edited them (ADR 0026).

`doctor` says *drift* when a copy differs from **today's** template, which
cannot tell a file the template moved on from apart from one somebody edited.
The space's marker records the toolkit commit it was made from, and the
toolkit's own history holds the template as it was then: a copy that still
equals that was never touched, and may be replaced. Anything else is somebody's,
and is named and left.

`propose` changes nothing and `perform` does what it says, as a rename does.
"""

import re

from . import git, lock, presence
from . import space as space_lib

UNSEEN = presence.UNSEEN


def recorded(root):
    """The toolkit commit the space's marker names, or None."""
    marker = (root / space_lib.MARKER).read_text()
    return next((l.split(":", 1)[1].strip() for l in marker.splitlines()
                 if l.startswith("toolkit:")), None)


def then(toolkit, commit, rel):
    """The template at `rel` as toolkit `commit` held it, `<NAME>` and all, or
    None when this clone's history has no such commit or no such file there."""
    return git.show(toolkit, commit, f"templates/space/{rel}") if commit else None


def written_from(text, template):
    """Whether `text` is `template` written for one name, unedited.

    For any one name, not only the space's own: `rename` leaves a copy the
    template has since moved on from where it was, the old name in its body
    (`rename.propose`'s *untouched*). Nobody edited that copy either."""
    if "<NAME>" not in template:
        return text == template
    parts = [re.escape(part) for part in template.split("<NAME>")]
    pattern = parts[0] + f"({space_lib.LEGAL.pattern})" + r"\1".join(parts[1:])
    return re.fullmatch(pattern, text) is not None


def propose(root, toolkit, mine=None):
    """What updating the space at `root` would do. Writes nothing."""
    was, now = recorded(root), git.head(toolkit) or "unknown"
    replaced, written, left = [], [], []
    for rel in space_lib.SCAFFOLD:
        f, today = root / rel, space_lib.template(toolkit, rel, root.name)
        if not f.exists():
            written.append(rel)
            continue
        text = f.read_text()
        if text == today:
            continue
        old = then(toolkit, was, rel)
        if old is None:
            left.append({"what": rel, "why": f"toolkit {was} is not in this toolkit's "
                                             f"history, so there is nothing to tell an "
                                             f"edit from"})
        elif written_from(text, old):
            replaced.append(rel)
        else:
            left.append({"what": rel, "why": f"edited since toolkit {was}; yours to merge"})
    return {"path": str(root), "from": was, "to": now, "replaced": replaced,
            "written": written, "left": left, "unseen": UNSEEN,
            "refused": presence.occupied(root, "update", mine)}


def perform(root, toolkit):
    """Do what `propose` says, holding the space throughout, and return what it
    said. Left uncommitted: the next commit the user approves carries it."""
    try:
        mine = lock.take(root, "contour update")
    except lock.Held:
        return propose(root, toolkit)
    try:
        said = propose(root, toolkit, mine)
        if said["refused"]:
            return said
        for rel in said["replaced"] + said["written"]:
            f = root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(space_lib.template(toolkit, rel, root.name))
        marker = root / space_lib.MARKER
        marker.write_text("".join(
            f"toolkit: {said['to']}\n" if l.startswith("toolkit:") else l
            for l in marker.read_text().splitlines(keepends=True)))
        return said
    finally:
        lock.release(root, mine)


def lines(said, done):
    """What update did, or would do, as a person reads it."""
    out = [f"update {said['path']}", f"    toolkit {said['from']} -> {said['to']}", ""]
    replaced, written = ("replaced", "written") if done else ("replace", "write")
    out += [f"  {replaced:<9} {rel}" for rel in said["replaced"]]
    out += [f"  {written:<9} {rel}   (it was missing)" for rel in said["written"]]
    if not said["replaced"] and not said["written"]:
        out.append("  nothing to replace")
    if said["left"]:
        out += ["", "left alone:"]
        out += [f"  {l['what']}\n      {l['why']}" for l in said["left"]]
    if done:
        out += ["", "not saved yet: the next commit you approve carries it"]
    else:
        out += ["", said["unseen"], "", "nothing changed. to do it: contour update"]
    return out
