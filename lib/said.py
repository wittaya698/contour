"""A size the chat said, carried to a new space's console as a value (ADR 0033).

A Desktop chat that makes a space often already heard how big the thing is.
`create` takes that as `{"dimension": "width", "mm": 300}`, the launch line
carries it as `--said width:300`, and the console turns it into the toolkit's
own sentence: a suggestion the user is asked, never the anchor. A dimension
from a fixed three and a number are not words, so the launch line still
carries none anybody else wrote (ADR 0021, decision 4).

Blender-free: the connector and the console both import it.
"""
import math

DIMENSIONS = {"height": "tall", "width": "wide", "depth": "deep"}
"""The overall three the schema names, each as the user would say it. A part's
dimension is not one: before a spec there are no parts for it to belong to."""


def value(anchor):
    """`anchor`, as `create` takes it, in the launch line's spelling. Refused,
    in words about the size, unless it is one of the three and a positive,
    finite number of millimetres."""
    if not isinstance(anchor, dict):
        raise ValueError(f"an anchor is a dimension and its mm, not {anchor!r}")
    dimension, mm = anchor.get("dimension"), anchor.get("mm")
    if dimension not in DIMENSIONS:
        raise ValueError(f"an anchor's dimension is one of {', '.join(DIMENSIONS)}, "
                         f"not {dimension!r}")
    if isinstance(mm, bool) or not isinstance(mm, (int, float)) \
            or not math.isfinite(mm) or not mm > 0:
        raise ValueError(f"an anchor's mm is a positive number, not {mm!r}")
    return f"{dimension}:{millimetres(mm)}"


def read(text):
    """The launch line's `dimension:mm` back to the two, refused as `value`
    refuses."""
    dimension, _, mm = str(text).partition(":")
    try:
        number = float(mm)
    except ValueError:
        raise ValueError(f"one of {', '.join(DIMENSIONS)} and its mm, as width:300, "
                         f"not {text!r}") from None
    value({"dimension": dimension, "mm": number})
    return dimension, number


def size(dimension, mm):
    """*300 mm wide*."""
    return f"{millimetres(mm)} mm {DIMENSIONS[dimension]}"


def sentence(dimension, mm):
    """What the console's first prompt adds: what the chat said, whose it is,
    and that only the user's answer here is the anchor (ADR 0033, decision 4)."""
    said = size(dimension, mm)
    return (f"In the Desktop chat that made this space, the user was understood "
            f"to say it is {said}. That is what another model wrote, not something "
            f"the user told you. Ask whether it is right — \"Is it {said}, as you "
            f"said in the chat?\" — and take only their answer here as the anchor.")


def millimetres(mm):
    """300, not 300.0; 300.5 as it is."""
    return f"{int(mm)}" if float(mm).is_integer() else f"{mm}"
