"""The mark store: a located comment, on disk (ADR 0018).

A mark is a comment that knows where it is. It carries the view it was placed
on, the pixel, one line of text, who wrote it, and whether it is still open.

The file is a flat JSON array, tracked by git — a mark is a finding about the
model, and `beaky`'s one known defect lived in the one file nothing verifies
(ADR 0016). It is not a spec: the spec guard covers `refs/` only, so writing
here needs no confirmation gate.
"""
import json
from pathlib import Path

from . import git, store

NAME = "marks.json"
PREFIX = "m"
"""The file and the letter its ids carry. `lib/store.py` holds the mechanics of
a JSON file and none of this: `m1` means a mark, which is a fact about marks."""


def load(path):
    """Every mark on file, or none at all. A space with no marks has no file."""
    return store.load(path, [])


def save(path, marks):
    return store.save(path, marks)


def next_id(marks):
    return store.next_id(marks, PREFIX)


def append(path, mark, author="user"):
    """Store one mark, stamped with its id, author and status. Returns it.

    Always open, whoever wrote it. There is no way to append a closed mark
    because there is no reason to: a finding that was never outstanding is not
    a finding, and `close` is the one door, reached only from the page.
    """
    marks = load(path)
    stored = {"id": next_id(marks), **mark, "author": author, "status": "open"}
    save(path, marks + [stored])
    return stored


def on_sheet(path, view, pixel, text, part=None):
    """A click on one of our four views. Returns the stored mark.

    The view is part of where it is: *too thin* about the front and *too thin*
    about the side are two findings, and a badge has to be drawn on the tile the
    user was looking at. The part is what the identity mask says was under the
    pixel, and is absent when the click landed on background — a remark about a
    gap is about no part at all (ADR 0018).
    """
    mark = {"view": view, "pixel": pixel, "text": text}
    if part:
        mark["part"] = part
    return append(path, mark)


def on_reference(path, ref, pixel, text, to=None, author="user"):
    """A click — or a drag — on one of the user's photographs. Returns it.

    It says *here is what I meant*, and it can never be closed by a build: there
    are no parts in a photograph to anchor into and no render of ours to move
    under it, so the pixel it is born with is the whole answer. With a second end
    it is a **span**, which is what aims `contour measure` at a separation
    (ADR 0018).

    The reference itself is never touched by any of this. Rule 1 is unchanged:
    what is stored here is a comment in the space, beside the picture.
    """
    mark = {"ref": ref, "pixel": pixel, "text": text}
    if to:
        mark["to"] = to
    return append(path, mark, author=author)


def on_part(path, part, text, author="agent", came_from=None):
    """A mark that names a part and no point on it. Returns it.

    The agent's shape, and the shape a promoted veto takes. Neither author
    clicked anything: the agent knows which part it has a question about and
    nothing finer, and a veto was authored against a call, not a pixel. Where on
    the part the badge goes is decided per view against the identity mask, so
    naming the part is enough to be drawn (ADR 0018).

    `came_from` is the veto this became a question about, if it was one. Not a
    resolution — a veto is never resolved — but a reader following the question
    backwards has to land on the moment it came from.

    The part is named at the top level and the record carries no anchor at all,
    which is the whole of what it means to have no pin: an anchor holds a
    position in a part's own coordinates, and a part's name is not one
    (slice 19).
    """
    mark = {"part": part, "text": text}
    if came_from:
        mark["from"] = came_from
    return append(path, mark, author=author)


def pin(mark):
    """Where this mark actually is, in its part's own coordinates, or None.

    A pin and not a pixel: the sheet is regenerated every build, so a pixel
    starts lying the moment geometry moves. A mark that names a part and no
    point on it has no pin, and is badged from the identity mask instead.
    """
    return (mark.get("anchor") or {}).get("local")


def reference(mark):
    """Which of the user's photographs this is on, or None for a sheet mark."""
    return mark.get("ref")


def span_end(mark):
    """The far end of a span, or None when the mark has only one end."""
    return mark.get("to")


def lines(mark):
    """A direction's lines, each `{"from", "to"}`, or None when the mark is
    not a direction (ADR 0032, decision 2)."""
    return mark.get("lines")


def view(mark):
    """Which of our views this was placed on, or None. A ref mark answers None:
    it was drawn by no view of ours."""
    return mark.get("view")


