"""Contour CLI: the only sanctioned way to run Blender (ADR 0008).

Run the model commands from inside a model space — the directory holding
spec.yaml, found by walking up for .contour/project (ADR 0015). A model is
never named on the command line: you are standing in it.

Blender's stdout (~2-5k tokens of banner and chatter per run) goes to
.contour/last-build.log. The Blender side writes a JSON report; this wrapper
prints only its terse `lines`. Stdlib only: no venv, no yaml.

What used to be the whole of `./contour`, which is now a shim that calls
`main` (issue 24). The commands themselves are rows in `lib/commands.py`, and
`main` is the one place their columns are applied: arity, then the space, then
the hold. Moving here is what made any of it importable — the launcher had no
`.py` extension, so its tests spawned it against a stub Blender or read it as
text. ADR 0008 is about Blender only ever being run through `contour`, not
about where the code that runs it sits.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from lib import commands, delete, git, presence, rename, restore, revision, space     # stdlib-only by test (ADR 0019, 29)

ROOT = Path(__file__).resolve().parent.parent
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
TIMEOUT_S = 300


def usage():
    """The help: the prose above about Blender's output, then one line per
    usage entry in the table, rendered so none can be missing or left over."""
    rows = [(args, text) for c in commands.TABLE for args, text in c.usage]
    width = max(len(args) for args, _ in rows) + 2
    return "\n".join([__doc__.split("\n\n", 3)[2].rstrip(), ""]
                     + [f"    contour {args:<{width}}{text}".rstrip() for args, text in rows])


MARKER = space.MARKER
PROJECT = space.find()
HERE = space.layout(PROJECT, ROOT) if PROJECT else None
"""The layout of the space this was typed in, or None outside one.

