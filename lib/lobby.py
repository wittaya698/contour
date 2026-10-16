"""`contour lobby`: every space on this machine, on one page (ADR 0021).

A `Page`, so it stands behind issue 01's protections exactly as the canvas and
the console do, and has nothing of its own but what it shows. What it shows is
asked of the command line: `listing` is the reading `contour spaces --json`
prints, handed in by the launcher, so the page and the command cannot disagree
about which spaces exist (ADR 0021, decision 3).

Its lifetime is the tab. There is no Done button: a list has nothing to finish,
so a page that stopped beating is the only ending there is.
"""
import base64
import contextlib
import functools
import json
import os
import signal
import socket
import subprocess
import sys
import urllib.parse
import webbrowser
from pathlib import Path

from lib import commands, enter, lock, policy, refs, space
from lib.page import Blob, Page

PAGE = Path(__file__).resolve().parent / "lobby.html"
CONTOUR = PAGE.parent.parent / "contour"
GRACE_S = 10          # beats are seconds apart; this is several missed ones
HIDDEN_GRACE_S = 60 * 60   # a background tab's timers may stop; a quit browser
                           # is caught here, and a lingering lobby costs a port
RELOAD_S = 5          # a reload says going, then beats again within this

RECORD = "lobby.json"
"""The running lobby, said in `~/.contour`: its pid and where it listens, and
never its address with the secret in it. One lobby lists every space, so a
second is a second tab of the same list (ADR 0025, decision 12)."""
SHOW = signal.SIGUSR1
"""What a second `contour lobby` sends the running one: show yourself."""
SHOWN = "lobby-show.json"
"""Where, on the page, a second `contour lobby` asked to be shown: a signal
carries no words, so they are left beside the record before it is sent."""


def fragment(create):
    """The part of the lobby's address its page reads and its server never
    sees: `#create`, and the name to fill in, when it is opened on its create
    form. None is the list as it is."""
    if create is None:
        return ""
    return "#create" + (f"={urllib.parse.quote(create)}" if create else "")

REFERENCE_CAP = 20 * 2**20
"""How large one dropped reference may be: a photo, not a video."""

CAN = ("create", "rename", "update", "delete", "restore", "purge")
"""What the lobby can do beyond listing, for the page to ask about. Each action
arrives as a capability with the command that performs it, and a button
for one the host cannot perform is a button that fails
(ADR 0021, decision 2). `enter` and `reveal` are added by `granted`, where
they can be."""


ASKS = {
    "rename": ("space", lambda asked, it: asked["name"], "shown"),
    "update": ("space", None, "shown"),
    "delete": ("space", lambda asked, it: it["name"], "name"),
    "restore": ("trash", lambda asked, it: it["id"], None),
    "purge": ("trash", lambda asked, it: it["id"], "typed"),
}
"""What the page sends each command that confirms: where it runs, the word it
proposes with, and what its confirm carries. `shown` is the proposal the page
showed, which must be what the command says now. `name` is the name the user
typed, which the command judges against the space's own. `typed` is an id the
user typed, which must be the bundle the page showed: the command removes any
bundle it is given. `restore` proposes nothing and acts on its id."""


def granted():
    """What this host can do: everything in `CAN`; `enter`, and `label`, only
    where the console's environment exists (ADR 0021, decision 2; ADR 0030,
    decision 7); and `reveal`, open in Finder, only where there is a Finder."""
    return (CAN + (() if enter.environment() else ("enter", "label"))
            + (("reveal",) if sys.platform == "darwin" else ()))


