"""Where a variant's files live (ADR 0012: one directory per model).

    models/<v>/     spec.yaml  refs/  build.py  sheet.png  NOTES.md   tracked
                    out/  exports/                                    ignored
                    release/v<N>/                                     tracked

The fixture has the same shape under `fixtures/`, with one difference: it has
no tracked sheet or export, because nothing about it is a deliverable, so
those land in its `out/` with the rest of its scratch. That also keeps the
selftest from ever dirtying a tracked file.
"""
import os
from pathlib import Path

ROOT = Path(os.environ.get("CONTOUR_ROOT") or Path(__file__).resolve().parent.parent)


def parse(args):
    """['smoke', '--fixture'] -> ('smoke', True)"""
    fixture = "--fixture" in args
    names = [a for a in args if not a.startswith("--")]
    if len(names) != 1:
        raise SystemExit(f"expected exactly one variant name, got {names}")
    return names[0], fixture


def resolve(variant, fixture=False):
    base = ROOT / ("fixtures" if fixture else "models") / variant
    out = base / "out"
    return {"spec": base / "spec.yaml",
            "build": base / "build.py",
            "refs": base / "refs",
            "out": out,
            "blend": out / f"{variant}.blend",
            "sheet": out / "sheet.png" if fixture else base / "sheet.png",
            "glb": out / f"{variant}.glb" if fixture else base / "exports" / f"{variant}.glb",
            "release": base / "release"}
