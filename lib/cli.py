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

from lib import commands, connector, delete, git, presence, rename, restore, revision, space, survey, update     # stdlib-only by test (ADR 0019, 29)

ROOT = Path(__file__).resolve().parent.parent
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
TIMEOUT_S = 300
UNITS_TIMEOUT_S = 300
"""The unit suite's own limit, apart from one Blender run's. It was raised to
600s when the suite outgrew 300s (333s on master, 2026-10-09), and came back
once issue 95 took the suite to ~166s inside selftest (2026-10-10). A suite
that nears it again is slow tests to fix, not a limit to raise."""
UNITS_BUDGET_S = 200
"""Where selftest starts saying the suite is slow: about 1.2x its time when
issue 95 was done (~166s), so drift is a `warn` line while it is small, well
before `UNITS_TIMEOUT_S` stops the run."""
PER_TEST_S = 2.5
"""One test over this, not marked `@slow("why")` (tests/budget.py), is named in
selftest's report. The total says the suite got slow; this says which test."""


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
LOG = OUT / survey.LOG
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
                  f"{survey.held_by(record['took_over'])}, which is gone")
        return record
    except Exception as e:
        rec = getattr(e, "record", None)
        if rec is None:
            raise
        print(f"contour {command}: this space is held by {survey.held_by(rec)}.",
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
        panel.record(OUT / panel.NAME, rep, HERE.blend)
        return say_marks(emit(draw(rep)))
    if cmd != "export":
        return emit(stage([cmd]))
    from lib import exported
    rep = stage(["export"])
    if not rep["ok"]:
        exported.record(OUT / exported.NAME, rep, HERE.glb, HERE.blend)
        return emit(rep)
    rt = stage(["roundtrip"], first=False)
    # For the console's card, whichever door this came through (ADR 0025,
    # decision 5): a run's own export says so by the run it was made inside.
    exported.record(OUT / exported.NAME, rt, HERE.glb, HERE.blend,
                    run=os.environ.get("CONTOUR_RUN"))
    rt["lines"] = rep["lines"] + rt["lines"]
    return emit(rt)


def on_filmstrip(cmd, rest, held):
    """A clip as one picture, for a checkpoint (ADR 0023). Never drawn by a
    build: `contour check` renders the sheet for the page and nothing else, and
    this says where the picture is rather than putting it in the report."""
    rep = stage(["filmstrip", *[f"--clip={c}" for c in rest]])
    if rep["ok"]:
        from lib import filmstrip
        filmstrip.record(HERE.out, HERE.blend)
    return emit(rep)


def on_api(cmd, rest, held):
    return emit(stage(["api", *rest]))


def on_measure(cmd, rest, held):
    if rest[:1] == ["--standing"] and len(rest) == 2:
        # Whether a span's number may be proposed is read off `marks.json`
        # alone, so it is answered here and costs no Blender start.
        from lib import span
        return emit(span.standing(HERE.marks, rest[1]))
    return emit(stage(["measure", *rest]))


def on_worksheet(cmd, rest, held):
    """The spans, drawn onto the references (ADR 0022, decision 8). With none
    on file there is nothing to draw, which the marks alone can say: no
    Blender, and no file left from the last time there were some."""
    from lib import marks, worksheet
    if not worksheet.spans(marks.load(HERE.marks)):
        return emit({"ok": True, "lines": [
            "ok   worksheet  no spans on file: nothing to draw, nothing written"]})
    rep = stage(["worksheet"])
    if rep["ok"]:
        worksheet.record(HERE.dot, HERE.marks)
    return emit(rep)


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
                              verdict=HERE.dot / panel.NAME, name=PROJECT.name)
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
    words = [w for w in rest if w not in ("--json", "--new")]
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
    said = init(words[0], new="--new" in rest, to=to)
    if "--json" in rest:
        return emit({"ok": said["ok"], "lines": [json.dumps(
            {"path": said["path"],
             "refused": None if said["ok"] else said["lines"][0].removeprefix("FAIL ")},
            indent=2)]})
    return emit(said)


def on_doctor(cmd, rest, held):
    return emit(doctor())