def pixel(mark):
    """Where on that picture it was placed, or None once a ray has spent it."""
    return mark.get("pixel")


def part(mark):
    """Which part this mark is about, or `""`.

    One question with one answer, asked of a record that has two ways of saying
    it: the canvas writes the mask's reading at the top level as the mark is
    born, and a resolved pin carries the part the ray actually hit. Slice 19
    converges the spelling; until it does, every reader asks here rather than
    knowing both (ADR 0018).
    """
    return mark.get("part") or (mark.get("anchor") or {}).get("part") or ""


def text(mark):
    """The one line the author wrote."""
    return mark.get("text", "")


def is_open(mark):
    """Whether this finding still stands. Only the user closes one, so this is
    the question every reader asks and none of them answers."""
    return mark.get("status") == "open"


def anchor(path, found):
    """Write back what the rays found: `{mark id: {"part", "local"}}`.

    Returns the ids that were anchored. The pixel is dropped as the pin lands,
    so `unresolved` needs no flag to read and no mark ever carries two answers
    to the same question. A mark on a photograph is skipped whatever the caller
    offers for it: there are no parts in a photograph to be anchored in.

    What a ray found is two answers and is stored as two. The part it hit is
    written where every part name lives, at the top level, and what stays under
    the anchor is the pin alone — the mask's reading under the click, if there
    was one, is overwritten by the surface the ray actually reached (slice 19).

    The ray itself is cast in `lib/cmd_resolve.py`, which is the only part of
    this that needs a scene. What lands here is the record\'s own transition.
    """
    kept = load(path)
    done = []
    for mark in kept:
        if reference(mark):
            continue
        hit = found.get(mark.get("id"))
        if hit:
            mark.pop("pixel", None)
            mark["part"] = hit["part"]
            mark["anchor"] = {"local": hit["local"]}
            done.append(mark["id"])
    if done:
        save(path, kept)
    return done


def orphan(path, part_names):
    """Say, for every mark that points at a part, whether that part is still in
    the build. Returns the ids now orphaned.

    The flag is what the last build found, not a scar: a part that comes back
    takes its pins back with it. Deleting a part does not answer the question
    that was asked about it, so the pin is said to be homeless rather than
    re-projected against whatever happens to be nearest — which is the same
    mistake nearest-centroid makes, one build later (ADR 0018).

    A mark still carrying a pixel is not asked. It is waiting on a ray, and what
    part it will turn out to be about is not yet anybody\'s answer.
    """
    kept = load(path)
    gone, before = [], json.dumps(kept)
    for mark in kept:
        if not part(mark) or pixel(mark):
            continue
        if part(mark) in part_names:
            mark.pop("orphaned", None)   # a rename undone, a part back in build.py
        else:
            mark["orphaned"] = True
            gone.append(mark["id"])
    if json.dumps(kept) != before:
        save(path, kept)
    return gone


def orphaned(mark):
    """Whether the part this mark points at is missing from the last build."""
    return bool(mark.get("orphaned"))


def address(path, mark_id, build):
    """Attach *addressed in this build* to one finding. Returns it, or None.

    Not a close, and deliberately hard to mistake for one: the status is not
    touched here. The badge dims, which says the agent believes it has done
    something about the question — and the question stands until the user says
    otherwise (ADR 0018).

    `build` is a fingerprint the caller already has, passed in rather than
    computed: which build this is belongs to `lib/views.py`, and a record does
    not reach for a `.blend` to find out what it is being told.
    """
    kept = load(path)
    found = None
    for mark in kept:
        if mark.get("id") == mark_id:
            mark["addressed"] = build
            found = mark
    if found is not None:
        save(path, kept)
    return found


def addressed(mark):
    """The build the agent claims deals with this, or None. Never a close."""
    return mark.get("addressed")


def unresolved(all_marks):
    """The marks still waiting on a ray: a pixel, and no pin yet.

    A ref mark is never among them. It points into a photograph, which has no
    parts and never gets rebuilt, so its pixel is the whole answer (ADR 0018).
    """
    return [m for m in all_marks
            if pixel(m) and not pin(m) and not reference(m)]


