"""Where a model's files live (ADR 0015: the toolkit is a tool, a model is a
space).

A **model space** is its own directory and its own git repository, flat:

    <space>/        spec.yaml  refs/  build.py  sheet.png  NOTES.md   tracked
                    out/  exports/                                    ignored
                    release/v<N>/                                     tracked
                    .contour/project                                  the marker

The launcher finds the space by walking up from the working directory and
passes it in as CONTOUR_PROJECT. The **fixture** is the one exception: it lives
inside the toolkit and is addressed by name, because the selftest has no space
to stand in. It has no tracked sheet or export -- nothing about it is a
deliverable -- so those land in its out/ and the selftest can never dirty a
tracked file.
"""
import os
from pathlib import Path

ROOT = Path(os.environ.get("CONTOUR_ROOT") or Path(__file__).resolve().parent.parent)
_p = os.environ.get("CONTOUR_PROJECT")
PROJECT = Path(_p) if _p else None


MARKER = Path(".contour") / "project"


def find(start=None):
    """The model space containing `start`, or None. Walks up for
    `.contour/project`, the way git walks up for `.git`.

    The marker is that file and not the `.contour/` directory: the toolkit has
    a `.contour/` too, for its own logs, and must never be mistaken for a
    space. Lives here because two callers now walk — the launcher and the
    console — and what a space *is* gets one definition.
    """
    here = (Path(start) if start else Path.cwd()).resolve()
    for d in (here, *here.parents):
        if (d / MARKER).is_file():
            return d
    return None


def parse(args):
    """['smoke', '--fixture'] -> ('smoke', True);  [] -> (<space name>, False).

    A model is never named on the command line: you are standing in it.
    """
    if "--fixture" in args:
        names = [a for a in args if not a.startswith("--")]
        if len(names) != 1:
            raise SystemExit(f"--fixture takes exactly one name, got {names}")
        return names[0], True
    extra = [a for a in args if not a.startswith("--")]
    if extra:
        raise SystemExit(f"this command takes no model name, got {extra}: "
                         f"cd into the model space and run it there (ADR 0015)")
    if PROJECT is None:
        raise SystemExit("not in a model space: no .contour/project found here "
                         "or above (ADR 0015)")
    return PROJECT.name, False


def resolve(variant, fixture=False):
    base = ROOT / "fixtures" / variant if fixture else PROJECT
    out = base / "out"
    return {"spec": base / "spec.yaml",
            "build": base / "build.py",
            "refs": base / "refs",
            "out": out,
            "blend": out / f"{variant}.blend",
            "sheet": out / "sheet.png" if fixture else base / "sheet.png",
            "mask": out / "mask.png",
            "parts": out / "parts.json",
            "views": out / "views.json",
            "marks": out / "marks.json" if fixture else base / "marks.json",
            "glb": out / f"{variant}.glb" if fixture else base / "exports" / f"{variant}.glb",
            "release": base / "release"}


def display(path):
    """A path as a human should read it: relative to whichever root owns it."""
    for root in (PROJECT, ROOT):
        if root:
            try:
                return str(path.relative_to(root))
            except ValueError:
                pass
    return str(path)
