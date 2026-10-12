"""A model's topics: the words it is labelled with so it can be found
(ADR 0030).

Beside `marks.json` and `vetoes.json` at the space's root, tracked for the same
reason, and saved with the next version like them. Two lists: the words the user
approved, and the words they struck, which are remembered so that the agent is
never offered back a word the user already said no to for this model.

Blender-free: the console writes it and the launcher and the lobby read it.
"""
import re
import shlex
from pathlib import Path

from . import intent, store

_BY_HAND = re.compile(r"\bcontour\s+topics\s+(add|strike)\b")

NAME = "topics.json"

CATEGORY = "topics"
"""A proposal's gate category, which the ask-list never lets through: approving
is the point (ADR 0030, decision 2)."""


def load(space):
    """The approved topics and the struck words, each in the order they came."""
    held = store.load(Path(space) / NAME, {})
    return {"topics": list(held.get("topics", [])),
            "struck": list(held.get("struck", []))}


def offered(space, words):
    """`words` as they may be put to the user, each spelled as it is kept and
    once: `(offered, struck_before)`.
    A word the user struck for this model is never offered again (ADR 0030,
    decision 5); it is held back and named, so the agent can be told why."""
    struck = set(load(space)["struck"])
    spelled = [w for w in dict.fromkeys(word(t) for t in words) if w]
    return ([w for w in spelled if w not in struck],
            [w for w in spelled if w in struck])


def answered(space, proposed, kept):
    """A proposal answered: `kept` become topics and the rest are struck."""
    held = load(space)
    for word in proposed:
        into = held["topics"] if word in kept else held["struck"]
        if word not in into:
            into.append(word)
    store.save(Path(space) / NAME, held)
    return held


def word(text):
    """A topic as it is kept: trimmed and lowercased, so a filter finds
    *Creature* and *creature* as one word. None for nothing."""
    text = " ".join((text or "").split()).lower()
    return text or None


def add(space, text):
    """The user's own word, ungated. One they struck before is theirs to take
    back: the memory exists to stop the agent offering it, not them."""
    held = load(space)
    w = word(text)
    if w is None:
        raise ValueError("a topic is a word; this one is empty")
    held["struck"] = [s for s in held["struck"] if s != w]
    if w not in held["topics"]:
        held["topics"].append(w)
    store.save(Path(space) / NAME, held)
    return held


def strike(space, text):
    """The user strikes a word: no longer a topic, and never proposed again."""
    held = load(space)
    w = word(text)
    if w is None:
        raise ValueError("a topic is a word; this one is empty")
    held["topics"] = [t for t in held["topics"] if t != w]
    if w not in held["struck"]:
        held["struck"].append(w)
    store.save(Path(space) / NAME, held)
    return held


FIRST_GREEN = "next first green: propose topics to find this model by"
"""What `contour check` says once in a model's life (ADR 0030, decision 4)."""


STAMP = "first-green"
"""Beside the check's own record in `.contour/`: that it has been said."""


def first_green(dot, was, now):
    """The line a check adds at the model's first green build, or None.
    Stamped at every green, so it is said once and never after; `was`, the
    check's last verdict, says a space green before stamps existed is past it."""
    if not now.get("ok"):
        return None
    stamp = Path(dot) / STAMP
    if stamp.is_file():
        return None
    stamp.write_text("")
    # Green before there was a stamp to keep: past its first green already.
    return None if (was or {}).get("ok") else FIRST_GREEN


def by_hand(tool, payload):
    """Whether this call labels the model other than by proposing: the user's
    own command, or the file itself. The console refuses it from its agent, as
    the ask-list's writer is refused (ADR 0030, decision 2)."""
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return Path(payload.get("file_path") or payload.get("notebook_path") or "").name == NAME
    text = payload.get("command") or ""
    try:
        written = NAME in text and intent.writes(text, shlex.split(text))
    except ValueError:
        written = NAME in text        # unreadable: not given the benefit of it
    return written or bool(_BY_HAND.search(text))


def told(proposed, kept, struck_before=()):
    """The answer as the agent is told it: kept, struck, and held back."""
    return {"kept": kept, "struck": [w for w in proposed if w not in kept],
            "struck_before": list(struck_before)}
