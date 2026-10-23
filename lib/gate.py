"""What a gate says, in plain words (ADR 0025, decision 6).

A gate is a confirm and never a proposal (rule 1): the case for a call is made
before it, in the agent's prose. What the gate owes the person answering it is
the act — what Claude wants to do — and what would change, so that *allow*
answers a sentence they could read. The raw call stays on the page, one click
away, and is never offered for editing (ADR 0019, decision 13).

One table, keyed by the categories `lib/intent.py` declares, for the reason
`lib/verdict.py` is one table: a second would be a second vocabulary.

Stdlib, and Blender-free: the console imports this to draw a gate.
"""
import difflib
import json
import re
from pathlib import Path

from . import marks, miniyaml, policy

WORDS = {
    "spec-write": ("Claude wants to change the spec", "Allow", "Deny"),
    "ref-write": ("Claude wants to change your reference pictures", "Allow", "Deny"),
    "build": ("Claude wants to build the model to check its work", "Allow", "Deny"),
    "commit": ("Save this version?", "Save", "Not yet"),
    "push": ("Claude wants to send this model off this computer", "Allow", "Deny"),
    "topics": ("Claude suggests words to find this model by", "Keep these", "None of them"),
}
"""Category -> the act, and the two answers to it. Every category `contour
intents` prints is here (`tests/test_gate.py`)."""

REVISION = ("revision",)
"""The field a spec write bumps, which no write may move alone (issue 104)."""

UNWATCHED = {
    "spec-write": "Changing the spec",
    "ref-write": "Changing your reference pictures",
    "build": "Building the model to check its work",
    "commit": "Saving a version",
    "push": "Sending this model off this computer",
}
"""Category -> what runs without asking, as the page lists it beside Undo. All
five, though *Always* writes only a build: a hand-written list can say any."""


def unwatched(space):
    """What this space lets through without asking, as the page lists it. A
    category the table lacks shows its own name, as `say` does."""
    return [{"category": c, "says": UNWATCHED.get(c, c)}
            for c in policy.allowed(space)]


def say(category, space, tool, call, proposal=""):
    """What a page says about one gate, as one dict it renders and does not
    reason about. A category the table does not know shows its own name, and
    the plain answers: arriving visible, as `lib/verdict.py`'s unworded check
    does.

    `proposal` is what the agent last said before the call. For a spec write
    it is the argument rule 1 asks for, and the span it names is named here.

    `always` is whether the gate offers a third answer, *Always for this
    model*: on a build only, from the table `lib/policy.py` writes against.
    """
    act, allow, deny = WORDS.get(category, (category, "Allow", "Deny"))
    said = {"act": act, "allow": allow, "deny": deny, "changes": [], "spans": [],
            "always": category in policy.ALWAYS}
    if category == "spec-write":
        said["changes"] = changes(Path(space) / "spec.yaml", tool, call)
        said["spans"] = spans(Path(space) / marks.NAME, proposal)
    if category == "topics":
        # Each its own toggle: the person keeps or strikes word by word
        # (ADR 0030, decision 2).
        said["words"] = list(call.get("words") or [])
        said["new"] = list(call.get("new") or [])
    return said


def spans(held, proposal):
    """The spans `proposal` names, in the order it names them. Only an id this
    space holds as a span: a plain mark mentioned in passing is not a
    measurement, and an id held nowhere is not one either."""
    are = {m["id"] for m in marks.load(held) if marks.span_end(m)}
    named = re.findall(rf"\b{marks.PREFIX}\d+\b", proposal or "")
    return [n for n in dict.fromkeys(named) if n in are]


def changes(spec, tool, call):
    """Each field a spec write moves, as a person reads it: *seat depth 600 →
    640 mm*, in the order the spec will read. The revision too: left out, a
    write that bumps it read as one that did not, and was denied for it
    (issue 126). Empty when the write cannot be
    read ahead of running it — a shell call is a program, not a document — and
    the raw call is what is left to read, as it was before."""
    out = []
    for path, (was, will) in (moved(spec, tool, call) or {}).items():
        if isinstance(was, list) and isinstance(will, list):
            out += items(path, was, will)
        else:
            out.append(field(path, was, will))
    return out


def items(path, was, will):
    """A list that moved, as the items that moved in it: *notes 6: … diameter,
    ~170 → ~191 proud …*, and the rest not at all, so nobody hunts for the one
    changed word in two copies of the list (issue 111). One added or removed
    is said as that. An item is named by where it stands, counting from 1 — in
    the old list if it went, in the new one otherwise — since it has no name
    of its own."""
    name = " ".join(path).replace("_", " ")
    key = [json.dumps(item, sort_keys=True, default=str) for item in (*was, *will)]
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, key[:len(was)], key[len(was):], autojunk=False).get_opcodes():
        if op == "equal":
            continue
        paired = min(i2 - i1, j2 - j1) if op == "replace" else 0
        out += [f"{name} {j1 + k + 1}: {reworded(number(was[i1 + k]), number(will[j1 + k]))}"
                for k in range(paired)]
        out += [f"{name} {i + 1} removed: {number(was[i])}" for i in range(i1 + paired, i2)]
        out += [f"{name} {j + 1} added: {number(will[j])}" for j in range(j1 + paired, j2)]
    return out


