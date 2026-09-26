"""`contour-console`, once an interpreter has been found for it.

The page is the canvas's page and the server is the canvas's server: the console
adds a lifetime and, in later slices, the run it drives. Serving its own copy of
either would put *what a mark is* in two places that drift silently, both still
parsing the old shape.
"""
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

from lib import canvas as canvas_lib
from lib import marks as marks_store


def phrase(secs):
    """A duration as the last line should read it. Minutes, unless the caller
    shortened the clock for a test, where `0 minutes` would be a lie."""
    return f"{secs / 60:.0f} minutes" if secs >= 60 else f"{secs:.0f} seconds"


GRACE_S = 10          # beats are seconds apart; this is several missed ones
IDLE_S = 60 * 60      # the tab left open on Friday, ended before Monday


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
        self.canvas = canvas_lib.Canvas(
            sheet=self.space / "sheet.png",
            marks=self.space / marks_store.NAME,
            mask=out / "mask.png", parts=out / "parts.json")

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
            if time.monotonic() - self.canvas.last_touch > self.idle:
                self.ended = f"idle for {phrase(self.idle)}"
                return self.canvas.finish()
            time.sleep(0.25)

    def stop(self):
        self.canvas.stop()

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
        console.wait()
    except KeyboardInterrupt:
        console.stop()                        # the port, before anything else
        print("console closed — interrupted", flush=True)
        return 130
    print(f"console closed — {console.ended or 'the page said done'}", flush=True)
    return 0


if __name__ == "__main__":
    # The shim resolved the space and passed it in: the console never walks up
    # on its own, because it was launched from the toolkit's directory.
    sys.exit(main(sys.argv[1:], os.environ["CONTOUR_PROJECT"]))
