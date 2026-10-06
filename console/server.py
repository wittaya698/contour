"""`contour-console`, once an interpreter has been found for it.

The page is the canvas's page and the server is the canvas's server: what the
console adds is a lifetime and the run it drives, served as extra routes beside
the shared ones rather than as a second server. Serving its own copy of either
would put *what a mark is* in two places that drift silently, both still parsing
the old shape.
"""
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

from console import run as run_lib
from console import vetoes as veto_store
from console import launcher
from lib import canvas as canvas_lib
from lib import exported
from lib import gate as gate_words
from lib import panel as panel_state
from lib import policy, presence, signals
from lib import space as space_lib


def phrase(secs):
    """A duration as the last line should read it. Minutes, unless the caller
    shortened the clock for a test, where `0 minutes` would be a lie."""
    return f"{secs / 60:.0f} minutes" if secs >= 60 else f"{secs:.0f} seconds"


GRACE_S = 10          # beats are seconds apart; this is several missed ones
IDLE_S = 60 * 60      # the tab left open on Friday, ended before Monday
HIDDEN_GRACE_S = IDLE_S   # a background tab's timers may stop; no longer than
                          # an idle console already lives (issue 39)

TOOLKIT = Path(__file__).resolve().parent.parent

NEW_SPACE = (
        "A new model, just made: nothing is in it yet. Start it the way the "
        "toolkit's new-space skill says "
        f"({TOOLKIT}/.claude/skills/new-space/SKILL.md); it is already named and "
        "made, so skip that step.\n"
        "1. Before writing anything, ask the user, in plain words: What is it? "
        "How big is it in real life? Where will it be seen? What parts must it "
        "have? One real measurement is enough when there are pictures; never "
        "guess one.\n"
        "2. Any reference pictures the user gave are already in refs/. Measure "
        "them; never change them.\n"
        "3. Propose the tolerances and the triangle budget yourself, from what "
        "it is and where it will be seen, and say they are yours.\n"
        "4. Draft spec.yaml, and flag every number you chose rather than the "
        "user, tolerances first. Ask the user before writing it (rule 1).")


def variation(of):
    """The new-space flow, for a space made as a variation of `of`: its spec and
    its build named for reference, and neither copied (ADR 0021, decision 4). A
    copied spec would arrive already agreed to, and this one is confirmed as its
    own."""
    source = space_lib.layout(of)
    return (
        f"This space is a variation of {source.name}, at {source.root}. Read its "
        f"{source.spec} and {source.build} for reference only: copy neither, and "
        "never write in that space. This space's spec.yaml is its own contract, "
        "drafted and confirmed here like any new one.\n" + NEW_SPACE)


BEGIN = {"new-space": lambda of: NEW_SPACE, "variation": variation}
"""The runs a console can be begun on, by name (ADR 0021, decision 4). A name
and never a prompt's text: the launch line is the one way into a console that
is not its own page, so it carries the choice of a flow the toolkit wrote, and
nothing anybody could put words in. A variation's `--of` is a path, and only a
model space's: the prompt is still the toolkit's words about it. The prompt is
the run's first line in the transcript like any other."""


def begun(argv):
    """The first prompt `argv` asks for, or None; and why it cannot be had."""
    def value(flag):
        at = argv.index(flag) + 1 if flag in argv else None
        return argv[at] if at is not None and at < len(argv) else None
    if "--begin" not in argv:
        return None, None
    flow = value("--begin")
    if flow not in BEGIN:
        return None, f"--begin takes one of: {', '.join(BEGIN)}"
    of = value("--of")
    if flow == "variation" and not (of and (Path(of) / space_lib.MARKER).is_file()):
        return None, "--begin variation takes --of <the model space it varies>"
    return BEGIN[flow](of), None

CAN = canvas_lib.MARKS_ONLY + ("drive",)
"""What the page may offer when the console is the one serving it.

The launcher's answer plus the run, and built from `MARKS_ONLY` rather than
spelled out, so marking cannot come to mean one thing here and another there.
`drive` is the console's whole difference: it owns the build, so it is the only
host that can be asked to start or end one (ADR 0019).
"""