class Lobby(Page):
    """One lobby session. `listing` is called on every request for the list,
    because the list is derived and never stored."""

    max_body = 128 * 2**20       # several references, base64 inside the JSON

    def __init__(self, listing, can=None, grace=GRACE_S, hidden_grace=HIDDEN_GRACE_S,
                 reload_grace=RELOAD_S):
        super().__init__(PAGE, can=granted() if can is None else can, grace=grace,
                         hidden_grace=hidden_grace, reload_grace=reload_grace)
        self.listing = listing
        self.labelling = None        # the act, while it proposes

    def served(self):
        return {("GET", "/spaces"): lambda q: self.listing(),
                ("POST", "/create"): self.create,
                ("GET", "/location"): lambda q: {"default": str(self.location())},
                **{("POST", f"/{c.name}"): functools.partial(self.confirming, c.name)
                   for c in commands.TABLE if c.confirms},
                ("GET", "/environment"): lambda q: {"console": enter.environment()},
                ("POST", "/enter"): self.enter,
                ("POST", "/reveal"): self.reveal,
                ("GET", "/picture"): self.picture,
                ("POST", "/label"): self.label,
                ("GET", "/labels"): self.labels,
                ("POST", "/labelled"): self.labelled}

    def label(self, asked):
        """Start the labelling act: topics proposed for every space with none,
        together (ADR 0030, decision 7). Under the console's interpreter, since
        an approval and the agent are the console's; answered with which spaces
        it proposes for and why the others are skipped, while it goes on."""
        if "label" not in self.can:
            return {"refused": f"no console environment; make one, from {enter.ROOT}: "
                               f"{enter.environment()}"}
        if self.labelling is not None and self.labelling.poll() is None:
            return {"refused": "it is already proposing; answer what it proposes"}
        self.labelling = subprocess.Popen(
            labelling("label"), cwd=str(CONTOUR.parent), env=labelling_env(),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True,
            start_new_session=True)
        # Its plan is the one line it prints; nothing else is read from it.
        with self.labelling.stdout:
            line = self.labelling.stdout.readline()
        return dict(json.loads(line), refused=None) if line else \
            {"refused": "the act ended before it said what it proposes for"}

    def labels(self, asked):
        """Every topic proposal waiting next in a space, and whether the act is
        still proposing."""
        said = subprocess.run(labelling("shown"), cwd=str(CONTOUR.parent),
                              env=labelling_env(), capture_output=True, text=True,
                              timeout=60)
        return {"labelling": self.labelling is not None and self.labelling.poll() is None,
                "proposals": json.loads(said.stdout or "[]")}

    def labelled(self, asked):
        """One space's proposal answered: the words ticked are kept, the rest
        struck. None for a space or proposal that is not waiting."""
        said = subprocess.run(labelling("answer"), cwd=str(CONTOUR.parent),
                              env=labelling_env(), capture_output=True, text=True,
                              timeout=60, input=json.dumps(
                                  {"path": asked.get("path"), "id": asked.get("id"),
                                   "words": list(asked.get("words") or [])}))
        return json.loads(said.stdout or "null")

    def location(self):
        return location(self.listing()["roots"])

    def picture(self, asked):
        """A row's picture: the space's last sheet, or its first reference
        before there is one (ADR 0025, decision 10). Read, never drawn or
        resized, and only for a space the listing holds. Anything else, or a
        space with neither, is None: not found."""
        listed = {s["path"]: s["picture"] for s in self.listing()["spaces"]}
        if not listed.get(asked.get("path")):
            return None
        here = space.layout(asked["path"])
        if listed[asked["path"]] == "sheet" and here.sheet.is_file():
            return Blob((here.sheet.read_bytes(), "image/png"))
        named = refs.listing(here.refs)
        return Blob(refs.blob(here.refs, named[0])) if named else None

    def create(self, asked):
        """`contour init` in the location the page named, its answer as it gave
        it, then the new space's console on the new-space flow (ADR 0021,
        decision 4). The lobby drafts nothing: the drafting is the console's,
        under its gates. With no console environment the space is still made,
        and `next` says how to go on from a terminal."""
        location = Path(str(asked.get("location") or "")).expanduser()
        roots = [Path(r) for r in self.listing()["roots"]]
        if not location.is_absolute() or not any(
                location.resolve().is_relative_to(r.resolve()) for r in roots):
            return {"path": None, "next": None,
                    "refused": f"this lobby looks in {' and '.join(map(str, roots))}, "
                               f"and {location} is not inside it, so the new space would "
                               f"not be listed; make it there, or set $CONTOUR_SPACES "
                               f"to look elsewhere"}
        # A variation's source is a space of the page's, as a rename's path is:
        # the first prompt is about it, so it has to be one (issue 38).
        of = asked.get("of")
        if of and of not in {s["path"] for s in self.listing()["spaces"]}:
            return {"path": None, "next": None,
                    "refused": f"{of} is not a space this lobby lists, so there is "
                               f"nothing to make a variation of"}
        pictures, refused = dropped(asked.get("references") or [])
        if refused:
            return {"path": None, "next": None, "refused": refused}
        return made(str(asked.get("name") or ""), location, of=of, pictures=pictures)

    def confirming(self, cmd, asked):
        """A command that confirms, run as its row in the table says, its answer
        as it gave it: the rules are the command's, and so is every refusal
        (issue 85). What is this page's is which word it sends and what it
        confirms with (`ASKS`).

        A confirm is the confirm of what the page showed only (rule 1): asked
        again, the command must say the same, or nothing is done and the page
        has a new proposal to show. A space or a bundle the listing does not
        hold is no space of the page's: None, which the server answers as not
        found. Spaces are run in; the trash is run from the toolkit, since
        there is no space to stand in until a bundle has been restored."""
        shape = next(c for c in commands.TABLE if c.name == cmd).confirms
        where, word, confirm = ASKS[cmd]
        if where == "space":
            listed, key = {s["path"]: s for s in self.listing()["spaces"]}, asked.get("path")
        else:
            listed, key = {d["id"]: d for d in self.listing()["deleted"]}, asked.get("id")
        if key not in listed:
            return None
        stand = key if where == "space" else CONTOUR.parent
        to = ["--to", str(asked["to"])] if "--to" in shape.takes and asked.get("to") else []
        words = [word(asked, listed[key])] if word else []

        def run(*said, yes=False):
            return contour(stand, cmd, *said, *to, *(["--yes"] if yes else []), "--json")
        if not shape.proposes:
            return run(*words)
        if confirm == "name":
            # The name the user typed, and the command judges it.
            return run(str(asked["name"]), yes=True) if "name" in asked else run(*words)
        now = run(*words)
        if confirm not in asked or now["refused"]:
            return now
        if confirm == "shown" and asked["shown"] != now:
            return dict(now, refused="the proposal changed since it was shown; "
                                     "read this one, then confirm it")
        if confirm == "typed" and asked["typed"] != key:
            return dict(now, refused=f"to remove this bundle, type {key}")
        return run(*words, yes=True)

    def enter(self, asked):
        """Start a console on a space the listing holds, refused as
        `enter.into` refuses. Nothing is passed to it but where to stand. A
        path the listing does not hold is None: not found."""
        listed = {s["path"]: s for s in self.listing()["spaces"]}
        if asked.get("path") not in listed:
            return None
        return {"path": asked["path"],
                "refused": enter.into(asked["path"], listed[asked["path"]]["presence"])}

    def reveal(self, asked):
        """Open a space the listing holds in Finder. A path the listing does
        not hold is None: not found."""
        if asked.get("path") not in {s["path"] for s in self.listing()["spaces"]}:
            return None
        if "reveal" not in self.can:
            return {"path": asked["path"], "refused": "no Finder on this machine to open it in"}
        return {"path": asked["path"], "refused": enter.reveal(asked["path"])}


