"""The survey: a model space as seen from outside it (issue 84).

What the lobby, `contour spaces` and the connector know about a space — its row,
its status, its log, its pictures and what each is of, its spend, how its
copies stand, and the trash beside the live list. Derived from the space on
every call and stored nowhere, so no two readers can disagree; and it writes
nothing, so the connector imports it directly (ADR 0024, decision 1) and still
cannot reach a write. Not the *reading* of a reference (CONTEXT.md).

It returns data. How a chat is handed a picture or the spec's text is
`lib/connector.py`'s; how a terminal prints a row is `lib/cli.py`'s.
"""
import json
import re
from datetime import datetime
from pathlib import Path

from . import git, policy, presence, revision, update
from . import space as space_lib

TOOLKIT = Path(__file__).resolve().parent.parent

LOG = "last-build.log"
"""Where every stage leaves Blender's output, in the space's `.contour/`."""

STEM = re.compile(r"(?P<name>.+)-(?P<date>\d{4}-\d{2}-\d{2})(?:-\d+)?")
"""A bundle's file name, as `delete.destination` spells it: the name and date
are there too, for a bundle whose record beside it was lost."""


def toolkit_commit():
    """Which toolkit this is, as a space's marker records it. `unknown` is the
    spelling a person reads for *git could not say* (`lib/git.py`, slice 21)."""
    return git.head(TOOLKIT) or "unknown"


def listing():
    """Every space and its health, as `contour spaces --json` prints it and the
    lobby serves it: one reading, so the two cannot disagree."""
    now, roots = toolkit_commit(), space_lib.roots(TOOLKIT)
    return {"roots": [str(r) for r in roots],
            "spaces": [row(s, now) for s in space_lib.spaces(roots)],
            "deleted": deleted()}


def row(root, now):
    """One space as `spaces` reports it. The text form and the JSON form both
    print this, so they cannot disagree about which spaces exist or which are
    behind (slice 28)."""
    from . import last_run, panel, refs, store, verdict
    was = update.recorded(root)
    here = space_lib.layout(root)
    kept = store.load(here.dot / panel.NAME, None)
    return {"name": root.name, "path": str(root),
            "verdict": verdict.say(kept) if kept else None,
            # What a lobby row shows of it: the last sheet, or before there is
            # one, what it is to be built from (ADR 0025, decision 10).
            "picture": ("sheet" if here.sheet.is_file()
                        else "reference" if refs.listing(here.refs) else None),
            "view": viewed(here) if here.sheet.is_file() else None,
            "worked": worked(here),
            "toolkit": {"commit": was,
                        "state": "unknown" if was is None
                        else "current" if was == now else "behind"},
            "commits": git.commits(root), "remotes": git.remotes(root),
            "scaffold": copies(root),
            "rules": sees_rules(root),
            "presence": presence.live(root),
            # What the lobby's row says while a run is parked, and whether the
            # console there is a requester's, whose page Open brings up
            # (ADR 0027, decision 7).
            "waiting": last_run.parked(root),
            "unattended": last_run.unattended(root),
            # What waits in the space for the person, after its run has ended:
            # the acts, never why (ADR 0028, decision 5).
            "approvals": last_run.approvals(root),
            "awaiting": last_run.awaiting(last_run.approvals(root)),
            "renamed": renamed(root),
            "updated": update.uncommitted(root)}


def copies(root):
    """Which copies are behind, edited or missing: how each stands (issue 83),
    gathered by state, with the ones in step left unsaid."""
    found = update.standing(root, TOOLKIT)
    return {s: [r for r, stands in found.items() if stands == s]
            for s in ("behind", "edited", "missing")}


def out_of_step(root):
    """What `doctor` would find behind the toolkit here: the recorded commit
    and how each copy stands, and nothing else of a row, so a chat, `spaces`
    and `doctor` say the same of every copy."""
    was = update.recorded(root)
    return {"toolkit": "unknown" if was is None
            else "current" if was == toolkit_commit() else "behind",
            **copies(root)}