def on_migrate_marks(cmd, rest, held):
    return emit(migrate_marks())


def on_mcp(cmd, rest, held):
    """The connector (ADR 0024): Desktop on the other end of stdin and stdout.
    It reads through the survey on its own; what is handed it here is the two
    acts, open and create, and nothing else that writes (issue 84).

    `--config` prints Desktop's block and writes nothing: that file is the
    user's, and lists servers that are not Contour's.
    """
    if rest == ["--config"]:
        found = shutil.which("contour")
        linked = found and Path(found).resolve() == (ROOT / "contour").resolve()
        link = Path(found) if linked else Path.home() / ".local" / "bin" / "contour"
        print(json.dumps(connector.config(link), indent=2))
        if not linked:
            print(f"no `contour` link on PATH; make the one this block names:\n"
                  f"    ln -s {ROOT / 'contour'} ~/.local/bin/", file=sys.stderr)
        return 0 if linked else 1
    if rest:
        print(usage(), file=sys.stderr)
        return 2
    connector.serve(sys.stdin, sys.stdout, {
        **connector.readings(),
        "open": lambda args: opened(args.get("page"), args.get("space"),
                                    create=bool(args.get("create")), name=args.get("name")),
        "create": lambda args: created(args.get("name"), args.get("references") or [])})
    return 0


def on_status(cmd, rest, held):
    """The connector's `status`, for a requester without MCP (ADR 0027,
    decision 8): one reading behind both, so they cannot disagree. Named, not
    stood in, because a requester stands outside the space it asked of."""
    if rest[1] != "--json":
        print(usage(), file=sys.stderr)
        return 2
    try:
        root = space.named(rest[0], ROOT)
    except LookupError as e:
        return emit({"ok": False, "lines": [f"FAIL {e}"]})
    print(json.dumps(survey.status(root), indent=2))
    return 0


def on_spaces(cmd, rest, held):
    if rest == ["--json"]:
        return emit(spaces(as_json=True))
    return emit(spaces(rest[0] if rest else None))


def on_lobby(cmd, rest, held):
    from lib import lobby
    if rest and rest[0] != "--create":
        print(usage(), file=sys.stderr)
        return 2
    return emit(lobby.serve(
        survey.listing, grace=seconds("CONTOUR_LOBBY_GRACE", lobby.GRACE_S),
        hidden_grace=seconds("CONTOUR_LOBBY_HIDDEN_GRACE", lobby.HIDDEN_GRACE_S),
        create=(rest[1] if len(rest) > 1 else "") if rest else None))


CONFIRMING = {
    "rename": (lambda w, o: rename.propose(PROJECT, w, ROOT),
               lambda w, o: rename.perform(PROJECT, w, ROOT), rename.lines),
    "delete": (lambda w, o: delete.propose(PROJECT, w),
               lambda w, o: delete.perform(PROJECT, w), delete.lines),
    "update": (lambda w, o: update.propose(PROJECT, ROOT),
               lambda w, o: update.perform(PROJECT, ROOT), update.lines),
    "purge": (lambda w, o: restore.proposed_purge(w),
              lambda w, o: restore.purge(w), restore.purge_lines),
    "restore": (None, lambda w, o: restore.restore(w, ROOT, o.get("--to")), restore.lines),
}
"""What each command that confirms asks of its own module: the proposal, the
act, and the lines a terminal reads. Everything else is `on_confirming`'s."""


