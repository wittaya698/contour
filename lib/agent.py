"""The agent's side of the canvas: a finding arrives as a badge (ADR 0018).

The canvas was built so the user could point at the build; this is the return
path. The agent pins what it already computes — check deltas, `contour measure`
readings, the parts it is unsure of — so a finding lands on the picture instead
of in a paragraph nobody reads.

Two things this module deliberately cannot do. It cannot close a mark: only the
user closes a finding, and a finding is not disposed of by the party it is aimed
at — nor answer one of its own spans, which is a question put to the user
(ADR 0022, decision 5). And it cannot touch the spec or the references: an
agent mark is a proposal, and rule 1's propose -> confirm -> write is untouched
by it.
"""
import argparse
import json
from pathlib import Path

from . import marks, views

USAGE = ('contour mark --part <name> "one line", '
         'or --ref <image> --pixel <x,y> "one line", '
         'or --addressed <mark id>')


def _pixel(text):
    x, y = text.split(",")
    return [int(x), int(y)]


def write(path, text, part=None, ref=None, pixel=None):
    """Append one agent mark. Returns it.

    A mark says where it is in the terms the author actually has. The user
    clicks, so a user mark carries a pixel. The agent does not click: about the
    build it knows *which part* it has a question about, from the same tables
    verification reads, and it names that part and lets the render decide where
    on it the badge goes. About a reference it has no parts to name and a pixel
    is all there is, so it marks one the way the user would.
    """
    if ref:
        return marks.on_reference(path, ref, pixel, text, author="agent")
    return marks.on_part(path, part, text)


def addressed(path, mark_id, blend):
    """Attach *addressed in this build* to one finding. Returns it, or None.

    Not a close, and deliberately hard to mistake for one: the status is not
    touched here and there is no code path in this module that touches it. The
    badge dims, which says the agent believes it has done something about the
    question — and the question stands until the user says otherwise.

    The build is the one on disk, hashed the same way `views.json` hashes it,
    so the agent cannot invent a number and a later reader can tell whether the
    build has moved on since the claim. Which build this is, is the only part of
    the question this module answers: the transition itself belongs to the
    record, in `lib/marks.py`.
    """
    return marks.address(path, mark_id, views.fingerprint(blend))


def known(parts):
    """The part names this build actually has, or None when there is no table.

    `out/parts.json` is written by every render, so it is the build's own list
    and not a second copy of one. Absent means the space has never been
    rendered, which is nothing to refuse a name with.
    """
    parts = Path(parts) if parts else None
    if not parts or not parts.exists():
        return None
    return set(json.loads(parts.read_text(encoding="utf-8")).values())


def command(path, args, blend=None, parts=None):
    """`contour mark`: the agent's one way to say something on the picture.

    A command rather than a file edit, so that ids, authorship and the open
    status are stamped in one place and cannot be got wrong by hand. There is
    deliberately no flag here that closes anything.
    """
    p = argparse.ArgumentParser(prog="contour mark", add_help=False)
    p.add_argument("text", nargs="?")
    p.add_argument("--part")
    p.add_argument("--ref")
    p.add_argument("--pixel", type=_pixel)
    p.add_argument("--addressed")
    try:
        opt = p.parse_args(args)
    except (SystemExit, argparse.ArgumentError):
        return {"ok": False, "lines": [f"FAIL mark  {USAGE}"]}
    if opt.addressed:
        done = addressed(path, opt.addressed, blend)
        if done is None:
            return {"ok": False,
                    "lines": [f"FAIL mark  no mark {opt.addressed} on file"]}
        return {"ok": True, "lines": [f"ok   mark    {done['id']} addressed in "
                                      f"build {marks.addressed(done) or 'no build'}"]}
    if not opt.text or not (opt.part or opt.ref):
        return {"ok": False, "lines": [f"FAIL mark  {USAGE}"]}
    here = known(parts)
    if opt.part and here is not None and opt.part not in here:
        return {"ok": False,
                "lines": [f"FAIL mark  no part {opt.part!r} in this build: "
                          f"{', '.join(sorted(here))}"]}
    stored = write(path, opt.text, part=opt.part, ref=opt.ref, pixel=opt.pixel)
    where = opt.ref or opt.part
    return {"ok": True, "lines": [f"ok   mark    {stored['id']} {where}  {opt.text}"]}
