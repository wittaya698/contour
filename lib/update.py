"""Updating a model space: its copies brought in step with the toolkit, where
nobody edited them (ADR 0026).

A copy that differs from **today's** template may be one the template moved
on from, or one somebody edited. The space's marker records the toolkit commit
it was made from, and the toolkit's own history holds the template as it was
then: a copy that still equals that was never touched, and may be replaced.
Anything else is somebody's, and is named and left. `standing` is that
judgement, and the one `doctor`, the lobby, the connector and `rename` read
(issue 83).

`propose` changes nothing and `perform` does what it says, as a rename does.
"""

import re

from . import git, lock, presence
from . import space as space_lib

UNSEEN = presence.UNSEEN


def named(marker):
    """The toolkit commit a marker's text names, or None."""
    return next((l.split(":", 1)[1].strip() for l in marker.splitlines()
                 if l.startswith("toolkit:")), None)


def recorded(root):
    """The toolkit commit the space's marker names, or None."""
    return named((root / space_lib.MARKER).read_text())


def uncommitted(root):
    """`{"from": toolkit commit}` while an update is not yet in a commit, else
    None. Read from git each time and stored nowhere, as `survey.renamed`
    is: the marker at HEAD names one toolkit commit and the marker on disk
    another. A space with no commit has nothing to have been updated from."""
    was = git.show(root, "HEAD", str(space_lib.MARKER))
    if was is None:
        return None
    return {"from": named(was)} if named(was) != recorded(root) else None


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


def standing(root, toolkit):
    """How each copy in `root` stands against the toolkit: `in step` (today's
    template), `behind` (the template at the recorded commit, unedited, and
    moved on since), `edited`, or `missing`. The one answer `doctor`, the
    lobby's row, the connector and `rename` read (issue 83). A recorded commit
    this clone's history lacks leaves nothing to tell an edit from, so every
    copy that differs counts as edited (ADR 0026)."""
    was, said = recorded(root), {}
    for rel in space_lib.SCAFFOLD:
        f = root / rel
        if not f.exists():
            said[rel] = "missing"
            continue
        text = f.read_text()
        if text == space_lib.template(toolkit, rel, root.name):
            said[rel] = "in step"
            continue
        old = then(toolkit, was, rel)
        said[rel] = "behind" if old is not None and written_from(text, old) else "edited"
    return said


def propose(root, toolkit, mine=None):
    """What updating the space at `root` would do. Writes nothing."""
    was, now = recorded(root), git.head(toolkit) or "unknown"
    stands = standing(root, toolkit)
    replaced = [rel for rel, s in stands.items() if s == "behind"]
    written = [rel for rel, s in stands.items() if s == "missing"]
    left = [{"what": rel,
             "why": f"edited since toolkit {was}; yours to merge"
             if then(toolkit, was, rel) is not None
             else f"toolkit {was} is not in this toolkit's history, so there is "
                  f"nothing to tell an edit from"}
            for rel, s in stands.items() if s == "edited"]
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
        out += ["", said["unseen"], "", "nothing changed. to do it: contour update --yes"]
    return out