def on_confirming(cmd, rest, held):
    """Every command that confirms, as its row's `confirms` says (issue 85).

    The first word, if the row takes one, is the name or id verbatim: what a
    page sends is whatever was typed, and a typed `--yes` must be a wrong name
    and not a confirm. Then `--yes`, `--json`, and the flags the row takes.
    Without `--yes` it proposes and writes nothing (ADR 0021, decision 5; ADR
    0026, second amendment). The commands that write take their own hold:
    `rename`'s lock moves with the directory and `delete`'s goes with it, so
    the table's `holds` is False and `main` takes none.
    """
    shape = next(c for c in commands.TABLE if c.name == cmd).confirms
    words = list(rest)
    word = words.pop(0) if shape.word else None
    flags, given = set(), {}
    while words:
        w = words.pop(0)
        if w in ("--yes", "--json"):
            flags.add(w)
        elif w in shape.takes and words:
            given[w] = words.pop(0)
        else:
            print(usage(), file=sys.stderr)
            return 2
    propose, act, lines = CONFIRMING[cmd]
    done = "--yes" in flags or not shape.proposes
    said = (act if done else propose)(word, given)
    if "--json" in flags:
        return emit({"ok": not said["refused"], "lines": [json.dumps(said, indent=2)]})
    if said["refused"]:
        return emit({"ok": False, "lines": [f"FAIL {cmd}  {said['refused']}"]})
    return emit({"ok": True, "lines": lines(said, done)})


def seconds(name, fallback):
    """A timeout from the environment, so a test proving what a silence means
    does not have to wait out the real one."""
    return float(os.environ.get(name) or fallback)


def on_intents(cmd, rest, held):
    from lib import intent
    print("\n".join(intent.categories()))
    return 0


def on_asks(cmd, rest, held):
    """The resolved policy, or with `--always <c>` / `--undo <c>` this space's
    entry rewritten (ADR 0025, decision 6). The page is the writer's one client
    (ADR 0021, decision 3); the console refuses the agent's call to it, since an
    agent widening its own permissions is what the ask-list exists to prevent."""
    from lib import policy
    acts = {"--always": policy.always, "--undo": policy.undo}
    act = next((w for w in rest if w in acts), None)
    named = [w for w in rest if w not in (*acts, "--json")]
    if act is None and not named:
        try:
            print("\n".join(policy.report(PROJECT)))
        except policy.PolicyError as e:
            return emit({"ok": False, "lines": [f"FAIL {e}"]})
        return 0
    if act is None or len(named) != 1:
        print(usage(), file=sys.stderr)
        return 2
    try:
        said = {"refused": None, "allowed": list(acts[act](PROJECT, named[0]))}
    except policy.PolicyError as e:
        said = {"refused": str(e), "allowed": None}
    if "--json" in rest:
        return emit({"ok": not said["refused"], "lines": [json.dumps(said, indent=2)]})
    if said["refused"]:
        return emit({"ok": False, "lines": [f"FAIL asks  {said['refused']}"]})
    return emit({"ok": True, "lines": policy.report(PROJECT)})


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


def init(name, new=False, to=None):
    """Create a model space (ADR 0015): its own directory, its own git repo.

    Copies only what the agent must read from the working directory. The
    guards are never copied — settings.json and the pre-push stub call the
    installed toolkit, so there is one implementation and nothing to drift.

    An existing directory is adopted, never clobbered, unless `new` says the
    space must be made from nothing — what the lobby asks, since a name typed
    into a form that matches somebody's folder is no reason to make that
    folder a repository. `to` is the directory the space goes in, made if it
    is not there yet; here, if not given. Every refusal comes before anything
    is written.
    """
    base = Path(to).expanduser() if to else Path.cwd()
    refused = init_refusal(name, new, base)
    if refused:
        return {"ok": False, "path": None, "lines": [f"FAIL {refused}"]}
    space = (base / name).resolve()
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
        f"toolkit: {survey.toolkit_commit()}\n"
        f"toolkit_path: {ROOT}\n"
        f"created: {time.strftime('%Y-%m-%d')}\n")
    lines = [f"ok   {space}"]
    failed = git.start(space)
    if failed:
        return {"ok": False, "path": str(space), "lines": [f"FAIL git init: {failed}"]}
    failed = stub(space, ROOT)
    if failed:
        return {"ok": False, "path": str(space), "lines": [f"FAIL {failed}"]}
    lines += ["ok   git init, pre-push stub installed (this space is never pushed)",
              f"ok   scaffolding copied from toolkit {survey.toolkit_commit()}"]
    if kept:
        lines.append(f"kept {len(kept)} existing file(s) untouched: {', '.join(kept)}")
    lines += [
              "",
              "next: write spec.yaml (schema: %s)" % (ROOT / "schema" / "spec.schema.yaml"),
              "      put the user's reference images in refs/",
              "      write build.py, then run: contour check"]
    return {"ok": True, "path": str(space), "lines": lines}