def old_spelling(all_marks):
    """The marks still keeping a part's name under the anchor (slice 19).

    What `contour doctor` counts and what `migrate` rewrites, asked of a list
    so that counting one costs no more than reading the file already did.

    A space is never migrated on load and may never be migrated at all: the
    reader above is bilingual, so an untouched space keeps working, and the
    only thing this slice ends is new marks being written either way. Which is
    also why this is a question a space can be asked rather than a state it is
    put into.
    """
    return [m for m in all_marks if (m.get("anchor") or {}).get("part")]


def migrate(path):
    """Move every part name out of the anchor and up to the top level. Returns
    the ids rewritten, and writes nothing when there are none.

    Idempotent by what it asks: a record already in one spelling has no name
    under its anchor, so running this twice is running it once and then reading
    the file. An anchor left holding nothing at all is dropped rather than kept
    empty — that is an agent's mark, which never had a pin, and `{}` there
    would be a third spelling of *no pin* for the next reader to handle.

    Which part a mark is about does not change here. A record written before
    this slice can carry both spellings at once and they can disagree — the
    canvas wrote the mask's reading as the mark was born, and a ray later wrote
    the surface it hit under the anchor without touching it — and every reader
    since has answered with the top-level one. So that is the one kept.
    Preferring the ray may well be right; it is not a decision a rewrite makes
    on the way past. No record written from here on can disagree with itself:
    `anchor` above writes the one field.

    The record is rebuilt rather than edited so the name takes the anchor's
    place in it. This is the one commit that rewrites `marks.json` wholesale,
    and a name appended at the end would put the line that went and the line
    that arrived in different hunks of the diff the user has to review.
    """
    kept = load(path)
    moved = []
    for at, mark in enumerate(kept):
        name = (mark.get("anchor") or {}).get("part")
        if not name:
            continue
        pin_only = {k: v for k, v in mark["anchor"].items() if k != "part"}
        fresh = {}
        for key, value in mark.items():
            if key != "anchor":
                fresh[key] = value
                continue
            fresh.setdefault("part", name)
            if pin_only:
                fresh["anchor"] = pin_only
        kept[at] = fresh
        moved.append(mark["id"])
    if moved:
        save(path, kept)
    return moved


def close(path, mark_id):
    """Mark one finding as dealt with, by the only party allowed to say so.

    Returns the closed mark, or None if no such id is on file — the page can
    be looking at a list the store no longer has.
    """
    marks = load(path)
    found = None
    for mark in marks:
        if mark.get("id") == mark_id:
            mark["status"] = "closed"
            found = mark
    if found is not None:
        save(path, marks)
    return found


def answered(mark):
    """How the user answered this agent span — `adopted`, `corrected`,
    `rejected` — or None while it is still a question (ADR 0022, decision 5)."""
    return mark.get("answer")


def by_eye(all_marks):
    """The open agent spans placed by eye that the user has not answered: the
    ones whose numbers cannot be proposed yet, which a run waits on (ADR 0035,
    decision 2). A snapped span is not one, nor is a direction."""
    return [m for m in all_marks
            if m.get("author") == "agent" and reference(m) and span_end(m)
            and m.get("placed") == "by eye" and is_open(m) and not answered(m)]


def _answering(path, mark_id, change, then=None):
    """Give one agent span the user's answer. Returns `{"mark": ...}`, or
    `{"refused": why}` with nothing written.

    Only an open agent span with no answer yet is a question. Once adopted or
    corrected it is the user's, so it cannot be answered twice; once rejected
    it is closed. `change(mark, kept)` edits the record in place — and may add
    to `kept`, which is saved with it — or returns why it refuses.

    The mark comes with the answer's slip: what `unanswer` needs to take it
    back (issue 136). `then(kept, mark)` runs after the change, inside the
    same write: what the answer changes beyond its own mark, such as the
    readings it reads again (issue 141), is then undone with it.
    """
    kept = load(path)
    found = next((m for m in kept if m.get("id") == mark_id), None)
    if found is None:
        return {"refused": f"no mark {mark_id} on file"}
    if not (found.get("author") == "agent" and reference(found)
            and (span_end(found) or lines(found)) and is_open(found)
            and not answered(found)):
        return {"refused": f"{mark_id} is not an agent span or direction "
                           f"waiting on an answer: only an open one the agent "
                           f"drew is a question"}
    was = json.loads(json.dumps(kept))      # as it stood, untouched by change
    refused = change(found, kept)
    if refused:
        return {"refused": refused}
    if then:
        then(kept, found)
    save(path, kept)
    return {"mark": found, "slip": _slip(mark_id, was, kept)}