Asked of the space rather than derived here: `out/<name>.blend` was spelled in
five places and `marks.json` in nine, all of them restating ADR 0015 (slice 17).
"""
OUT = (HERE.dot if HERE else ROOT / ".contour")   # logs sit with whatever the command is about
LOG = OUT / "last-build.log"
REPORT = OUT / "report.json"


def stage(args, first=True):
    """Run one Blender process. Returns its report dict, never raises."""
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.unlink(missing_ok=True)
    cmd = [BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
           "--python", str(ROOT / "lib" / "entry.py"), "--", *args]
    env = dict(os.environ, CONTOUR_ROOT=str(ROOT), CONTOUR_REPORT=str(REPORT),
               PYTHONDONTWRITEBYTECODE="1")
    if PROJECT:
        env["CONTOUR_PROJECT"] = str(PROJECT)
    t0 = time.time()
    with open(LOG, "w" if first else "a") as log:
        log.write(f"$ {' '.join(args)}\n")
        log.flush()
        try:
            rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env,
                                timeout=TIMEOUT_S).returncode
        except subprocess.TimeoutExpired:
            return {"ok": False, "lines": [f"FAIL blender timed out after {TIMEOUT_S}s"]}
        except FileNotFoundError:
            return {"ok": False, "lines": [f"FAIL no Blender at {BLENDER} (set $BLENDER)"]}
    if REPORT.exists():
        rep = json.loads(REPORT.read_text())
    else:
        tail = LOG.read_text().strip().splitlines()[-8:]
        rep = {"ok": False, "lines": [f"FAIL blender exit {rc}, no report", *tail]}
    rep["secs"] = round(time.time() - t0, 1)
    return rep


def emit(rep):
    print("\n".join(rep["lines"]))
    if not rep["ok"] and "secs" in rep:   # only Blender stages write that log
        print(f"(full log: {LOG})")
    return 0 if rep["ok"] else 1


def need_project(cmd):
    """Say so plainly. Never fall back to the toolkit's own directory: a stray
    `contour check` elsewhere would then build something unexpected (ADR 0015)."""
    print(f"contour {cmd}: not in a model space.\n"
          f"  No {MARKER} found here or above {Path.cwd()}.\n"
          f"  cd into a model space — the directory holding spec.yaml.",
          file=sys.stderr)
    return 2


spec_revision = revision.of


def check_revision():
    """A spec may change; it may not change silently (ADR 0016).

    Rule 1 used to make an unapproved spec edit impossible. Now it makes one
    noisy, and this is the noise: content that differs from HEAD without a bump
    is the one case where a change nobody approved looks different from a
    change that was. Returns None when there is nothing to say — this runs on
    every model command, so it is silent on success and costs nothing.
    """
    found = revision.unbumped(PROJECT)
    if found is None:
        return None
    was, is_ = found
    return {"ok": False, "lines": [
        f"FAIL revision  spec.yaml differs from HEAD, revision still {is_}",
        "  The spec is the user's intent. It may be revised once they have",
        "  confirmed the change, never quietly (rule 1, ADR 0016).",
        f"  confirmed -> set revision: {was + 1}   not confirmed -> git checkout -- spec.yaml"]}


def say_marks(code):
    """What the canvas has to say, after the check has said its piece (ADR 0018).

    Never red and never part of the exit code: red means the build violates the
    spec, and a mark exists precisely because the spec did not catch the thing.
    Silent at zero, so it costs nothing on the command run dozens of times a
    session.
    """
    from lib import marks
    line = marks.status_line(HERE.marks)
    if line:
        print(line)
    return code


def held_by(rec):
    """Who has the space, in one line the user can act on."""
    return f"pid {rec.get('pid', '?')} running {rec.get('command', 'something')}"


def hold(command, doing=None):
    """Take the space for the length of this call, or refuse and say who has it.

    `command` is what *this* caller is; `doing` is what goes on the record, so
    the next caller's refusal can name a process it could go and look at.
    """
    from lib import lock
    try:
        record = lock.take(PROJECT, doing or command,
                           run=os.environ.get("CONTOUR_RUN"))
        if record.get("took_over"):
            print(f"ok   lock    took over the hold left by "
                  f"{held_by(record['took_over'])}, which is gone")
        return record
    except Exception as e:
        rec = getattr(e, "record", None)
        if rec is None:
            raise
        print(f"contour {command}: this space is held by {held_by(rec)}.",
              file=sys.stderr)
        return None


def free(record):
    """Release the space, whatever happened — a failed or interrupted run that
    kept the lock would wedge the space until somebody found the file."""
    from lib import lock
    lock.release(PROJECT, record)




def on_run(cmd, rest, held):
    """`contour run <cmd>...`: one run, holding the space while it lasts.

    The unit the lock is scoped to. What races is the `build.py` editing
    *between* builds, so a build-scoped lock would look like a fix and not be
    one — the holder here is the whole session, whatever it does. The hold is
    taken by `main`, like every other; what this adds is handing its run id to
    the process inside, so the builds that process starts are inside the hold
    rather than refused by it.
    """
    env = dict(os.environ, CONTOUR_RUN=held["run"])
    try:
        return subprocess.run(rest, env=env).returncode
    except KeyboardInterrupt:
        return 130


def draw(rep):
    """Render for the page, once the build is on disk (ADR 0019, decision 24).

    Renders were rate-limited because a sheet entering the *conversation* costs
    ~1400 tokens (ADR 0005) — a cost to the agent's context and not to the
    render. A sheet going to a page costs neither, so the panel can be current
    instead of labelled stale, and this report gains no line: the agent still
    pulls a sheet into context only at a checkpoint.

    Nothing is drawn unless the build got as far as saving. A `build.py` that
    raised leaves no report and no geometry, and rendering then would produce a
    picture of a model that has never existed, in the panel where every other
    picture is real. A *verify-red* build is not that: it saved, and the wrong
    model is exactly what the user needs to look at.
    """
    if "results" not in rep:
        return rep
    drawn = stage(["render"], first=False)
    if drawn["ok"]:
        return rep                            # the panel is current; say nothing
    # A render that failed after a build that saved is a finding, and rule 2 says
    # report it. Never the exit code, though: what the check judged is the spec.
    return {**rep, "lines": [*rep["lines"],
                             *[f"warn {line}" for line in drawn["lines"]]]}


def on_build(cmd, rest, held):
    """The commands the table files under `build`: the ones that write `out/`
    and read the spec, and so the ones a second run may not join in on."""
    drifted = check_revision()
    if drifted:
        return emit(drifted)
    if cmd == "check":
        rep = stage(["build"])
        from lib import panel
        panel.record(OUT / panel.NAME, rep)
        return say_marks(emit(draw(rep)))
    if cmd != "export":
        return emit(stage([cmd]))
    rep = stage(["export"])
    if not rep["ok"]:
        return emit(rep)
    rt = stage(["roundtrip"], first=False)
    rt["lines"] = rep["lines"] + rt["lines"]
    return emit(rt)


def on_api(cmd, rest, held):
    return emit(stage(["api", *rest]))


def on_measure(cmd, rest, held):
    return emit(stage(["measure", *rest]))


def on_canvas(cmd, rest, held):
    from lib import canvas, panel, signals
    # All three, and not only Ctrl-C: the presence below is taken back only on
    # a path out of the session, and SIGTERM or a closed terminal would
    # otherwise end the process where it stood (issue 27, issue 30).
    signals.raising(*signals.STOPPING)
    with presence.present(PROJECT, "canvas"):
        report = canvas.serve(HERE.sheet, HERE.marks, HERE.mask, HERE.parts,
                              resolve=lambda: stage(["resolve"]),
                              refs=HERE.refs, views=HERE.views,
                              blend=HERE.blend,
                              verdict=HERE.dot / panel.NAME)
    return emit(report)


def on_resolve(cmd, rest, held):
    """One ray per unresolved mark, against the build the sheet was drawn from.

    ADR 0018 ran this at canvas close because that was the last moment before
    geometry could change; the console knows a better one — the instant a build
    is approved — and reaches it by typing this (ADR 0019, decisions 10 and 14).

    Held like a build, because it reads the build: rays cast while another
    terminal is rebuilding would land in geometry that is being replaced
    underneath them. The console's own resolve carries `$CONTOUR_RUN`, so the
    hold its run already took is one it is inside of (slice 02).
    """
    return emit(stage(["resolve"]))


def on_mark(cmd, rest, held):
    from lib import agent
    return emit(agent.command(HERE.marks, rest, HERE.blend, HERE.parts))


def on_selftest(cmd, rest, held):
    return emit(stage_selftest())


def on_install_hooks(cmd, rest, held):
    return emit(install_hooks())


def on_init(cmd, rest, held):
    return emit(init(rest[0]))


def on_doctor(cmd, rest, held):
    return emit(doctor())


def on_migrate_marks(cmd, rest, held):
    return emit(migrate_marks())


def on_spaces(cmd, rest, held):
    if rest == ["--json"]:
        return emit(spaces(as_json=True))
    return emit(spaces(rest[0] if rest else None))


def on_lobby(cmd, rest, held):
    from lib import lobby
    return emit(lobby.serve(listing, grace=seconds("CONTOUR_LOBBY_GRACE", lobby.GRACE_S)))


def on_rename(cmd, rest, held):
    """Proposes, or with `--yes` does what it proposed (ADR 0021, decision 5).

    `holds` is False in the table and the hold is taken in `rename.perform`:
    the lock file moves with the directory, so it has to be released at the
    new path, which `main` does not know.
    """
    names = [w for w in rest if not w.startswith("--")]
    if len(names) != 1:
        print(usage(), file=sys.stderr)
        return 2
    said = (rename.perform if "--yes" in rest else rename.propose)(PROJECT, names[0], ROOT)
    if "--json" in rest:
        return emit({"ok": not said["refused"], "lines": [json.dumps(said, indent=2)]})
    if said["refused"]:
        return emit({"ok": False, "lines": [f"FAIL rename  {said['refused']}"]})
    if "--yes" in rest:
        return emit({"ok": True, "lines": [f"ok   renamed to {said['to']}",
                                           f"     cd {said['to']}"]})
    return emit({"ok": True, "lines": rename.lines(said)})


def on_delete(cmd, rest, held):
    """Proposes, or with `--yes` deletes, leaving a bundle (ADR 0021, decision 6).

    `holds` is False in the table and the hold is taken in `delete.perform`:
    the lock file is inside the space, and goes with it. The name is the
    first word whatever it says, because what a page sends is whatever was
    typed, and a typed `--yes` must be a wrong name and not a confirm.
    """
    typed, flags = rest[0], rest[1:]
    if not set(flags) <= {"--yes", "--json"}:
        print(usage(), file=sys.stderr)
        return 2
    said = (delete.perform if "--yes" in flags else delete.propose)(PROJECT, typed)
    if "--json" in flags:
        return emit({"ok": not said["refused"], "lines": [json.dumps(said, indent=2)]})
    if said["refused"]:
        return emit({"ok": False, "lines": [f"FAIL delete  {said['refused']}"]})
    if "--yes" in flags:
        return emit({"ok": True, "lines": [f"ok   deleted {said['path']}",
                                           f"     its bundle: {said['bundle']}"]})
    return emit({"ok": True, "lines": delete.lines(said)})


def on_restore(cmd, rest, held):
    """A deleted space, cloned back from its bundle (ADR 0021, decision 6)."""
    words = list(rest)
    as_json = "--json" in words
    if as_json:
        words.remove("--json")
    to = None
    if "--to" in words:
        i = words.index("--to")
        if i + 1 >= len(words):
            print(usage(), file=sys.stderr)
            return 2
        to = words.pop(i + 1)
        words.pop(i)
    if len(words) != 1:
        print(usage(), file=sys.stderr)
        return 2
    said = restore.restore(words[0], ROOT, to)
    if as_json:
        return emit({"ok": not said["refused"], "lines": [json.dumps(said, indent=2)]})
    if said["refused"]:
        return emit({"ok": False, "lines": [f"FAIL restore  {said['refused']}"]})
    return emit({"ok": True, "lines": [f"ok   restored {said['path']}",
                                       f"     cd {said['path']}"]})


def on_purge(cmd, rest, held):
    """Proposes removing a bundle from the trash, or with `--yes` removes it.
    The id is the first word whatever it says, as `delete`'s name is."""
    typed, flags = rest[0], rest[1:]
    if not set(flags) <= {"--yes", "--json"}:
        print(usage(), file=sys.stderr)
        return 2
    said = (restore.purge if "--yes" in flags else restore.proposed_purge)(typed)
    if "--json" in flags:
        return emit({"ok": not said["refused"], "lines": [json.dumps(said, indent=2)]})
    if said["refused"]:
        return emit({"ok": False, "lines": [f"FAIL purge  {said['refused']}"]})
    if "--yes" in flags:
        return emit({"ok": True, "lines": [f"ok   removed {said['bundle']}"]})
    return emit({"ok": True, "lines": restore.purge_lines(said)})


