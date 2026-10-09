"""Stand-in executables the OS checks once per run, not once per test (issue 95).

macOS assesses a new executable the first time it runs: about 0.25 s, against
0.008 s after. A stub written in `setUp` is new every test, so the suite paid
that hundreds of times for scripts that differ only in where they write. Here
each distinct body is written once, and a test gets a symlink to it at the path
it asked for. A link to a file already checked runs at full speed.

A body therefore names no path of its own test. It finds that test's files
beside its `$0`, which is the link: `"$(dirname "$0")/opened"`.
"""
import hashlib
import tempfile
from pathlib import Path

_STORE = None


def executable(at, body):
    """An executable at `at` that runs `body`. Returns `at`."""
    global _STORE
    if _STORE is None:
        _STORE = Path(tempfile.mkdtemp(prefix="contour-stubs-"))
    kept = _STORE / hashlib.sha256(body.encode()).hexdigest()[:16]
    if not kept.exists():
        kept.write_text(body)
        kept.chmod(0o755)
    at = Path(at)
    at.unlink(missing_ok=True)
    at.symlink_to(kept)
    return at