def reworded(was, will):
    """Only the words that changed, and one either side to find them by."""
    a, b = was.split(), will.split()
    head = 0
    while head < min(len(a), len(b)) and a[head] == b[head]:
        head += 1
    tail = 0
    while tail < min(len(a), len(b)) - head and a[-1 - tail] == b[-1 - tail]:
        tail += 1
    before = (["…"] if head > 1 else []) + a[max(head - 1, 0):head]
    after = a[len(a) - tail:][:1] + (["…"] if tail > 1 else [])
    return " ".join([*before, *a[head:len(a) - tail], "→",
                     *b[head:len(b) - tail], *after])


def moved(spec, tool, call):
    """Every field a spec write moves, `revision` too, as {path: (was, will)}
    in the order the spec will read; None when the write cannot be read ahead
    of running it."""
    was = spec.read_text(encoding="utf-8") if spec.is_file() else ""
    if tool == "Write":
        will = call.get("content", "")
    elif tool == "Edit" and call.get("old_string", "") in was:
        count = -1 if call.get("replace_all") else 1
        will = was.replace(call["old_string"], call.get("new_string", ""), count)
    else:
        return None
    try:
        before, after = flat(miniyaml.loads(was) or {}), flat(miniyaml.loads(will) or {})
    except miniyaml.YamlError:
        return None
    return {path: (before.get(path), after.get(path))
            for path in dict.fromkeys([*after, *before])
            if before.get(path) != after.get(path)}


def partial(spec, tool, call):
    """Whether a spec write is part of a change and not the whole of one: the
    revision alone, or a field without the revision, which rule 1 bumps in
    the same write (issue 104). A write that cannot be read, or moves nothing
    a person could name, is not said to be either."""
    fields = moved(spec, tool, call)
    if not fields:
        return False
    return REVISION not in fields or set(fields) == {REVISION}


THOUSANDS = re.compile(r"(?<![\d.,])\d{1,3}(?:[,    ]\d{3})+(?:\.\d+)?(?![\d])")
"""A number with its thousands marked by a comma or a space."""


def unargued(spec, tool, call, proposal):
    """The numbers a spec write sets that `proposal`, the agent's text just
    before it, never names, as a person would write them: *644*, not *644.0*.
    Only numbers, since prose is not quoted back as a case; and a number inside
    another (*6440*, *1.644*) is not that number (issue 106)."""
    # By size, so *640.0* is 640, and a sign is left to the prose: a minus is
    # as often typed `−` as `-`.
    named = {float(n) for n in re.findall(r"\d+(?:\.\d+)?", proposal or "")}
    # And with its thousands marked, *8,000* or *8 000*, as the page's own
    # words say a triangle budget (issue 155). Read beside the plain reading,
    # never instead, so this lets more cases through and refuses none.
    named |= {float(re.sub(r"[^\d.]", "", n)) for n in THOUSANDS.findall(proposal or "")}
    return [number(will) for path, (_, will) in (moved(spec, tool, call) or {}).items()
            if path != REVISION and isinstance(will, (int, float))
            and not isinstance(will, bool) and abs(will) not in named]


def flat(doc, at=()):
    """A spec as {path: value}, one entry per scalar a person could name; a
    list is one value, since its items have no names of their own."""
    if not isinstance(doc, dict):
        return {at: doc}
    out = {}
    for key, value in doc.items():
        out.update(flat(value, (*at, str(key))))
    return out


def field(path, was, will):
    """One moved field, in words. A dimension is millimetres, as the schema
    says it always is, and so is anything whose key says `_mm`."""
    words, unit = list(path), ""
    if words[0] == "dimensions":
        # `height: { value, tol }`, or `height: 820` alone; a sub-measurement's
        # `part` is a name and not a length.
        words = words[1:]
        if words[-1] == "value" or len(words) == 1:
            words, unit = words[:1], " mm"
        elif words[-1] == "tol":
            words[-1], unit = "tolerance", " mm"
    elif words[-1].endswith("_mm"):
        words[-1], unit = words[-1].removesuffix("_mm"), " mm"
    name = " ".join(words).replace("_", " ")
    return f"{name} {number(was)} → {number(will)}{unit}"


def number(value):
    """A value as a person writes it: `600.0` is 600, and none is *none*."""
    if value is None:
        return "none"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