def labelling(*argv):
    """The labelling act's command line, under the console's interpreter."""
    return [str(enter.interpreter()), "-m", "console.labelling", *argv]


def labelling_env():
    return dict(os.environ, PYTHONPATH=str(CONTOUR.parent), PYTHONDONTWRITEBYTECODE="1")


def location(roots):
    """Where to make a space: the toolkit's `project/`, which this repo ignores
    and the push guard blocks (ADR 0021, decision 4), when `roots` take it in;
    otherwise the first of them."""
    roots = [Path(r) for r in roots]
    project = CONTOUR.parent / "project"
    if any(project.resolve().is_relative_to(r.resolve()) for r in roots):
        return project
    return roots[0]


def image(name, data):
    """Whether `data`, called `name`, is a reference the canvas can show: its
    first bytes say it is a PNG, a JPEG or a WebP, and its name says the same,
    since the name is what the canvas serves it as."""
    head = bytes(data[:12])
    said = ("image/png" if head.startswith(b"\x89PNG\r\n\x1a\n") else
            "image/jpeg" if head.startswith(b"\xff\xd8\xff") else
            "image/webp" if head[:4] == b"RIFF" and head[8:12] == b"WEBP" else None)
    return said is not None and refs.KINDS.get(Path(name).suffix.lower()) == said


def unfit(name, data, pictures, called=None):
    """Why `data`, called `name`, cannot join `pictures` in a new space's refs/,
    or None if it can. `called` is what the refusal names it, where that is
    more than its filename."""
    if not image(name, data):
        return (f"{called or name} is not a reference: a .png, .jpg or .webp "
                f"image whose name and bytes agree")
    if name in {n for n, _ in pictures}:
        return (f"two references are called {name}, and one would overwrite "
                f"the other in refs/")
    return None


def dropped(references):
    """The files dropped on create, as `(filename, bytes)` pairs, and why they
    are refused, if they are: all of them are checked before anything is made,
    so a bad drop never leaves half a space (ADR 0024, decision 11)."""
    pictures = []
    for r in references:
        name = str(r.get("name") or "")
        if Path(name).name != name or "\\" in name or name.startswith("."):
            return [], f"{name} is not a file's name, so it has no place in refs/"
        try:
            data = base64.b64decode(str(r.get("data") or ""), validate=True)
        except ValueError:
            return [], f"{name} did not arrive whole; drop it again"
        if len(data) > REFERENCE_CAP:
            return [], (f"{name} is over the {REFERENCE_CAP // 2**20} MB a reference "
                        f"may be")
        why = unfit(name, data, pictures)
        if why:
            return [], why
        pictures.append((name, data))
    return pictures, None