class Console:
    """One console session over one model space.

    The lifetime is the console's own and not the canvas's: the page beats, the
    server records the beat, and this decides what a silence means.
    """

    def __init__(self, space, grace=GRACE_S, idle=IDLE_S, hidden_grace=HIDDEN_GRACE_S):
        self.space = Path(space)
        self.grace = grace
        self.hidden_grace = hidden_grace
        self.idle = idle
        self.ended = None                     # why it ended, for the last line
        # Who launched this. The shim cannot forward a SIGKILL — nothing runs
        # after one — so the server watches the single fact that says it
        # happened, which is that its parent is gone. Read once at the start,
        # because after the parent dies the question has no answer left: the
        # process is reparented to init and `getppid` says 1 forever (issue 27).
        self.launched_by = os.getppid()
        # Where this space keeps its files, asked of the space. The console
        # used to restate ADR 0015 here — which build the sheet is of, where a
        # mark goes — and a restatement is a copy that can go out of step
        # (slice 17).
        here = space_lib.layout(self.space)
        self.dot, self.blend = here.dot, here.blend
        self.run = run_lib.Run(self.space)
        self.canvas = canvas_lib.Canvas(
            sheet=here.sheet, marks=here.marks,
            mask=here.mask, parts=here.parts, refs=here.refs, can=CAN,
            # `views.json` beside the build says which build the cameras drew,
            # so the panel can be labelled rather than quietly authoritative
            # (ADR 0019, decision 13).
            views=here.views, blend=here.blend,
            verdict=here.dot / panel_state.NAME, name=self.space.resolve().name,
            routes={("POST", "/run"): self.started,
                    ("GET", "/events"): self.transcript,
                    ("POST", "/verdict"): self.verdict,
                    ("GET", "/vetoes"): self.vetoes,
                    ("POST", "/promote"): self.promoted,
                    ("GET", "/asks"): self.asks,
                    ("POST", "/undo"): self.undone,
                    ("GET", "/export"): self.export_card,
                    ("POST", "/export"): self.exporting,
                    ("GET", "/export.glb"): self.handed,
                    ("POST", "/reveal"): self.revealed,
                    ("POST", "/end"): self.ending})

    def started(self, body):
        """`POST /run`: prose in. The one way a run begins, and the reason
        `drive` is a capability and not a second page."""
        if self.run.live:
            return {"started": False, "why": "a run is already under way"}
        self.run.start(body.get("prompt", ""), body.get("marks") or ())
        return {"started": True}

    def transcript(self, query):
        """`GET /events?since=n`: the transcript from a cursor.

        Polled rather than streamed: slice 01's four authentication mechanisms
        apply to a request unchanged, there is no long-lived response to unwind
        when Ctrl-C arrives, and a reloaded tab gets the whole run back instead
        of whatever happened after it reconnected.
        """
        return self.run.since(int(query.get("since") or 0))

    def ending(self, body):
        """`POST /end`: end the run, keep the console. The page's other ending,
        `/done`, closes the console itself — the canvas has one of those and the
        console has both, because it has something to end that outlives one
        agent session."""
        return self.run.end()

    def verdict(self, body):
        """`POST /verdict`: allow, or deny with a reason. Nothing else is read
        off the body — a gate has two answers and a sentence, and the call is
        not among them. *Always* is an allow that also writes this space's
        ask-list entry (ADR 0025, decision 6)."""
        return self.run.answer(body.get("id"), body.get("allow"),
                               body.get("reason"), always=bool(body.get("always")))

    def vetoes(self, query):
        """`GET /vetoes`: every veto in this space, as the page says it. A
        console route, because a veto has one writer and the page that shows it
        is the page that made it."""
        return veto_store.shown(self.space)

    def promoted(self, body):
        """`POST /promote`: a veto about a part becomes a sheet mark.

        A console route and not a canvas one, for the same reason the veto store
        lives above `lib/`: the canvas serves a page under a host with no run and
        no gates, so it has no vetoes to promote and must not learn about them.
        """
        return veto_store.promote(self.space, body.get("id"), body.get("part"))

    def asks(self, query):
        """`GET /asks`: what runs without asking for this model, each in words.
        Read by importing `lib/`; written only by the launcher, below."""
        try:
            return {"unwatched": gate_words.unwatched(self.space)}
        except policy.PolicyError as e:      # an ask-list nobody can read
            return {"unwatched": [], "refused": str(e)}

    def undone(self, body):
        """`POST /undo`: ask about this category again in this space. By the
        command that writes the list, of which the page is the one client
        (ADR 0021, decision 3); answered with the list as it now stands."""
        launcher.run(self.space, "asks", "--undo", str(body.get("category")), "--json")
        return self.asks({})

    def export_card(self, query):
        """`GET /export`: whether the button may export, and the last export's
        card, or None before one."""
        return {"offered": exported.offer(self.dot / panel_state.NAME, self.run.live),
                "card": exported.card(self.dot / exported.NAME, self.blend)}

    def exporting(self, body):
        """`POST /export`: the button. `contour export` spawned as the console
        spawns everything, with no agent turn (ADR 0025, decision 5); answered
        with the card it leaves, and what the launcher said when it failed."""
        offered = exported.offer(self.dot / panel_state.NAME, self.run.live)
        if not offered["can"]:
            return {"exported": False, "said": [offered["why"]], **self.export_card({})}
        ok, said = launcher.run(self.space, "export")
        return {"exported": ok, "said": [] if ok else said, **self.export_card({})}

    def handed(self, query):
        """`GET /export.glb`: the file itself, byte for byte, for Download."""
        glb = exported.file(self.dot / exported.NAME)
        return canvas_lib.Blob((glb.read_bytes(), "model/gltf-binary")) if glb else None

    def revealed(self, body):
        """`POST /reveal`: Show in Finder. `$CONTOUR_REVEAL` stands in for
        Finder the way `$BLENDER` stands in for Blender; off a Mac, the folder
        is opened instead, since there is no file manager to select it in."""
        glb = exported.file(self.dot / exported.NAME)
        if glb is None:
            return {"revealed": False}
        if os.environ.get("CONTOUR_REVEAL"):
            argv = [os.environ["CONTOUR_REVEAL"], str(glb)]
        elif sys.platform == "darwin":
            argv = ["open", "-R", str(glb)]
        else:
            argv = ["xdg-open", str(glb.parent)]
        done = subprocess.run(argv, capture_output=True, timeout=10)
        return {"revealed": done.returncode == 0}

    def start(self):
        url = self.canvas.start()
        threading.Thread(target=self.watch, daemon=True).start()
        return url

    def watch(self):
        """End the run when the page stops beating.

        Only after a first beat: before one, nothing has opened the page yet,
        and ending then would make a slow browser look like a closed tab.
        """
        while not self.canvas.done:
            if self.launched_by > 1 and os.getppid() != self.launched_by:
                # Before the gate suppression below, and deliberately: a console
                # parked at a gate is exactly the one holding the space, so a
                # check that a gate could postpone would miss the case that
                # costs something. Not a new way for a console to decide to
                # die — it is the page closing, seen from the other end.
                self.ended = "the console that launched it is gone"
                return self.canvas.finish()
            # A hidden tab's silence never ends a console at a gate: that
            # would decide the gate by silence, which ADR 0019 rules out. A
            # tab that closed — said so, or went quiet while on screen — still
            # does; it is the page closing, as above (issue 39).
            at_gate = self.run.pending is not None and self.canvas.hidden
            if self.canvas.closed(self.grace, None if at_gate else self.hidden_grace):
                self.ended = "the page closed"
                return self.canvas.finish()
            # A pending gate suppresses the idle clock. The console never
            # answers a gate on the user's behalf in either direction, and a
            # timeout that ended the run at an unanswered one would be answering
            # it — quietly making the lifetime rule into the timeout policy
            # ADR 0019 rejects. The suppression lasts exactly as long as the
            # gate: answering it is a request, and a request is a touch.
            if self.run.pending is not None:
                time.sleep(0.25)
                continue
            if time.monotonic() - self.canvas.last_touch > self.idle:
                self.ended = f"idle for {phrase(self.idle)}"
                return self.canvas.finish()
            time.sleep(0.25)

    def stop(self):
        self.canvas.stop()
        self.run.stop()

    def wait(self):
        self.canvas.wait()


