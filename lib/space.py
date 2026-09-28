"""What a model space is, what it contains, and where spaces are found
(ADR 0015: the toolkit is a tool, a model is a space).

A **model space** is its own directory and its own git repository, flat:

    <space>/        spec.yaml  refs/  build.py  sheet.png  NOTES.md   tracked
                    out/  exports/                                    ignored
                    release/v<N>/                                     tracked
                    .contour/project                                  the marker

The layout is a function of the space and not of the process: it was a table
read out of `$CONTOUR_PROJECT` at import once, which meant only the Blender side
could ask it, and the launcher and the console re-derived the same conventions by
hand. Ask it about the space you have.
"""
import os
from pathlib import Path
from typing import NamedTuple

MARKER = Path(".contour") / "project"


class Layout(NamedTuple):
    """Where one space keeps its files. A tuple of paths and not a dict, so a
    name it does not have is an `AttributeError` at the call site rather than a
    `KeyError` somewhere later, or a silent `None`."""
    toolkit: Path
    root: Path
    name: str
    spec: Path
    build: Path
    refs: Path
    out: Path
    dot: Path
    blend: Path
    sheet: Path
    marks: Path
    glb: Path
    mask: Path
    parts: Path
    views: Path
    release: Path

    @property
    def fixture(self):
        """Whether this is the fixture's layout.

        Derived from where it sits, not remembered from a flag the constructor
        took: `lib/mutants.py` breaks a build on purpose and may run nowhere
        else, so there must be no way to hand it a space's layout that says it
        is the fixture.
        """
        return (self.toolkit is not None
                and self.root.parent == self.toolkit / "fixtures")

    def display(self, path):
        """This path as a report should read it, relative to whichever root
        owns it.

        The toolkit is asked first, and owns only the fixture: a model space is
        never inside the toolkit (ADR 0015, and the push guard refuses one that
        is), so the question only ever arises for the selftest — where *which
        fixture* is the part worth printing.
        """
        for root in (self.toolkit, self.root):
            if root:
                try:
                    return str(Path(path).relative_to(root))
                except ValueError:
                    pass
        return str(path)


def find(start=None):
    """The model space containing `start`, or None. Walks up for
    `.contour/project`, the way git walks up for `.git`.

    The marker is that file and not the `.contour/` directory: the toolkit has a
    `.contour/` too, for its own logs, and must never be mistaken for a space.
    """
    here = (Path(start) if start else Path.cwd()).resolve()
    for d in (here, *here.parents):
        if (d / MARKER).is_file():
            return d
    return None


def _at(toolkit, root, name, sheet, marks, glb):
    """One layout, given the three paths the two layouts disagree about.

    Everything else is the same table in both, so it is written once: the
    difference between a space and the fixture is exactly *where a deliverable
    goes*, and that is legible here as three arguments rather than as two
    tables a reader has to diff.
    """
    out = root / "out"
    return Layout(toolkit=toolkit, root=root, name=name, out=out,
                  dot=root / ".contour",
                  spec=root / "spec.yaml", build=root / "build.py",
                  refs=root / "refs", release=root / "release",
                  blend=out / f"{name}.blend", mask=out / "mask.png",
                  parts=out / "parts.json", views=out / "views.json",
                  sheet=sheet, marks=marks, glb=glb)


def layout(root, toolkit=None):
    """A model space: the ordinary case, and the only one the launcher and the
    console ever see. Its sheet and its export are deliverables, so they sit
    where git can see them."""
    root = Path(root)
    return _at(Path(toolkit) if toolkit else None, root, root.name,
               sheet=root / "sheet.png", marks=root / "marks.json",
               glb=root / "exports" / f"{root.name}.glb")


def fixture(name, toolkit):
    """The selftest's fixture, which lives inside the toolkit and is addressed
    by name, because the selftest has no space to stand in.

    Nothing about it is a deliverable, so what a space keeps at its root the
    fixture keeps in `out/`, and the selftest can never dirty a tracked file by
    running.
    """
    toolkit = Path(toolkit)
    root = toolkit / "fixtures" / name
    return _at(toolkit, root, name, sheet=root / "out" / "sheet.png",
               marks=root / "out" / "marks.json",
               glb=root / "out" / f"{name}.glb")


def parse(args):
    """The layout this Blender process was launched for, picked from argv.

    `['smoke', '--fixture']` is the fixture; `[]` is the space the launcher
    started us in. A model is never named on the command line: you are standing
    in it, and a name accepted here would be a second way to say which space —
    one that could disagree with the directory the user is in.

    The one place the environment is read, and read when called rather than at
    import. `$CONTOUR_PROJECT` is how the launcher tells this process which
    space it is about; everything else takes the space it is asked about, which
    is what lets the launcher and the console ask at all.
    """
    toolkit = Path(os.environ["CONTOUR_ROOT"])
    named = [a for a in args if not a.startswith("--")]
    if "--fixture" in args:
        if len(named) != 1:
            raise SystemExit(f"--fixture takes exactly one name, got {named}")
        return fixture(named[0], toolkit)
    if named:
        raise SystemExit(f"this command takes no model name, got {named}: "
                         f"cd into the model space and run it there (ADR 0015)")
    here = os.environ.get("CONTOUR_PROJECT")
    if not here:
        raise SystemExit("not in a model space: no .contour/project found here "
                         "or above (ADR 0015)")
    return layout(here, toolkit)


def roots(toolkit):
    """Where to look for spaces. `$CONTOUR_SPACES` overrides; otherwise the
    directory holding the toolkit, which is where spaces live by convention.

    This names where to look, not what exists — so unlike a registry it cannot
    go stale, and a space moved within a root is still found (ADR 0015).
    """
    told = os.environ.get("CONTOUR_SPACES")
    return ([Path(p).expanduser() for p in told.split(":") if p] if told
            else [Path(toolkit).parent])


SKIP = {"node_modules", "venv", ".venv", "target", "Library", "Pictures", "Music"}


def spaces(where, depth=4):
    """Every model space under `where`, by its marker.

    Bounded on purpose: a scan of $HOME does not finish in a usable time, a
    scan of one workspace is instant.
    """
    found = []
    for root in where:
        root = Path(root)
        if not root.is_dir():
            continue
        base = len(root.parts)
        for here, dirs, _ in os.walk(root):
            d = Path(here)
            if (d / MARKER).is_file():
                found.append(d)
                dirs[:] = []                      # spaces do not nest
                continue
            if len(d.parts) - base >= depth:
                dirs[:] = []
                continue
            dirs[:] = [x for x in dirs if not x.startswith(".") and x not in SKIP]
    return sorted(found)
