"""Whether the model is right, said in plain words (ADR 0025, decision 4).

`last-build.json` keeps the last check's verdict whole (issue 58); this is what
a page says about it. One table, keyed by check id, and one owner, because the
console's panel, the lobby row, the export card, the page header and the
connector all say these same sentences — a second table would be a second
vocabulary to keep in step.

Stdlib, and Blender-free: both hosts serve it (ADR 0019, decision 32).
"""
import re


def _n(text):
    """A number as a person writes it: `1640.0` is 1640, `1640.4` stays."""
    return text[:-2] if text.endswith(".0") else text


def _reads(pattern, said):
    """A sentence for a check whose message carries the numbers: `pattern`
    finds what was measured and what was wanted in the check's own words, and
    `said` puts them in plain ones. None when the message no longer reads that
    way, and the report line is shown instead."""
    def sentence(r):
        m = re.search(pattern, r["msg"])
        return m and said.format(*(_n(g) for g in m.groups()))
    return sentence


def _lead(lead, prefix=""):
    """A sentence for a check whose message is a list of what it found: a
    plain lead, then the check's own detail, which is the measured half and
    names the parts it was found in."""
    def sentence(r):
        return f"{lead}: {r['msg'].removeprefix(prefix)}."
    return sentence


def _dimension(word):
    return _reads(r"([\d.]+)mm, want ([\d.]+)±([\d.]+)",
                  word + " is {} mm; the spec wants {}, give or take {}.")


WORDS = {
    "spec": _lead("The spec asks for something that can't be checked"),
    "height": _dimension("Height"),
    "width": _dimension("Width"),
    "depth": _dimension("Depth"),
    "parts": _lead("The parts don't match the spec's list", "parts "),
    "tris": _reads(r"tris ([\d,]+) > budget ([\d,]+)",
                   "It has {} triangles; the spec allows {}."),
    "quads": _reads(r"quads ([\d.]+)%, want >=([\d.]+)%",
                    "{}% of its faces have four sides; the spec wants at least {}%."),
    "ngons": _lead("Some faces have more than four sides", "ngons "),
    "manifold": _lead("The surface has holes or open edges", "non-manifold edges "),
    "loose": _lead("There are stray points or edges that belong to no face",
                   "loose verts/edges "),
    "normals": _lead("Some faces point inward", "inward faces "),
    "doubles": _reads(r"vertices within ([\d.]+)mm in (.+)",
                      "Some points sit closer than {} mm to each other, in {}."),
    "uv": _lead("The texture layout isn't right", "uv "),
    "mat_slots": _reads(r"(\d+) materials > max (\d+)",
                        "It uses {} materials; the spec allows {}."),
    "mat_names": _lead("The materials don't match the spec's names", "materials "),
    "up_axis": _lead("The spec wants a different way up"),
    "origin": _lead("The point it stands on isn't where the spec puts it"),
    "scale": _lead("Some parts still carry a size change that wasn't applied",
                   "scale not applied: "),
    "rotation": _lead("Some parts still carry a turn that wasn't applied",
                      "rotation not applied: "),
    "rig": _lead("Which part hangs from which isn't a tree", "rig "),
    "seams": _lead("A joint has no seam where its two parts meet"),
    "pivots": _lead("A part doesn't turn where its joint is"),
    "bones": _lead("The skeleton doesn't match the parts", "bones "),
    "clips": _lead("An animation doesn't match the spec", "clips "),
    "gl_rig": _lead("The exported file's skeleton or animations differ from the build"),
    "re_motion": _lead("Parts move differently in the exported file than in the build"),
}
"""Check id -> how a failure of it is said, in the order the report reads.
Every id `lib/checks.py` can report is here (`tests/test_verdict.py`)."""


def sentence(r):
    """One failing check, as one plain sentence — or, for a check the table
    does not know or a message it cannot read, the check's report line. Never
    dropped: a check added to the toolkit later arrives visible."""
    words = WORDS.get(r["id"])
    return (words and words(r)) or f"{r['id']}  {r['msg']}"


def say(kept):
    """What a page says about one kept verdict, as one dict it renders and
    does not reason about.

    A build that never got as far as being judged has no failures because
    nothing judged it, and says that rather than a count of none.
    """
    if not kept["built"]:
        return {"ok": False, "line": "the build stopped before it could be checked",
                "failing": [], "passing": []}
    results = kept["results"]
    failing = [sentence(r) for r in results if not r["ok"]]
    if failing:
        n = len(failing)
        line = (f"{n} thing doesn't" if n == 1 else f"{n} things don't") + " match the spec"
    else:
        line = "matches the spec"
    return {"ok": not failing, "line": line, "failing": failing,
            "passing": [reading(r) for r in results if r["ok"]]}


def reading(r):
    """One passing check, as the terminal's green line reads it: the id and
    what it came to, said once when the reading already names itself."""
    return r["info"] if r["info"].startswith(r["id"]) else f"{r['id']} {r['info']}".strip()
