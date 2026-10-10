"""A system notification, posted by the console itself (ADR 0027, decision 7).

When a run nobody was watching parks, reaching the person must not depend on
the requester relaying anything. The console says so on this machine, in plain
words, naming the space and the act. **It holds no link**: the URL carries the
secret behind every gate, and a notification is read on a lock screen.

Standard library only, as the console's half of anything in `lib/` is.
"""
import os
import subprocess
import sys
import threading


def command(text):
    """What posts `text`, or None where nothing can. `$CONTOUR_NOTIFIER`
    replaces it, given the text as its one argument, the way `$BLENDER`
    replaces the interpreter: a test proves what is said without a banner on
    the screen of whoever runs the suite."""
    told = os.environ.get("CONTOUR_NOTIFIER")
    if told:
        return [told, text]
    if sys.platform == "darwin":
        # The text as an AppleScript string: quoted, its own quotes escaped.
        quoted = '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
        return ["osascript", "-e", f'display notification {quoted} with title "Contour"']
    return None


def post(text):
    """Post `text` and return without waiting: the gate that parked must not
    wait on a notification centre. A machine that cannot post loses the
    banner, not the gate, which still waits on the page."""
    argv = command(text)
    if argv is None:
        return
    try:
        posting = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        return
    # Reaped off to the side, so a finished one is not left a zombie.
    threading.Thread(target=posting.wait, daemon=True).start()
