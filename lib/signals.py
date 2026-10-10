"""A signal as something a wait can be interrupted by (issue 27).

Two processes have to stop well: `contour-console`, which forwards what it was
sent and waits, and `console/server.py`, which closes a port and gives a space
back. What they share is the one step neither can do without and both used to
do only for `SIGINT` — turning a signal into something that comes out of the
wait it stopped, carrying which signal it was.

The interpreter already does this for `SIGINT` and calls it `KeyboardInterrupt`.
`SIGTERM` is what anything that is not a person sends, and `SIGHUP` is what a
closed terminal sends; neither was handled, so the default disposition killed
the process where it stood and neither resource was given back.

Blender-free, because both callers are: the shim is stdlib-only by design, and
the server must not need Blender to shut down.
"""
import signal


class Arrived(Exception):
    """A signal that arrived, named and numbered.

    An exception rather than a flag so it lands where `KeyboardInterrupt`
    already lands, and the code that ends a console is one piece of code with
    one thing that varies: which signal it was.
    """

    def __init__(self, number):
        super().__init__(name(number))
        self.number = number


STOPPING = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
"""The three ways a console is told to stop, and the only three handled.

`SIGKILL` is not here and cannot be: nothing runs after it, which is why it is
the case forwarding cannot reach and why the server watches its parent instead.
"""


ENDING_RUN = signal.SIGUSR1
"""What `contour stop` sends a console: end the run, keep the console
(ADR 0027, decision 9). Not one of `STOPPING`, which end the console itself —
a page open on the space stays open after its run is stopped."""


SHOWING = signal.SIGUSR2
"""What the lobby's enter and the connector's `open console` send a console
running unattended: open your own page in this machine's browser (ADR 0027,
decision 7). A signal because it carries nothing — the URL holds the secret
behind every gate, and it goes from console to browser and nowhere else."""


def raising(*numbers):
    """Have these signals raise `Arrived` in the main thread from now on."""
    def arrived(number, frame):
        raise Arrived(number)
    for number in numbers:
        signal.signal(number, arrived)


def number(which, fallback=signal.SIGINT):
    """Which signal an interruption was.

    `KeyboardInterrupt` does not say, because there is only one signal it can
    be; `Arrived` does. So a caller catching both asks here and is not made to
    care which of the two it caught.
    """
    return getattr(which, "number", fallback)


def name(number):
    """`SIGTERM`, for a line a person reads to find out what stopped this."""
    try:
        return signal.Signals(number).name
    except ValueError:
        return f"signal {number}"
