"""A JSON file, read or written the one way (slice 16).

Mechanics only: read a file or a default, write one back, say what the next id
is. Which files exist, what they are called and which letter their ids carry
stay with the modules that mean something by them — `m1` is a fact about marks
and `v1` a fact about vetoes, and a store that held the list of every file in a
space would be a second place for the layout to be wrong.

Blender-free, because `console/vetoes.py` imports it the way it imports
`lib/marks` and the console must never pull Blender into its own process.
"""
import json
import re
from pathlib import Path


def load(path, default):
    """What this file holds, or `default` when there is no file.

    The default is the caller's because callers disagree about absence: an
    append wants an empty list, the panel wants None, since *nothing has been
    drawn yet* is a state it shows and an empty sheet is not.
    """
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save(path, data):
    """Write it back, indented, with a newline at the end.

    Shaped to be read in a diff rather than by a parser, which is how
    `marks.json` and `vetoes.json` are already committed: a record arrives at
    the bottom and nothing above it moves, so `git diff` shows the line that
    was added instead of a reformatted file.
    """
    Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def next_id(records, prefix):
    """One past the highest number ever used under `prefix` — `m4`, `v1`.

    Not one past the count. Closed marks are pruned (0018-2), so the numbering
    has gaps, and a reused id would point at two different things. The prefix
    is the caller's because it is the only part of an id that means something:
    `m` is a mark and `v` is a veto, and the store has no opinion on either.
    """
    used = [int(m.group(1)) for m in
            (re.fullmatch(rf"{prefix}(\d+)", str(r.get("id", "")))
             for r in records) if m]
    return f"{prefix}{max(used, default=0) + 1}"
