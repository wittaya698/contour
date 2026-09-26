"""`contour-console`, once an interpreter has been found for it.

The page is the canvas's page and the server is the canvas's server: what the
console adds is a lifetime and the run it drives, served as extra routes beside
the shared ones rather than as a second server. Serving its own copy of either
would put *what a mark is* in two places that drift silently, both still parsing
the old shape.
"""
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

from console import run as run_lib
from lib import canvas as canvas_lib
from lib import marks as marks_store


def phrase(secs):
    """A duration as the last line should read it. Minutes, unless the caller
    shortened the clock for a test, where `0 minutes` would be a lie."""
    return f"{secs / 60:.0f} minutes" if secs >= 60 else f"{secs:.0f} seconds"


GRACE_S = 10          # beats are seconds apart; this is several missed ones
IDLE_S = 60 * 60      # the tab left open on Friday, ended before Monday

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

    def __init__(self, space, grace=GRACE_S, idle=IDLE_S):
        self.space = Path(space)
        self.grace = grace
        self.idle = idle
        self.ended = None                     # why it ended, for the last line
        out = self.space / "out"
        self.run = run_lib.Run(self.space)
        self.canvas = canvas_lib.Canvas(
            sheet=self.space / "sheet.png",
            marks=self.space / marks_store.NAME,
            mask=out / "mask.png", parts=out / "parts.json", can=CAN,
            routes={("POST", "/run"): self.started,
                    ("GET", "/events"): self.transcript,
                    ("POST", "/verdict"): self.verdict,
                    ("POST", "/end"): self.ending})

    def started(self, body):
        """`POST /run`: prose in. The one way a run begins, and the reason
        `drive` is a capability and not a second page."""
        if self.run.live:
            return {"started": False, "why": "a run is already under way"}
        self.run.start(body.get("prompt", ""))
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
        not among them."""
        return self.run.answer(body.get("id"), body.get("allow"),
                               body.get("reason"))

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
            beat = self.canvas.last_beat
            if beat is not None and time.monotonic() - beat > self.grace:
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
    sheet = Path(space) / "sheet.png"
    if not sheet.exists():
        print(f"contour-console: no sheet at {sheet}.\n"
              f"  Run contour render in this space first.", file=sys.stderr)
        return 1
    console = Console(space, grace=seconds("CONTOUR_CONSOLE_GRACE", GRACE_S),
                      idle=seconds("CONTOUR_CONSOLE_IDLE", IDLE_S))
    url = console.start()
    print(f"console at {url}", flush=True)
    if "--no-browser" not in argv:
        webbrowser.open(url)
    try:
        try:
            console.wait()
        except KeyboardInterrupt:
            print("console closed — interrupted", flush=True)
            return 130
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
