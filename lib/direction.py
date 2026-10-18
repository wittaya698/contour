"""A direction: lines along edges parallel in the object (ADR 0032, decision 2).

Where a direction's lines meet is how the camera saw it; `lib/camera.py` reads
spans through them. The agent proposes a direction as it does a span: it names
the edges, and picks each line's ends from what measurement found (ADR 0022,
decision 2). Along one row or one column of the picture, every place the
colour changes sharply is a **crossing**, numbered from the top or the left; a
line is two crossings picked, `col:0.45#2` being the second crossing down the
column 45% of the way across.

Edges by colour, not by a background mask: a photograph's background is a
deck or a table, not flat paper, and a face of the object can be as bright as
the next one in a different hue.

The arithmetic is here, out of Blender: a strip of colours in, crossings out.
Reading the picture is `cmd_measure`'s.
"""
import math

from . import marks

SHARP = 0.15
"""How far apart two neighbouring pixels' colours must be, as a distance in
RGB from 0 to 1, for the change between them to be a crossing. A flat face's
noise and a shadow's soft roll are well under it; a face against the next one
is well over."""


def pick(said, size):
    """`col:0.45#2` into `("col", 179, 2)`: which strip, at which pixel, and
    which crossing along it, counting from 1. None when it is not one."""
    try:
        where, n = said.split("#")
        kind, at = where.split(":")
        n, at = int(n), float(at)
    except ValueError:
        return None
    if kind not in ("row", "col") or not 0 <= at <= 1 or n < 1:
        return None
    across = size[0] if kind == "col" else size[1]
    return kind, int(round(at * (across - 1))), n


def crossings(colours):
    """Where along a strip its colour changes sharply: positions in pixels,
    to a fraction of one, from its start.

    The change between pixel `i` and `i + 1` sits at `i + 0.5`. One spread
    over two or three pixels, as antialiasing spreads it, is placed at its
    peak, by a parabola through the three changes around it.
    """
    steps = [math.dist(a[:3], b[:3]) for a, b in zip(colours, colours[1:])]
    found = []
    for i, s in enumerate(steps):
        before = steps[i - 1] if i else 0.0
        after = steps[i + 1] if i + 1 < len(steps) else 0.0
        if s < SHARP or s < before or s <= after:
            continue
        bend = before - 2 * s + after
        found.append(i + 0.5 + (0.5 * (before - after) / bend if bend else 0.0))
    return found


def place(strip, size, said):
    """Where one picked crossing is: `{"ok", "at"}`, or `{"ok": False, "why"}`
    naming the crossings that strip has."""
    got = pick(said, size)
    if got is None:
        return {"ok": False, "why": (
            f"{said} is not a crossing: say row:F#N or col:F#N, F from 0 to 1 "
            f"across the picture, N counting crossings from the top or the left")}
    kind, at, n = got
    found = crossings(strip(kind, at))
    if n > len(found):
        return {"ok": False, "why": f"{said}: {found_list(kind, at, found)}"}
    p = found[n - 1]
    return {"ok": True, "at": [at, p] if kind == "col" else [p, at]}


def found_list(kind, at, found):
    """A strip's crossings, as a refusal hands them back for the agent to pick from."""
    name = f"{'column' if kind == 'col' else 'row'} {at}"
    if not found:
        return f"{name} crosses no edge"
    return f"{name} crosses " + ", ".join(f"#{n} at {p:.1f}" for n, p in enumerate(found, 1))


def edges(strip, size, said):
    """`--edges col:0.3`: the crossings one strip finds, numbered, for the
    agent to pick a line's ends from. Positions count from the top or the
    left, as a mark's pixel does."""
    got = pick(f"{said}#1", size)
    if got is None:
        return f"  edges {said}  not a strip: say row:F or col:F, F from 0 to 1"
    kind, at, _ = got
    return f"  edges {found_list(kind, at, crossings(strip(kind, at)))}"


