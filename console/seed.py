"""What a run was started from: the marks in scope (ADR 0019, decision 21).

A run starts from prose. Marks may seed it, and seeding is composition rather
than a second kind of run: the selected marks become lines above the prose, and
what reaches the agent is one prompt. The alternative — a mode that takes marks
instead of words — would need the user to decide before typing which kind of
thing they were about to ask for, and *why is the neck 269* is neither.

Above `lib/` for the same reason `console/vetoes.py` is: the scope of a run is
the console's own knowledge. No `contour` subcommand has a run to know it about.
"""
from lib import marks


def where(mark):
    """The place part of a located comment, in the words the page shows: the view
    it was placed on and the part it landed on. Which part that is, is asked of the
    record rather than read off it: a mark has two ways of saying so until slice
    19 converges them, and knowing both here was one of the copies slice 18
    removed (ADR 0018).

    A ref mark answers this with the photograph alone. It was drawn by none of
    our views and has no part to land on, so the image *is* where it is — and
    saying `front` about it would send the agent to a render of ours instead.
    """
    if marks.reference(mark):
        return marks.reference(mark)
    return " ".join(w for w in (marks.view(mark) or "", marks.part(mark)) if w)


def sentence(mark):
    """One seeded mark, as the agent reads it. The id leads, because the report
    at the end of the run names marks by id and the agent has to have been told
    which name is which. Then where it is, because *too thin* about the neck and
    *too thin* about the beak are two different findings."""
    return f"- {mark['id']} ({where(mark)}): {marks.text(mark)}"


def compose(space, prose, ids):
    """The prompt a run starts from, and the marks it was seeded with.

    Returns `(prompt, seeded)`. With nothing selected the prose is the prompt
    unchanged: a run from prose is the base case and must not acquire a preamble
    just because this module exists.

    An id the store cannot honour — closed in another tab, pruned, never there —
    is dropped and the drop is named in the prompt. Refusing the whole run would
    block work the user meant over a mark they had just finished with; dropping it
    in silence would hide the one thing this module exists to make visible, a
    finding quietly falling out of scope.
    """
    on_file = {m["id"]: m for m in marks.load(space / marks.NAME)
               if marks.is_open(m)}
    wanted = list(ids or [])
    seeded = [on_file[i] for i in wanted if i in on_file]
    missing = [i for i in wanted if i not in on_file]
    if not seeded and not missing:
        return prose, []
    lines = []
    if seeded:
        lines.append("These open marks are what this run is about:")
        lines += [sentence(m) for m in seeded]
    if missing:
        lines.append(f"Not seeded, no longer open: {', '.join(missing)}")
    # The prose only if there is any. A selection is a complete request — the
    # marks are sentences about the model, written where they apply — and a blank
    # line where prose would have been reads as something not yet said.
    if prose:
        lines += ["", prose]
    return "\n".join(lines), seeded


def state(before, now):
    """What became of one seeded mark: `orphaned`, `addressed` or `unaddressed`.

    Orphaned first, and over the top of any claim. A part the build deleted
    leaves the pin with nowhere to point, and deleting a part does not answer the
    question that was asked about it — so *addressed* there would be a finding
    that looks dealt with and cannot be checked (ADR 0018).

    Addressed means *addressed by this run*, which is why the stamp the mark
    carried when it was seeded is remembered and compared rather than merely
    looked for. A mark the agent claimed two builds ago would otherwise seed a
    run and report itself dealt with without the agent touching it — the check
    passing precisely when there is nothing behind it.
    """
    if marks.orphaned(now):
        return "orphaned — its part is not in the build any more"
    stamp = marks.addressed(now)
    if stamp and stamp != marks.addressed(before):
        return f"addressed in build {stamp}"
    return "unaddressed"


def report(space, seeded):
    """What became of the marks this run was started from, as the page reads it.

    A report and only a report. Nothing here closes a mark, dims one, or writes
    to the store at all: `addressed` is the agent's claim and closing is the
    user's act, and the console being the one that knows the scope does not make
    it the one that gets to decide (ADR 0018, ADR 0019, decision 21).
    """
    if not seeded:
        return None
    now = {m["id"]: m for m in marks.load(space / marks.NAME)}
    lines = []
    for mark in seeded:
        here = now.get(mark["id"], {})
        lines.append(f"{mark['id']} ({where(mark)}): {state(mark, here)}")
    return "\n".join(lines)
