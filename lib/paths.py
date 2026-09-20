"""Where a variant's files live. The fixture gets its own out/ so selftest never
overwrites a real build or a tracked render."""
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
    if fixture:
        base, out = ROOT / "fixtures" / variant, ROOT / "out" / "selftest"
        return {"spec": base / "spec.yaml", "build": base / "build.py", "out": out,
                "blend": out / f"{variant}.blend", "sheet": out / f"{variant}.png",
                "glb": out / f"{variant}.glb"}
    out = ROOT / "out"
    return {"spec": ROOT / "spec" / f"{variant}.yaml",
            "build": ROOT / "models" / variant / "build.py", "out": out,
            "blend": out / f"{variant}.blend", "sheet": ROOT / "renders" / f"{variant}.png",
            "glb": ROOT / "exports" / f"{variant}.glb"}
