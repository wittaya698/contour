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
import re
from pathlib import Path

from . import marks, miniyaml

WORDS = {
    "spec-write": ("Claude wants to change the spec", "Allow", "Deny"),
    "ref-write": ("Claude wants to change your reference pictures", "Allow", "Deny"),
    "build": ("Claude wants to build the model to check its work", "Allow", "Deny"),
    "commit": ("Save this version?", "Save", "Not yet"),
    "push": ("Claude wants to send this model off this computer", "Allow", "Deny"),
}
"""Category -> the act, and the two answers to it. Every category `contour
intents` prints is here (`tests/test_gate.py`)."""


def say(category, space, tool, call, proposal=""):
    """What a page says about one gate, as one dict it renders and does not
    reason about. A category the table does not know shows its own name, and
    the plain answers: arriving visible, as `lib/verdict.py`'s unworded check
    does.

    `proposal` is what the agent last said before the call. For a spec write
    it is the argument rule 1 asks for, and the span it names is named here.
    """
    act, allow, deny = WORDS.get(category, (category, "Allow", "Deny"))
    said = {"act": act, "allow": allow, "deny": deny, "changes": [], "spans": []}
    if category == "spec-write":
        said["changes"] = changes(Path(space) / "spec.yaml", tool, call)
        said["spans"] = spans(Path(space) / marks.NAME, proposal)
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
    640 mm*, in the order the spec will read. Empty when the write cannot be
    read ahead of running it — a shell call is a program, not a document — and
    the raw call is what is left to read, as it was before."""
    was = spec.read_text(encoding="utf-8") if spec.is_file() else ""
    if tool == "Write":
        will = call.get("content", "")
    elif tool == "Edit" and call.get("old_string", "") in was:
        count = -1 if call.get("replace_all") else 1
        will = was.replace(call["old_string"], call.get("new_string", ""), count)
    else:
        return []
    try:
        before, after = flat(miniyaml.loads(was) or {}), flat(miniyaml.loads(will) or {})
    except miniyaml.YamlError:
        return []
    return [field(path, before.get(path), after.get(path))
            for path in dict.fromkeys([*after, *before])
            if path != ("revision",) and before.get(path) != after.get(path)]


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