FLAGS = ("--direction", "--line", "--line-by-eye")
"""Every flag the direction form takes, each with a value and the last two
as often as there are lines. Anything else is refused, as the span forms
refuse it (ADR 0022, decision 2)."""


def form(rest):
    """`contour measure <ref> --direction x --line col:0.3#2,col:0.55#2 ...
    "what the edges are"` into `{"ok", "name", "picks", "text"}`, or a
    refusal. A by-eye line is `--line-by-eye X0,Y0,X1,Y1`, rows from the top."""
    name, picks, text, i = None, [], [], 0
    while i < len(rest):
        said = rest[i]
        if not said.startswith("--"):
            text.append(said)
            i += 1
            continue
        value = rest[i + 1] if i + 1 < len(rest) else ""
        i += 2
        if said not in FLAGS:
            return _refused(f"{said} is not part of a direction: the agent picks "
                            f"each line's ends from crossings measured, or places "
                            f"a line by eye with --line-by-eye")
        if said == "--direction":
            name = value
        elif said == "--line":
            ends = value.split(",")
            if len(ends) != 2:
                return _refused(f"--line {value} is not two crossings: say "
                                f"--line col:0.3#2,col:0.55#2")
            picks.append(tuple(ends))
        else:
            try:
                x0, y0, x1, y1 = (float(v) for v in value.split(","))
            except ValueError:
                return _refused(f"--line-by-eye {value} is not X0,Y0,X1,Y1")
            picks.append({"by_eye": [[x0, y0], [x1, y1]]})
    if not name:
        return _refused("name the direction: --direction x")
    if len(text) != 1:
        return _refused('say in one line what the edges are, e.g. "the body tube\'s '
                        'top and bottom edges"')
    return {"ok": True, "name": name, "picks": picks, "text": text[0]}


def _refused(why):
    return {"ok": False, "lines": [f"FAIL measure  {why}"]}


def line(strip, size, a, b):
    """A line through two picked crossings: `{"ok", "from", "to"}`, or the
    first refusal."""
    ends = [place(strip, size, said) for said in (a, b)]
    for end in ends:
        if not end["ok"]:
            return end
    return {"ok": True, "from": ends[0]["at"], "to": ends[1]["at"]}


def propose(path, ref, name, picks, strip, size, text):
    """An agent direction on `ref`, one line per pair of picked crossings, or
    per `{"by_eye": [from, to]}` where nothing would snap (ADR 0022, decision
    3). Returns a report; nothing is written unless every line is placed.

    One mark for the direction, not one per line: it is one question, *are
    these edges parallel in the object?*, and answered once. Each line keeps
    the two crossings it was asked as, so it can be asked again.
    """
    if len(picks) < 2:
        return {"ok": False, "lines": [
            f"FAIL measure  direction {name}: a direction needs at least two lines, "
            f"since it is where they meet: nothing was drawn"]}
    lines = []
    for asked in picks:
        if isinstance(asked, dict):
            a, b = asked["by_eye"]
            lines.append({"from": list(a), "to": list(b), "placed": "by eye"})
            continue
        a, b = asked
        got = line(strip, size, a, b)
        if not got["ok"]:
            return {"ok": False, "lines": [f"FAIL measure  direction {name}: {got['why']}: "
                                           f"nothing was drawn"]}
        lines.append({"from": got["from"], "to": got["to"], "placed": "snapped",
                      "question": [a, b]})
    first = lines[0]
    drawn = marks.append(path, {"ref": ref, "direction": name, "text": text, "lines": lines,
                                "pixel": [round((first["from"][i] + first["to"][i]) / 2)
                                          for i in (0, 1)]},
                         author="agent")
    eyed = sum(1 for got in lines if got["placed"] == "by eye")
    return {"ok": True, "lines": [f"ok   measure {drawn['id']} {ref}  direction {name}: "
                                  f"{text}  ({len(lines)} lines"
                                  + (f", {eyed} by eye" if eyed else "") + ")"]}