def seconds(name, fallback):
    """A timeout from the environment, so a test proving what a silence means
    does not have to wait out the real one."""
    return float(os.environ.get(name) or fallback)


def on_intents(cmd, rest, held):
    from lib import intent
    print("\n".join(intent.categories()))
    return 0


def on_asks(cmd, rest, held):
    from lib import policy
    try:
        print("\n".join(policy.report(PROJECT)))
    except policy.PolicyError as e:
        return emit({"ok": False, "lines": [f"FAIL {e}"]})
    return 0


def on_hook(cmd, rest, held):
    return run_hook(rest[0], rest[1:])


def takes(row, rest):
    """Whether this many words may follow the command."""
    least, most = row.arity
    return least <= len(rest) and (most is None or len(rest) <= most)


def main(argv):
    """Find the row, then apply its columns in order: arity, space, hold.

    The one place they are applied. Arity comes first, so a mistyped call is
    answered with the usage wherever it is typed; the space next, so a command
    that needs one says so plainly rather than holding nothing; the hold last,
    and released whatever the handler did.
    """
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(usage())
        return 0
    cmd, rest = argv[0], argv[1:]
    row = next((c for c in commands.TABLE if c.name == cmd), None)
    if row is None or not takes(row, rest):
        print(usage(), file=sys.stderr)
        return 2
    if row.space and not PROJECT:
        return need_project(cmd)
    handler = globals()[row.handler]
    if not row.holds:
        return handler(cmd, rest, None)
    record = hold(cmd, " ".join([cmd, *rest]))
    if record is None:
        return 3
    try:
        return handler(cmd, rest, record)
    finally:
        free(record)