def sees_rules(root):
    """Whether an agent working in `root` is given the hard rules (open
    question 13): a `CLAUDE.md` of its own, or the toolkit's above it, which
    Claude Code finds by walking up."""
    return ((root / "CLAUDE.md").is_file()
            or (TOOLKIT in root.parents and (TOOLKIT / "CLAUDE.md").is_file()))


def viewed(here):
    """Where on the sheet its perspective view sits, as `{tile, size}`, or None.

    One view and not four is what a row shows: at row size the four-view sheet
    is four thumbnails of a thumbnail, and the perspective is the one that
    reads as the model (ADR 0025, decision 10, as amended by issue 70). Read off
    the views the sheet was drawn with; with none to read, the row shows the
    whole sheet, which is still the model and only harder to see."""
    try:
        drawn = json.loads(here.views.read_text(encoding="utf-8"))
        view = next(v for v in drawn["views"]
                    if v.get("label") == "persp" or v.get("type") == "PERSP")
        return {"tile": [int(n) for n in view["tile"]], "size": int(drawn["resolution"])}
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        return None


def worked(here):
    """When a space was last worked on, as ISO 8601: the newest of the files
    the work touches — the spec, the build, the marks, the references, the
    last check, and the marker `init` wrote, so a model nobody has touched
    since it was made says when it was made. Not the last commit: most work
    sits unsaved until the user says save (rule 5)."""
    from . import panel
    touched = [here.spec, here.build, here.marks, here.sheet, here.dot / panel.NAME,
               here.root / space_lib.MARKER,
               *(here.refs.iterdir() if here.refs.is_dir() else ())]
    times = [p.stat().st_mtime for p in touched if p.is_file()]
    return (datetime.fromtimestamp(max(times)).astimezone().isoformat(timespec="seconds")
            if times else None)


def renamed(root):
    """`{"from": old name}` while a rename is not yet in a commit, else None.

    Read from git each time and stored nowhere: the spec at HEAD names one
    model and the spec on disk another. A space with no commit has nothing to
    have been renamed from."""
    spec = space_lib.layout(root).spec
    was = git.show(root, "HEAD", "spec.yaml")
    if was is None or not spec.exists():
        return None
    old, now = revision.model(was), revision.model(spec.read_text(encoding="utf-8"))
    return {"from": old} if old != now else None


def held_by(rec):
    """Who has the space, in one line the user can act on."""
    return f"pid {rec.get('pid', '?')} running {rec.get('command', 'something')}"


def refusal(root, rec):
    """Why a space refuses a caller, from the hold it met. A run parked at a
    gate is waiting for a person, not busy, and its refusal says for what and
    the two ways on (ADR 0027, decision 9)."""
    from . import last_run
    run = last_run.read(root) or {}
    if run.get("run") == rec.get("run") and run.get("state") == "waiting for you":
        return (f"{last_run.waiting(root, run.get('act'))}. Open it in its "
                f"console, or stop the run with `contour stop {Path(root).name}`.")
    return f"this space is held by {held_by(rec)}."


def status(root):
    """Is it green, and if not why (ADR 0024, decisions 3 and 6) — and the
    same, as the pages say it (ADR 0025, decision 11): beside the report lines,
    so a chat can say what the console's panel says. And the space's latest
    run, which is what a requester comes back for (ADR 0027, decision 8),
    or None where nothing has run."""
    from . import last_run, lock, marks, panel, store, verdict as plainly, vetoes
    here = space_lib.layout(root)
    verdict = store.load(here.dot / panel.NAME, None)
    said = [] if verdict else ["never checked: no verdict here is not a green one"]
    run = last_run.read(root)
    rec = lock.holder(root)
    held = held_by(rec) if rec and lock.alive(rec) else None
    if held and verdict:
        said.append(f"a run is live ({held}); this verdict is from before it")
    waits = last_run.approvals(root)
    if waits:
        said.append(last_run.awaiting(waits))
    return {"verdict": verdict, "plain": verdict and plainly.say(verdict),
            "held": held, "said": said,
            "marks": sum(1 for m in marks.load(here.marks) if marks.is_open(m)),
            "vetoes": vetoes.uncommitted(root),
            "doctor": out_of_step(root), "run": run, "approvals": waits}