def init_refusal(name, new, base):
    """Why `contour init <name>` may not make a space in `base`, or None."""
    illegal = space.illegal(name)
    if illegal:
        return illegal
    where = base / name
    if (where / MARKER).exists():
        return f"{where.resolve()} is already a model space"
    if any(s.name == name for s in space.spaces(space.roots(ROOT))):
        return (f"a live space is already called {name}; a space's name is its "
                f"identity, so pick another")
    if new and (where.exists() or where.is_symlink()):
        return f"{where.resolve()} already exists; pick another name"
    return None


def doctor():
    """Is this space still in step with the toolkit, and still unpushable."""
    lines, ok, mend = [], True, False
    for rel, state in update.standing(PROJECT, ROOT).items():
        if state == "missing":
            lines.append(f"MISS {rel} — run contour update to write it")
            ok, mend = False, True
        elif state == "behind":
            lines.append(f"BEHIND {rel} — the toolkit has moved on")
            ok, mend = False, True
        elif state == "edited":
            # The user's own rules, and not something the space needs: an
            # update leaves it, so it is no reason to send anybody there.
            lines.append(f"EDITED {rel} — yours; update leaves it")
        else:
            lines.append(f"ok   {rel}")
    was, now = update.recorded(PROJECT) or "unknown", survey.toolkit_commit()
    lines.append(f"{'ok  ' if was == now else 'NOTE'} toolkit {was}"
                 + ("" if was == now else f" -> {now} since this space was created"))
    if mend:
        lines.append("     run contour update: it replaces what nobody edited, "
                     "and names what it leaves")
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


def opened(page, called, create=False, name=None):
    """Start the page where the user acts, and say only whether it started
    (ADR 0024, decision 5). Never its URL: that carries the secret behind
    every gate, and a chat is no place for it.

    The lobby can be opened on its create form, with `name` filled in: where a
    picture pasted into the chat is dropped (ADR 0025, decision 11)."""
    from lib import enter
    if page == "lobby":
        asked = ("--create", *([name] if name else ())) if create else ()
        enter.page(Path.home(), "lobby", *asked)    # every space's page stands in none
        return {"page": page, "space": None, "refused": None}
    if page not in ("console", "canvas"):
        raise LookupError(f"no page {page!r}: console, lobby or canvas")
    root = connector.named(called)
    here = presence.live(root)
    if page == "console":
        refused = enter.into(root, here)
    elif any(p["kind"] == "console" for p in here):
        # The connector's own: a second page would be a second writer to
        # `marks.json`, and the console's page can mark already.
        refused = "already open in a console; its page can mark"
    else:
        enter.page(root, "canvas")
        refused = None
    return {"page": page, "space": root.name, "refused": refused}


def created(name, paths):
    """The lobby's create, where the lobby would make it, plus references
    already on disk (ADR 0024, decision 10). Every path is read before
    anything is made, so a bad one leaves no half a space."""
    from lib import lobby
    read = []
    for p in map(Path, paths):
        try:
            data = p.read_bytes()
        except OSError as e:
            return refused_create(f"{p} cannot be read: {e.strerror}")
        why = lobby.unfit(p.name, data, read, called=p)
        if why:
            return refused_create(why)
        read.append((p.name, data))
    return lobby.made(str(name or ""), lobby.location(space.roots(ROOT)), pictures=read)


def refused_create(why):
    return {"path": None, "next": None, "refused": why}