SCAFFOLD = space.SCAFFOLD
template = space.template      # `init` names its new space `space`
stub = space.stub


def toolkit_commit():
    """Which toolkit this is, as a space's marker records it. `unknown` is the
    spelling a person reads for *git could not say* (`lib/git.py`, slice 21)."""
    return git.head(ROOT) or "unknown"


def init(name):
    """Create a model space (ADR 0015): its own directory, its own git repo.

    Copies only what the agent must read from the working directory. The
    guards are never copied — settings.json and the pre-push stub call the
    installed toolkit, so there is one implementation and nothing to drift.
    """
    space = (Path.cwd() / name).resolve()
    if (space / MARKER).exists():
        return {"ok": False, "lines": [f"FAIL {space} is already a model space"]}
    tpl = ROOT / "templates" / "space"
    (space / ".contour").mkdir(parents=True, exist_ok=True)
    (space / "refs").mkdir(exist_ok=True)
    kept = []
    for rel in SCAFFOLD:
        dst = space / rel
        if dst.exists():                  # adopting a directory: never clobber
            kept.append(rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(template(ROOT, rel, space.name))
    if not (space / ".gitignore").exists():
        (space / ".gitignore").write_text((tpl / "gitignore").read_text())
    else:
        kept.append(".gitignore")
    (space / ".contour" / "project").write_text(
        "# Contour model space (ADR 0015). This file is the marker: keep it tracked.\n"
        f"toolkit: {toolkit_commit()}\n"
        f"toolkit_path: {ROOT}\n"
        f"created: {time.strftime('%Y-%m-%d')}\n")
    lines = [f"ok   {space}"]
    failed = git.start(space)
    if failed:
        return {"ok": False, "lines": [f"FAIL git init: {failed}"]}
    failed = stub(space, ROOT)
    if failed:
        return {"ok": False, "lines": [f"FAIL {failed}"]}
    lines += ["ok   git init, pre-push stub installed (this space is never pushed)",
              f"ok   scaffolding copied from toolkit {toolkit_commit()}"]
    if kept:
        lines.append(f"kept {len(kept)} existing file(s) untouched: {', '.join(kept)}")
    lines += [
              "",
              "next: write spec.yaml (schema: %s)" % (ROOT / "schema" / "spec.schema.yaml"),
              "      put the user's reference images in refs/",
              "      write build.py, then run: contour check"]
    return {"ok": True, "lines": lines}


def scaffold(root):
    """Each scaffold file in `root` against the toolkit's template: `missing`,
    `drift` (present, but not what the template writes for this space's name),
    or `ok`. Asked by `doctor` of the space it stands in and by `spaces` of
    every space, so the two cannot disagree about which files have drifted."""
    return {rel: "missing" if not (root / rel).exists()
            else "ok" if (root / rel).read_text() == space.template(ROOT, rel, root.name)
            else "drift"
            for rel in SCAFFOLD}


def sees_rules(root):
    """Whether an agent working in `root` is given the hard rules (open
    question 13): a `CLAUDE.md` of its own, or the toolkit's above it, which
    Claude Code finds by walking up."""
    return ((root / "CLAUDE.md").is_file()
            or (ROOT in root.parents and (ROOT / "CLAUDE.md").is_file()))


def doctor():
    """Is this space still in step with the toolkit, and still unpushable."""
    lines, ok = [], True
    for rel, state in scaffold(PROJECT).items():
        if state == "missing":
            lines.append(f"MISS {rel} — run contour init in a fresh dir to see it")
            ok = False
        elif state == "drift":
            lines.append(f"DRIFT {rel} — differs from the toolkit's template")
            ok = False
        else:
            lines.append(f"ok   {rel}")
    marker = (PROJECT / MARKER).read_text()
    was = next((l.split(":", 1)[1].strip() for l in marker.splitlines()
                if l.startswith("toolkit:")), "unknown")
    now = toolkit_commit()
    lines.append(f"{'ok  ' if was == now else 'NOTE'} toolkit {was}"
                 + ("" if was == now else f" -> {now} since this space was created"))
    remotes = git.remotes(PROJECT)
    if remotes:
        lines.append(f"WARN this space has a remote ({', '.join(remotes)}); it is never pushed")
        ok = False
    hooks = git.hooks_dir(PROJECT)
    if hooks is None or not (hooks / "pre-push").exists():
        lines.append("WARN no pre-push stub — nothing stops a push from here")
        ok = False
    from lib import marks
    old = marks.old_spelling(marks.load(HERE.marks))
    if old:
        lines.append(f"NOTE {marks.phrase(len(old))} in the old spelling "
                     f"(the part named under the anchor) — run contour "
                     f"migrate-marks")
    if not shutil.which("contour"):
        lines.append("WARN `contour` is not on PATH: the spec guard in "
                     ".claude/settings.json cannot run,")
        lines.append(f"     so rule 1 is unenforced here. Fix, into any dir on PATH:")
        lines.append(f"       ln -s {ROOT / 'contour'} ~/.local/bin/contour")
        ok = False
    lines.append(f"     toolkit at {ROOT}")
    return {"ok": ok, "lines": lines}


def migrate_marks():
    """Rewrite this space's marks into one spelling: the part at the top level,
    the anchor holding the pin alone (slice 19).

    Asked for by name, and the only thing in the toolkit that rewrites the
    user's findings without them having just written one. `marks.json` is
    tracked across four spaces, so what it moved is printed rather than
    counted: a diff nobody can attribute is a diff nobody can review (rule 5).

    Never run on load, and not run by `doctor`, which only says how many there
    are. A space that is never migrated keeps working — the reader in
    `lib/marks.py` answers either spelling — so there is no moment at which
    this has to happen and no reason to make it happen quietly.
    """
    from lib import marks
    moved = marks.migrate(HERE.marks)
    if not moved:
        return {"ok": True, "lines": ["ok   nothing to migrate: every mark "
                                      "names its part at the top level"]}
    return {"ok": True, "lines": [f"ok   {marks.phrase(len(moved))} migrated: "
                                  f"{', '.join(moved)}",
                                  f"     review the diff in {HERE.marks.name} "
                                  f"before you commit it"]}


def run_hook(name, rest):
    """Run a guard out of tools/hooks/ (ADR 0015).

    A model space never copies these; its settings.json and its pre-push stub
    call this, so the guard is always the installed version and there is
    nothing to drift. exec, so stdin, stdout and the exit code pass straight
    through to whatever invoked the hook.
    """
    if name == "pre-push" and PROJECT:
        print("refused: a model space is never pushed (ADR 0011, ADR 0015).\n"
              "  to share a model: contour export, then hand over the .glb",
              file=sys.stderr)
        return 1
    script = {"spec": "guards/spec.py", "pre-push": "hooks/pre-push"}.get(name)
    if not script:
        print(f"contour hook: no guard named {name!r}", file=sys.stderr)
        return 2
    os.execv(str(ROOT / "tools" / script), [script, *rest])
    return 2                                          # unreachable; exec replaces us


def install_hooks():
    """Copy tools/hooks/* into this checkout's hooks dir (ADR 0011).

    Deliberately not core.hooksPath: that resolves inside the working tree, so
    checking out a variant branch that predates the hook would remove it from
    disk and the guard would silently cease to exist.
    """
    src = ROOT / "tools" / "hooks"
    hooks = [h for h in sorted(src.glob("*")) if h.is_file()]
    if not hooks:
        return {"ok": False, "lines": [f"FAIL no hooks in {src.relative_to(ROOT)}"]}
    dst = git.hooks_dir(ROOT)
    if dst is None:
        return {"ok": False, "lines": ["FAIL not a git checkout"]}
    dst.mkdir(parents=True, exist_ok=True)
    lines = []
    for h in hooks:
        t = dst / h.name
        t.write_bytes(h.read_bytes())
        t.chmod(0o755)
        lines.append(f"ok   {h.name}")
    override = git.hooks_override(ROOT)
    if override:
        lines.append(f"WARN core.hooksPath={override} overrides these; unset it")
    lines.append(f"installed {len(hooks)} hook(s) in {dst}")
    return {"ok": not override, "lines": lines}


def reading(root, now):
    """One space as `spaces` reports it, derived from the space on every call
    and never stored. The text form and the JSON form both print this, so they
    cannot disagree about which spaces exist or which are behind (slice 28)."""
    marker = (root / MARKER).read_text()
    was = next((l.split(":", 1)[1].strip() for l in marker.splitlines()
                if l.startswith("toolkit:")), None)
    found = scaffold(root)
    return {"name": root.name, "path": str(root),
            "toolkit": {"commit": was,
                        "state": "unknown" if was is None
                        else "current" if was == now else "behind"},
            "commits": git.commits(root), "remotes": git.remotes(root),
            "scaffold": {"drift": [r for r, s in found.items() if s == "drift"],
                         "missing": [r for r, s in found.items() if s == "missing"]},
            "rules": sees_rules(root),
            "presence": presence.live(root),
            "renamed": rename.uncommitted(root)}


def listing():
    """Every space and its health, as `contour spaces --json` prints it and the
    lobby serves it: one reading, so the two cannot disagree."""
    now = toolkit_commit()
    return {"roots": [str(r) for r in space.roots(ROOT)],
            "spaces": [reading(s, now) for s in space.spaces(space.roots(ROOT))],
            "deleted": restore.deleted()}


def spaces(name=None, as_json=False):
    """List the model spaces, or print one's path for `cd $(contour spaces x)`."""
    found = space.spaces(space.roots(ROOT))
    if as_json:
        said = listing()
        return {"ok": not any(s["remotes"] for s in said["spaces"]),
                "lines": [json.dumps(said, indent=2)]}
    if name:
        hits = [s for s in found if s.name == name]
        if len(hits) != 1:
            return {"ok": False, "lines": [f"FAIL {len(hits)} spaces named {name!r}"
                                           + (": " + ", ".join(str(h) for h in hits) if hits else "")]}
        return {"ok": True, "lines": [str(hits[0])]}
    if not found:
        return {"ok": True, "lines": [f"no model spaces under "
                                      f"{', '.join(str(r) for r in space.roots(ROOT))}",
                                      "(set $CONTOUR_SPACES to look elsewhere)"]
                + deleted_lines()}
    now, lines, ok = toolkit_commit(), [], True
    for s in (reading(s, now) for s in found):
        home = s["path"].replace(str(Path.home()), "~")
        tk = s["toolkit"]
        state = f"({tk['state']})"
        lines.append(f"  {s['name']:<12} {home:<34} toolkit {tk['commit'] or '?'} "
                     f"{state:<10} {s['commits']:>4} commits")
        for r in s["remotes"]:
            lines.append(f"  WARN {s['name']} has a remote ({r}) — a model space is never pushed")
            ok = False
    return {"ok": ok, "lines": lines + deleted_lines()}


def deleted_lines():
    """The trash, under the live list and apart from it (ADR 0021, decision 6)."""
    gone = restore.deleted()
    if not gone:
        return []
    return ["", "deleted (restore with contour restore <id> [--to <dir>]):"] + [
        f"  {d['name'] or '?':<12} deleted {d['deleted'] or '?'}  "
        + (f"restored, live at {d['live']}" if d["live"] else f"contour restore {d['id']}")
        for d in gone]


def unit_tests():
    """The toolkit's own tests: stdlib unittest, no Blender.

    They cover what runs outside Blender — the mark store, the canvas server,
    part identity as the canvas reads it, the launcher's own behaviour around a
    stubbed Blender. `$BLENDER` is withheld, so what needs the fixture's render
    skips here and runs in `fixture_tests` instead. Geometry is not testable
    this way and is not tested this way; that is what the fixture and the
    mutants are for (ADR 0009).
    """
    env = {k: v for k, v in os.environ.items() if k != "BLENDER"}
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                       cwd=str(ROOT), env=env, capture_output=True, text=True,
                       timeout=TIMEOUT_S)
    tail = (r.stderr or r.stdout).strip().splitlines()
    ran = next((l for l in tail if l.startswith("Ran ")), "ran ?")
    return {"ok": r.returncode == 0,
            "lines": [ran] if r.returncode == 0 else tail[-12:]}