def log(root, lines=40):
    """The tail of `last-build.log`, and the stage its first line says wrote it.

    Every stage rewrites the log, so after a check and a filmstrip it is the
    filmstrip's; naming the writer is what keeps it from being read as the
    cause of a red check it never saw (ADR 0024, decision 6).
    """
    try:
        said = (space_lib.layout(root).dot / LOG).read_text().splitlines()
    except FileNotFoundError:
        said = []
    if not said:
        return {"stage": None, "lines": [], "said": ["no log: nothing has run here"]}
    first = said[0].removeprefix("$ ").split()
    stage = "check" if first[:1] == ["build"] else first[0]
    return {"stage": stage, "lines": said[len(said) - max(0, int(lines)):],
            "said": [] if stage == "check"
            else [f"this log is from {stage}, not the last check"]}


def picture(root, which):
    """One of the space's pictures — where it is, if drawn, and what it is of
    (ADR 0024, decision 3). Read off disk only: nothing is rendered to answer.

    The sheet and the filmstrip are of a build, and say so through the panel's
    own comparison, so a chat and the console never disagree about one. The
    worksheet is of the spans on the references, and is behind when they move.
    """
    from . import filmstrip, panel, worksheet
    here = space_lib.layout(root)
    of_build = lambda record: lambda: panel.state(
        views=record, blend=here.blend, verdict=here.dot / panel.NAME)
    path, reading = {
        "sheet": (here.sheet, of_build(here.views)),
        "filmstrip": (here.filmstrip, of_build(here.out / filmstrip.RECORD)),
        "worksheet": (root / worksheet.NAME,
                      lambda: worksheet.state(here.dot, here.marks)),
    }.get(which, (None, None))
    if path is None:
        raise LookupError(f"no picture {which!r}: sheet, filmstrip or worksheet")
    if not path.is_file():
        return {"picture": which, "said": "not drawn yet"}
    return {"picture": which, "path": path, "of": reading()}


def spec(root):
    """The spec as it is on disk, or None before one is drafted."""
    path = space_lib.layout(root).spec
    return path.read_text() if path.is_file() else None


def spent(root):
    """What the console's runs here cost, as `tools/tokens.py` reports them."""
    from . import spend
    runs = spend.runs(root)
    return {"runs": runs,
            "said": [] if runs else ["no console has run here: a terminal "
                                     "session's cost is tools/tokens.py's to read"]}


def trash():
    """Where deleted spaces go: `~/.contour/trash`, beside the ask-list. Only
    files, so the space scan, which looks for a marker in a directory, can
    never take one for a live space."""
    return policy.home() / "trash"


def about(bundle):
    """The record beside a bundle of where its space stood, for restore."""
    return bundle.with_suffix(".json")


def live(path):
    """`path`, if a space stands there now, else None: a bundle whose space was
    restored, or made again under the same name, is not the only copy, and
    the list says so rather than offering a restore the path would refuse."""
    return path if path and (Path(path) / space_lib.MARKER).is_file() else None


def deleted():
    """Every deleted space in the trash, oldest name first. Read from the files
    each time, like the live list (ADR 0021, decision 6)."""
    found = []
    for bundle in sorted(trash().glob("*.bundle")):
        try:
            said = json.loads(about(bundle).read_text())
        except (OSError, ValueError):
            said = {}
        named = STEM.fullmatch(bundle.stem)
        found.append({"id": bundle.stem,
                      "name": said.get("name") or (named and named["name"]),
                      "path": said.get("path"),
                      "deleted": said.get("deleted") or (named and named["date"]),
                      "live": live(said.get("path")),
                      "bundle": str(bundle)})
    return found