def spaces(name=None, as_json=False):
    """List the model spaces, or print one's path for `cd $(contour spaces x)`.
    Both lists print the survey's rows, so they cannot disagree (slice 28)."""
    if name:
        try:
            return {"ok": True, "lines": [str(space.named(name, ROOT))]}
        except LookupError as e:
            return {"ok": False, "lines": [f"FAIL {e}"]}
    said = survey.listing()
    if as_json:
        return {"ok": not any(s["remotes"] for s in said["spaces"]),
                "lines": [json.dumps(said, indent=2)]}
    if not said["spaces"]:
        return {"ok": True, "lines": [f"no model spaces under {', '.join(said['roots'])}",
                                      "(set $CONTOUR_SPACES to look elsewhere)"]
                + deleted_lines(said["deleted"])}
    lines, ok = [], True
    for s in said["spaces"]:
        home = s["path"].replace(str(Path.home()), "~")
        tk = s["toolkit"]
        state = f"({tk['state']})"
        lines.append(f"  {s['name']:<12} {home:<34} toolkit {tk['commit'] or '?'} "
                     f"{state:<10} {s['commits']:>4} commits")
        for r in s["remotes"]:
            lines.append(f"  WARN {s['name']} has a remote ({r}) — a model space is never pushed")
            ok = False
    return {"ok": ok, "lines": lines + deleted_lines(said["deleted"])}


def deleted_lines(gone):
    """The trash, under the live list and apart from it (ADR 0021, decision 6)."""
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
    try:
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests",
                            "--durations", "0"],
                           cwd=str(ROOT), env=env, capture_output=True, text=True,
                           timeout=UNITS_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"ok": False, "lines": [f"the unit tests ran past {UNITS_TIMEOUT_S}s "
                                       f"and were stopped"]}
    tail = (r.stderr or r.stdout).strip().splitlines()
    ran = next((l for l in tail if l.startswith("Ran ")), "ran ?")
    return {"ok": r.returncode == 0,
            "lines": [ran] if r.returncode == 0 else tail[-12:],
            "warn": budget_warnings(r.stderr, ROOT / "tests")}


def budget_warnings(output, tests_dir):
    """What a unit run's own report says about its time: the total against
    `UNITS_BUDGET_S`, and each test over `PER_TEST_S` that no `@slow` excuses.
    `output` is unittest's, run with `--durations 0`. Read, never imported:
    importing a test module would take the suite's lock (tests/one_run.py)."""
    import ast
    warned = []
    total = re.search(r"^Ran \d+ tests? in ([\d.]+)s", output, re.M)
    if total and float(total.group(1)) > UNITS_BUDGET_S:
        warned.append(f"the unit tests took {float(total.group(1)):.0f}s, over their "
                      f"{UNITS_BUDGET_S}s budget; --durations names the slowest (issue 95)")
    marked = {}

    def excused(test_id):
        module, cls, method = (test_id.split(".") + ["", ""])[:3]
        if module not in marked:
            try:
                tree = ast.parse((Path(tests_dir) / f"{module}.py").read_text())
            except (OSError, SyntaxError):
                tree = None
            marked[module] = set() if tree is None else {
                (c.name, f.name) for c in tree.body if isinstance(c, ast.ClassDef)
                for f in c.body if isinstance(f, ast.FunctionDef)
                and any(isinstance(d, ast.Call) and getattr(d.func, "id", None) == "slow"
                        for d in f.decorator_list)}
        return (cls, method) in marked[module]

    over = [(float(s), test_id) for s, test_id in
            re.findall(r"^([\d.]+)s\s+\S+ \(([\w.]+)\)\s*$", output, re.M)
            if float(s) > PER_TEST_S and not excused(test_id)]
    if over:
        named = ", ".join(f"{test_id} {s:.1f}s" for s, test_id in sorted(over, reverse=True)[:3])
        more = f" and {len(over) - 3} more" if len(over) > 3 else ""
        warned.append(f"{len(over)} over {PER_TEST_S}s without @slow: {named}{more}")
    return warned


def fixture_tests():
    """`tests/test_fixture.py`'s claims against the fixture's render — the
    mask, the views, anchoring, an agent's badge and the filmstrip — run here so that one
    command still proves them (ADR 0009, issue 25). A skip is a failure: the
    point of running them here is that they cannot be left out.
    """
    import unittest
    os.environ["BLENDER"] = BLENDER          # before loading: the skip is decided there
    found = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_fixture.py")
    cases = unittest.TestSuite(t for s in found for c in s for t in c
                               if type(t).__name__ in ("FixtureTest", "FilmstripTest"))
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
    lines += [f"warn {'units':<10}{line}" for line in units.get("warn", [])]
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