def seconds(name, fallback):
    """A timeout from the environment, the way `$BLENDER` names an interpreter:
    one hatch, named after the thing it replaces, so a test proving what a
    silence means does not have to wait out the real one."""
    return float(os.environ.get(name) or fallback)


def main(argv, space):
    # No sheet is not a refusal here, unlike `contour canvas`. That command
    # exists to mark a sheet and has nothing to show without one; this one
    # exists to make one, and refusing would mean the surface that can produce a
    # first build cannot be opened until something else has. The panel says which
    # build it is showing, and none is an answer (ADR 0019, decision 13).
    begin, refused = begun(argv)
    if refused:
        print(refused, file=sys.stderr)
        return 2
    console = Console(space, grace=seconds("CONTOUR_CONSOLE_GRACE", GRACE_S),
                      idle=seconds("CONTOUR_CONSOLE_IDLE", IDLE_S),
                      hidden_grace=seconds("CONTOUR_CONSOLE_HIDDEN_GRACE", HIDDEN_GRACE_S))
    # All three, and not only the SIGINT the interpreter raises for: a console
    # is stopped by a closed terminal and by anything tidying up as often as by
    # a person, and the port, the hold and the presence below are given back
    # only on a path out of `wait` (issue 27).
    signals.raising(*signals.STOPPING)
    # Before the URL is printed, so nothing can have opened the page while the
    # space still looked unattended (issue 30).
    with presence.present(space, "console"):
        return serving(console, argv, begin)


def serving(console, argv, begin=None):
    url = console.start()
    if begin:
        console.run.start(begin)
    print(f"console at {url}", flush=True)
    try:
        try:
            # Inside: a browser can take seconds to answer, and a Ctrl-C in
            # them is the same Ctrl-C (issue 36 found it in the lobby first).
            if "--no-browser" not in argv:
                webbrowser.open(url)
            console.wait()
        except (KeyboardInterrupt, signals.Arrived) as which:
            number = signals.number(which)
            print(f"console closed — interrupted by {signals.name(number)}",
                  flush=True)
            return 128 + number
        print(f"console closed — {console.ended or 'the page said done'}",
              flush=True)
        return 0
    finally:
        # The port and the space, on every path out. Two resources that outlive a
        # process that drops them: a port still answering makes the next console
        # look like a port conflict, and a hold still held wedges the space.
        console.stop()


if __name__ == "__main__":
    # The shim resolved the space and passed it in: the console never walks up
    # on its own, because it was launched from the toolkit's directory.
    sys.exit(main(sys.argv[1:], os.environ["CONTOUR_PROJECT"]))