def _slip(mark_id, was, now):
    """What one answer to `mark_id` did: every record it touched, as it was
    and as the answer left it. A record it added has no before."""
    before = {m.get("id"): m for m in was}
    touched = [m for m in now if before.get(m.get("id")) != m]
    return {"id": mark_id,
            "before": [before[m["id"]] for m in touched if m["id"] in before],
            "after": json.loads(json.dumps(touched))}


def unanswer(path, slip):
    """Take one answer back, for a slip (issue 136): every record it touched
    as it was, in its place, and any it added gone, so the file is as it was
    before the answer. Returns `{"mark": span}`, or `{"refused": why}` with
    nothing written.

    Only while all of it is still exactly as the answer left it. Anything
    since — another answer, a run's use of the number — means the answer has
    been built on, and it stands (ADR 0022, decision 5).
    """
    kept = load(path)
    here = {m.get("id"): m for m in kept}
    for m in slip["after"]:
        if here.get(m["id"]) != m:
            return {"refused": f"{m['id']} has changed since you answered, so "
                               f"the answer stands"}
    before = {m["id"]: m for m in slip["before"]}
    added = {m["id"] for m in slip["after"]} - set(before)
    save(path, [before.get(m.get("id"), m) for m in kept if m.get("id") not in added])
    return {"mark": before[slip["id"]]}


def spanned(path, mark, answer, at):
    """An agent span and the reading pinned beside it, stored together in one
    write. Returns `(span, reading)`.

    Linked from the start: the span keeps its reading's id, so whatever the
    user answers can reach the number it gave without reading prose. `answer`
    is the reading without the span's id, which only the store knows yet.
    """
    kept = load(path)
    drawn = {"id": next_id(kept), **mark, "author": "agent", "status": "open"}
    said = _reading(next_id(kept + [drawn]), drawn["id"], drawn["ref"], answer, at)
    drawn["reading"] = said["id"]
    save(path, kept + [drawn, said])
    return drawn, said


def _reading(mark_id, of, ref, answer, at):
    """The agent mark that carries a span's number, pinned at `at`."""
    return {"id": mark_id, "ref": ref, "pixel": at, "text": f"span {of}: {answer}",
            "author": "agent", "status": "open"}


def reading_of(kept, mark):
    """The reading a span gave, among `kept`, or None for a span drawn before
    readings were linked, or for a mark that is no span."""
    return next((m for m in kept if m.get("id") == mark.get("reading")), None)


def restate(said, mark, answer):
    """A span's reading, said again: what the span reads now that its
    reference's foundations have changed (issue 141). In place, in a list the
    caller saves, as an answer's `then` does."""
    said["text"] = f"span {mark['id']}: {answer}"


def old_way(all_marks):
    """The spans whose number is still a reading made the old way: at a scale
    the foreground box gave, not yet read again through the camera (ADR 0032,
    decision 7). A span drawn with no anchor kept no scale to read at, so its
    pixels were no box's number."""
    return [m for m in all_marks if isinstance(m.get("scale"), (int, float))
            and is_open(reading_of(all_marks, m) or {"status": "closed"})]


def supersede(kept, mark, answer):
    """A span's old reading, made at a scale it kept from the foreground box,
    replaced by one through the camera (issue 142). Nothing is deleted: the
    old reading is closed as superseded, as a correction's is, and the new one
    says which it replaced. The span keeps no scale after: it is read through
    the camera from then on. In place, in a list the caller saves."""
    old = _superseded(kept, mark)
    old["superseded"] = True
    said = _reading(next_id(kept), mark["id"], mark["ref"], answer, old["pixel"])
    said["was"] = old["id"]
    kept.append(said)
    mark["reading"] = said["id"]
    mark.pop("scale")


def _superseded(kept, mark):
    """Close the reading a span gave: its number no longer stands. Returns it,
    or None for a span drawn before readings were linked."""
    old = reading_of(kept, mark)
    if old is not None:
        old["status"] = "closed"
    return old


def adopt(path, mark_id, then=None):
    """*It is right.* The span is the user's from then on, and still says who
    drew it."""
    def change(mark, kept):
        mark.update(author="user", drawn_by="agent", answer="adopted")
    return _answering(path, mark_id, change, then)


