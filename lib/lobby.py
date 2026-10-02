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

from lib.page import Page

PAGE = Path(__file__).resolve().parent / "lobby.html"
CONTOUR = PAGE.parent.parent / "contour"
GRACE_S = 10          # beats are seconds apart; this is several missed ones

CAN = ("rename",)
"""What the lobby can do beyond listing, for the page to ask about. Each action
arrives as a capability with the command that performs it — delete, create and
enter are still to come — and a button for one the host cannot perform is a
button that fails (ADR 0021, decision 2)."""


class Lobby(Page):
    """One lobby session. `listing` is called on every request for the list,
    because the list is derived and never stored."""

    def __init__(self, listing, can=CAN, grace=GRACE_S):
        super().__init__(PAGE, can=can, grace=grace)
        self.listing = listing

    def served(self):
        return {("GET", "/spaces"): lambda q: self.listing(),
                ("POST", "/rename"): self.rename}

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


def contour(space, *args):
    """A `contour` command run in `space`, and the JSON it printed."""
    r = subprocess.run([sys.executable, str(CONTOUR), *args], cwd=space,
                       capture_output=True, text=True, timeout=120)
    return json.loads(r.stdout)


def serve(listing, grace=GRACE_S, open_browser=True):
    """One lobby session, start to last line. Blocks until the tab closes."""
    lobby = Lobby(listing, grace=grace)
    url = lobby.start()
    print(f"lobby at {url}", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        lobby.wait()
    except KeyboardInterrupt:
        lobby.stop()
        return {"ok": True, "lines": ["lobby closed — interrupted"]}
    return {"ok": True, "lines": [f"lobby closed — {lobby.ended or 'the page said done'}"]}
