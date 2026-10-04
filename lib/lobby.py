"""`contour lobby`: every space on this machine, on one page (ADR 0021).

A `Page`, so it stands behind issue 01's protections exactly as the canvas and
the console do, and has nothing of its own but what it shows. What it shows is
asked of the command line: `listing` is the reading `contour spaces --json`
prints, handed in by the launcher, so the page and the command cannot disagree
about which spaces exist (ADR 0021, decision 3).

Its lifetime is the tab. There is no Done button: a list has nothing to finish,
so a page that stopped beating is the only ending there is.
"""
import json
import subprocess
import sys
import webbrowser
from pathlib import Path

from lib import enter
from lib.page import Page

PAGE = Path(__file__).resolve().parent / "lobby.html"
CONTOUR = PAGE.parent.parent / "contour"
GRACE_S = 10          # beats are seconds apart; this is several missed ones
HIDDEN_GRACE_S = 60 * 60   # a background tab's timers may stop; a quit browser
                           # is caught here, and a lingering lobby costs a port

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
                ("POST", "/reveal"): self.reveal}

    def location(self):
        """Where the page offers to make a space: the toolkit's `project/`,
        which this repo ignores and the push guard blocks (ADR 0021, decision
        4), when this lobby looks there; otherwise the first place it looks."""
        roots = [Path(r) for r in self.listing()["roots"]]
        project = CONTOUR.parent / "project"
        if any(project.resolve().is_relative_to(r.resolve()) for r in roots):
            return project
        return roots[0]

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
        flow = "variation" if of else "new-space"
        said = contour(CONTOUR.parent, "init", str(asked.get("name") or ""), "--to", str(location),
                       "--new", "--json")
        if said["refused"]:
            return dict(said, next=None)
        missing = enter.environment()
        if missing:
            return dict(said, next=f"no console environment to open it in; make one, "
                                   f"from {enter.ROOT}: {missing}, then: cd {said['path']} "
                                   f"&& {enter.CONSOLE} --begin {flow}"
                                   + (f" --of {of}" if of else ""))
        enter.console(said["path"], begin=flow, of=of)
        return dict(said, next=None)

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
