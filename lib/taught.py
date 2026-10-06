"""The shown terms, each taught in one line (ADR 0025, decision 1; issue 77).

*Reference*, *sheet*, *mark*, *span* and *spec* keep their exact words on the
page, because the agent says them too, and each carries the line
`docs/CONTEXT.md` gives it under *On the page* where a page first shows it.

Which lines the viewer has closed is kept on this computer, in `~/.contour`,
and not in the browser: every page is served on a port of its own, so the
browser's storage would forget a closed line the next time any page opened,
and the lobby would never hear what the canvas was told. The record is a
convenience — unreadable, it is empty, and every line is shown.
"""
import json

from lib import policy

LINES = {
    "reference": "A picture you give of what you want. Claude measures it and never changes it.",
    "sheet": "Claude's picture of what it built: four views, on a grid of one-metre squares.",
    "mark": "A note pinned to one spot on a picture: click the spot, then type one line.",
    "span": "A distance on a reference, end to end: drag across it, and Claude measures it.",
    "spec": "What the model has to be, written as numbers. A build matches it or it doesn't.",
}
"""{term: its line}, in `docs/CONTEXT.md`'s words."""

RECORD = "taught.json"


def closed():
    """The terms whose lines the viewer has closed, in the order closed. An
    unreadable record, or a term no page teaches, is not one."""
    try:
        said = json.loads((policy.home() / RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [t for t in said if t in LINES] if isinstance(said, list) else []


def close(term):
    """Note that the viewer closed `term`'s line; the record as it now is."""
    now = closed()
    if term in LINES and term not in now:
        now.append(term)
        policy.home().mkdir(parents=True, exist_ok=True)
        (policy.home() / RECORD).write_text(json.dumps(now), encoding="utf-8")
    return now
