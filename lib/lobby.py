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
import json
import subprocess
import sys
import webbrowser
from pathlib import Path

from lib import enter, refs, space
from lib.page import Blob, Page

PAGE = Path(__file__).resolve().parent / "lobby.html"
CONTOUR = PAGE.parent.parent / "contour"
GRACE_S = 10          # beats are seconds apart; this is several missed ones
HIDDEN_GRACE_S = 60 * 60   # a background tab's timers may stop; a quit browser
                           # is caught here, and a lingering lobby costs a port

REFERENCE_CAP = 20 * 2**20
"""How large one dropped reference may be: a photo, not a video."""

CAN = ("create", "rename", "delete", "restore", "purge")
"""What the lobby can do beyond listing, for the page to ask about. Each action
arrives as a capability with the command that performs it, and a button
for one the host cannot perform is a button that fails
(ADR 0021, decision 2). `enter` and `reveal` are added by `granted`, where
they can be."""


def granted():
    """What this host can do: everything in `CAN`; `enter` only where the
    console's environment exists (ADR 0021, decision 2); and `reveal`, open in
    Finder, only where there is a Finder."""
    return (CAN + (() if enter.environment() else ("enter",))
            + (("reveal",) if sys.platform == "darwin" else ()))


class Lobby(Page):
    """One lobby session. `listing` is called on every request for the list,
    because the list is derived and never stored."""

    max_body = 128 * 2**20       # several references, base64 inside the JSON

    def __init__(self, listing, can=None, grace=GRACE_S, hidden_grace=HIDDEN_GRACE_S):
        super().__init__(PAGE, can=granted() if can is None else can, grace=grace,
                         hidden_grace=hidden_grace)
        self.listing = listing

    def served(self):
        return {("GET", "/spaces"): lambda q: self.listing(),
                ("POST", "/create"): self.create,
                ("GET", "/location"): lambda q: {"default": str(self.location())},
                ("POST", "/rename"): self.rename,
                ("POST", "/delete"): self.delete,
                ("POST", "/restore"): self.restore,
                ("POST", "/purge"): self.purge,
                ("GET", "/environment"): lambda q: {"console": enter.environment()},
                ("POST", "/enter"): self.enter,
                ("POST", "/reveal"): self.reveal,
                ("GET", "/picture"): self.picture}

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

    def rename(self, asked):
        """`contour rename` in the space the page named, its answer as it
        gave it: the rules are the command's, and so is every refusal.

        A confirm carries the proposal the page showed, and is the confirm of
        that proposal only (rule 1): asked again, the command must say the
        same, or nothing is done and the page has a new one to show.

        A path the listing does not hold is no space of the page's: None, which
        the server answers as not found."""
        if asked.get("path") not in {s["path"] for s in self.listing()["spaces"]}:
            return None
        now = contour(asked["path"], "rename", asked["name"], "--json")
        if "shown" not in asked or now["refused"]:
            return now
        if asked["shown"] != now:
            return dict(now, refused="the proposal changed since it was shown; "
                                     "read this one, then confirm it")
        return contour(asked["path"], "rename", asked["name"], "--yes", "--json")

    def delete(self, asked):
        """`contour delete` in the space the page named, its answer as it gave
        it. Asked with no name, the proposal, for the space the listing names;
        asked with the name the user typed, the delete — and the command, not
        this, judges whether what was typed is the space's name.

        A path the listing does not hold is None: not found."""
        listed = {s["path"]: s["name"] for s in self.listing()["spaces"]}
        if asked.get("path") not in listed:
            return None
        if "name" not in asked:
            return contour(asked["path"], "delete", listed[asked["path"]], "--json")
        return contour(asked["path"], "delete", str(asked["name"]), "--yes", "--json")

    def restore(self, asked):
        """`contour restore` of a bundle the listing holds, its answer as it
        gave it. Run from the toolkit, since there is no space to stand in
        until it has been restored. An id the listing does not hold is None:
        not found."""
        if asked.get("id") not in {d["id"] for d in self.listing()["deleted"]}:
            return None
        to = ["--to", str(asked["to"])] if asked.get("to") else []
        return contour(CONTOUR.parent, "restore", asked["id"], *to, "--json")

    def purge(self, asked):
        """`contour purge` of a bundle the listing holds. Asked with no typed
        id, the proposal; with one, the removal — but only of the bundle the
        page showed. The command takes any id it is given, so a typed id that
        names some other bundle is refused here, before it can remove that one.
        An id the listing does not hold is None: not found."""
        if asked.get("id") not in {d["id"] for d in self.listing()["deleted"]}:
            return None
        now = contour(CONTOUR.parent, "purge", asked["id"], "--json")
        if "typed" not in asked or now["refused"]:
            return now
        if asked["typed"] != asked["id"]:
            return dict(now, refused=f"to remove this bundle, type {asked['id']}")
        return contour(CONTOUR.parent, "purge", asked["id"], "--yes", "--json")

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


def serve(listing, grace=GRACE_S, hidden_grace=HIDDEN_GRACE_S, open_browser=True):
    """One lobby session, start to last line. Blocks until the tab closes."""
    lobby = Lobby(listing, grace=grace, hidden_grace=hidden_grace)
    url = lobby.start()
    print(f"lobby at {url}", flush=True)
    try:
        if open_browser:          # inside: a Ctrl-C can land while a browser opens
            webbrowser.open(url)
        lobby.wait()
    except KeyboardInterrupt:
        lobby.stop()
        return {"ok": True, "lines": ["lobby closed — interrupted"]}
    return {"ok": True, "lines": [f"lobby closed — {lobby.ended or 'the page said done'}"]}