def fixture_tests():
    """`tests/test_fixture.py`'s claims against the fixture's render — the
    mask, the views, anchoring and an agent's badge — run here so that one
    command still proves them (ADR 0009, issue 25). A skip is a failure: the
    point of running them here is that they cannot be left out.
    """
    import unittest
    os.environ["BLENDER"] = BLENDER          # before loading: the skip is decided there
    found = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_fixture.py")
    cases = unittest.TestSuite(t for s in found for c in s for t in c
                               if type(t).__name__ == "FixtureTest")
    result = unittest.TestResult()
    cases.run(result)
    wrong = [f"{getattr(t, '_testMethodName', t)}: {err.strip().splitlines()[-1]}"
             for t, err in result.failures + result.errors]
    wrong += [f"{getattr(t, '_testMethodName', t)}: skipped, {why}" for t, why in result.skipped]
    if wrong or not result.testsRun:
        return {"ok": False, "lines": wrong or ["no fixture tests ran"]}
    return {"ok": True, "lines": [f"{result.testsRun}/{result.testsRun} held against its render"]}


def stage_selftest():
    """Fixture through every stage, plus proof that verify can actually fail."""
    steps = [["build", "smoke", "--fixture"],
             ["render", "smoke", "--fixture"],
             ["export", "smoke", "--fixture"],
             ["roundtrip", "smoke", "--fixture"]]
    lines, ok, t0 = [], True, time.time()
    units = unit_tests()
    ok &= units["ok"]
    lines.append(f"{'ok  ' if units['ok'] else 'FAIL'} {'units':<10}"
                 + " | ".join(units["lines"]))
    if not units["ok"]:
        lines.insert(0, "selftest FAIL (%.1fs)" % (time.time() - t0))
        return {"ok": False, "lines": lines}
    for i, args in enumerate(steps):
        rep = stage(args, first=(i == 0))
        ok &= rep["ok"]
        shown = " | ".join(l.strip() for l in rep["lines"]) if rep["ok"] \
            else " | ".join(rep["lines"][:1] + rep["lines"][-3:])
        lines.append(f"{'ok  ' if rep['ok'] else 'FAIL'} {args[0]:<10}{shown}")
        if not rep["ok"]:
            break
    else:
        fx = fixture_tests()
        ok &= fx["ok"]
        lines.append(f"{'ok  ' if fx['ok'] else 'FAIL'} {'fixture':<10}"
                     + " | ".join(fx["lines"]))
    lines.insert(0, f"selftest {'PASS' if ok else 'FAIL'} ({time.time() - t0:.1f}s)")
    return {"ok": ok, "lines": lines}