def made(name, location, of=None, pictures=()):
    """`contour init --new` in `location`, its answer as it gave it; then
    `pictures`, `(filename, bytes)` pairs checked before this was called, written
    into the new space's `refs/` as they came; then its console on the
    new-space flow, or the variation flow `of` a space. The lobby and the
    connector both make a space here, so neither drafts anything (ADR 0024,
    decision 10). With no console environment the space is still made, and
    `next` says how to go on from a terminal."""
    flow = "variation" if of else "new-space"
    said = contour(CONTOUR.parent, "init", name, "--to", str(location), "--new", "--json")
    if said["refused"]:
        return dict(said, next=None)
    for filename, data in pictures:
        # Not rule 1's write: nothing in a space this new is tracked yet, and a
        # reference is guarded from when git first tracks it (ADR 0024, decision 10).
        (Path(said["path"]) / "refs" / filename).write_bytes(data)
    missing = enter.environment()
    if missing:
        return dict(said, next=f"no console environment to open it in; make one, "
                               f"from {enter.ROOT}: {missing}, then: cd {said['path']} "
                               f"&& {enter.CONSOLE} --begin {flow}"
                               + (f" --of {of}" if of else ""))
    enter.console(said["path"], begin=flow, of=of)
    return dict(said, next=None)


def contour(space, *args):
    """A `contour` command run in `space`, and the JSON it printed."""
    r = subprocess.run([sys.executable, str(CONTOUR), *args], cwd=space,
                       capture_output=True, text=True, timeout=120)
    return json.loads(r.stdout)


def running():
    """The running lobby's record, or None. Alive by the hold's rule, on this
    machine, and listening where it said — so a pid since reused by something
    else is never sent a signal meant for a lobby."""
    try:
        record = json.loads((policy.home() / RECORD).read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(record, dict) or record.get("host") != socket.gethostname():
        return None
    if not lock.alive(record):
        return None
    where = urllib.parse.urlparse(str(record.get("origin")))
    try:
        socket.create_connection((where.hostname, where.port), timeout=1).close()
    except (OSError, TypeError, ValueError):
        return None
    return record


@contextlib.contextmanager
def recorded(lobby):
    """Say this lobby is the running one for as long as the block lasts, and
    show it again whenever a second `contour lobby`, or a page's *Models*,
    asks. Taken back only if it is still this one's."""
    signal.signal(SHOW, lambda number, frame: webbrowser.open(lobby.url + asked_to_show()))
    record = {"pid": os.getpid(), "host": socket.gethostname(), "origin": lobby.origin}
    path = policy.home() / RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record))
    try:
        yield
    finally:
        with contextlib.suppress(OSError, ValueError):
            if json.loads(path.read_text()) == record:
                path.unlink()


def asked_to_show():
    """The fragment a second `contour lobby` left, taken so it is used once."""
    path = policy.home() / SHOWN
    try:
        said = json.loads(path.read_text())
        path.unlink()
    except (OSError, ValueError):
        return ""
    return said if isinstance(said, str) and said.startswith("#") else ""


def serve(listing, grace=GRACE_S, hidden_grace=HIDDEN_GRACE_S, open_browser=True,
          create=None, reload_grace=RELOAD_S):
    """One lobby session, start to last line. Blocks until the tab closes.

    Or, when a lobby is already running, shows that one and starts nothing: its
    address is its own to open, since it carries its secret. `create`, a name or
    "", opens either on the create form, with that name filled in."""
    there = running()
    if there:
        (policy.home() / SHOWN).write_text(json.dumps(fragment(create)))
        os.kill(there["pid"], SHOW)
        return {"ok": True, "lines": ["lobby already open — shown again"]}
    lobby = Lobby(listing, grace=grace, hidden_grace=hidden_grace,
                  reload_grace=reload_grace)
    url = lobby.start()
    print(f"lobby at {url}", flush=True)
    try:
        with recorded(lobby):
            if open_browser:      # inside: a Ctrl-C can land while a browser opens
                webbrowser.open(url + fragment(create))
            lobby.wait()
    except KeyboardInterrupt:
        lobby.stop()
        return {"ok": True, "lines": ["lobby closed — interrupted"]}
    return {"ok": True, "lines": [f"lobby closed — {lobby.ended or 'the page said done'}"]}