def correct(path, mark_id, pixel, to, answer, then=None):
    """*Not quite: here.* The span takes the user's ends and is theirs, keeps
    the ends the agent drew, and is answered afresh. `answer` is the reading
    at the new ends, worked out by the caller, which knows the scale.

    No longer snapped: the user placed it, so no question would place these
    ends again, and the agent's question goes with the flag.
    """
    def change(mark, kept):
        if lines(mark):
            return f"{mark_id} is a direction, not a span: it is corrected by its lines"
        if not (pixel and to) or list(pixel) == list(to):
            return "a correction needs two different ends"
        _superseded(kept, mark)
        at = [round((pixel[0] + to[0]) / 2), round((pixel[1] + to[1]) / 2)]
        said = _reading(next_id(kept), mark_id, mark["ref"], answer, at)
        kept.append(said)
        mark.update(author="user", drawn_by="agent", answer="corrected",
                    agent_ends=[mark["pixel"], mark["to"]],
                    pixel=list(pixel), to=list(to), reading=said["id"])
        mark.pop("placed", None)
        mark.pop("question", None)
        return None
    return _answering(path, mark_id, change, then)


def correct_lines(path, mark_id, drawn, then=None):
    """*Not quite: these edges.* A direction takes the user's lines and is
    theirs, and keeps the lines the agent drew, as a corrected span keeps its
    ends. The user placed them, so no question would place them again, and
    each line's goes."""
    def change(mark, kept):
        if not lines(mark):
            return f"{mark_id} is a span, not a direction: it is corrected by its ends"
        if len(drawn) < 2:
            return "a direction needs at least two lines, since it is where they meet"
        mark.update(author="user", drawn_by="agent", answer="corrected",
                    agent_lines=mark["lines"],
                    lines=[{"from": list(got["from"]), "to": list(got["to"])} for got in drawn])
        return None
    return _answering(path, mark_id, change, then)


def reject(path, mark_id, why, then=None):
    """*It measured the wrong thing.* Closed, with the user's one line of why,
    and its number — on the span and on the reading — marked not to be used.

    A reason is required: a rejection with none tells the agent only that it
    was wrong, and the next span it draws would be drawn as blind.
    """
    why = (why or "").strip()

    def change(mark, kept):
        if not why:
            return "a rejection needs a reason: one line of what it measured instead"
        old = _superseded(kept, mark)
        if old is not None:
            old["unused"] = True
        mark.update(status="closed", answer="rejected", why=why, unused=True)
        return None
    return _answering(path, mark_id, change, then)


def _released(path):
    """The last release tag and the marks it holds — `(tag, marks)`, or
    `(None, [])` when there is no tag to archive anything.

    The tag *is* the archive, so `git show` is asked what it actually
    contains rather than a stamp of our own being trusted about it.
    """
    path = Path(path)
    released = git.releases(path.parent)
    if not released:
        return None, []
    tag = released[0]
    blob = git.show(path.parent, tag, path.name)
    try:
        return tag, (json.loads(blob) if blob else [])
    except json.JSONDecodeError:
        return tag, []


def prune(path):
    """Drop closed marks the last release tag already holds.

    Returns a line naming what went and where it still is, or None when
    nothing was dropped: deleting from a tracked file in silence is worse
    than not deleting at all.

    Open marks are never pruned, at any age — an unanswered finding does not
    expire — and nothing is dropped that git cannot show back, so with no tag,
    or no marks file in it, this does nothing at all.
    """
    tag, archived = _released(path)
    if not archived:
        return None
    gone = {m.get("id") for m in archived if m.get("status") == "closed"}
    here = load(path)
    kept = [m for m in here
            if not (m.get("status") == "closed" and m.get("id") in gone)]
    dropped = len(here) - len(kept)
    if not dropped:
        return None
    save(path, kept)
    return f"{phrase(dropped)} pruned, closed at {tag}"


def phrase(n):
    """`3 marks`, `1 mark` — the count with the right noun on it."""
    return f"{n} mark{'' if n == 1 else 's'}"


def status_line(path):
    """What `contour check` says about the marks, or None when there is
    nothing to say (ADR 0018).

    Never red, and never part of the exit code: red means the build violates
    the spec, and a mark is precisely the thing the spec did not catch.
    """
    n = sum(1 for m in load(path) if m.get("status") == "open")
    return f"{phrase(n)} open" if n else None
