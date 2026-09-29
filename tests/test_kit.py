"""`lib/kit.py`'s interface, which every space's `build.py` is written against.

Its callers live in other repositories, so nothing in this one breaks when a
parameter is renamed or a default moves — four spaces do, the next time each is
built. `kit` needs `bpy`, so this reads its source rather than importing it.
The table is the promise: changing it is allowed, and is the moment to say so.
What `kit` does is the fixture's build, run by `contour selftest`; what it
computes is `tests/test_units.py` (issue 26).
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROMISED = {
    "mm": "(*v)",
    "material": "(name, hex_colour, roughness=0.9)",
    "box_bm": "(size_mm)",
    "sphere_bm": "(radius_mm, segments=32, rings=24)",
    "cylinder_bm": "(radius_mm, depth_mm, segments=32, cap_tris=False)",
    "add": "(name, bm, at_mm=(0, 0, 0), mat=None, smooth=False)",
    "bake_transform": "(obj)",
}


def signatures(module):
    """{public name: its parameters as written} for what `lib/<module>.py`
    offers: the functions it defines, and those it imports from a sibling and
    hands on under the same name — `kit.mm` is `units.mm`. A constant maps to
    None."""
    tree = ast.parse((ROOT / "lib" / f"{module}.py").read_text(encoding="utf-8"))
    found = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            found[node.name] = f"({ast.unparse(node.args)})"
        elif isinstance(node, ast.Assign):
            found.update({t.id: None for t in node.targets if isinstance(t, ast.Name)})
        elif isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            theirs = signatures(node.module)
            found.update({a.asname or a.name: theirs.get(a.name) for a in node.names})
    return found


class KitInterfaceTest(unittest.TestCase):
    def test_every_name_a_build_calls_is_still_there_as_promised(self):
        found = signatures("kit")
        for name, params in PROMISED.items():
            self.assertIn(name, found, f"kit.{name} is gone, and every space that "
                                       f"calls it breaks at its next build")
            self.assertEqual(found[name], params,
                             f"kit.{name}{params} is now kit.{name}{found[name]} — "
                             f"every space's build.py is written against the first")

    def test_the_constant_a_build_may_scale_by_is_there(self):
        self.assertIn("MM", signatures("kit"))

    def test_a_build_in_the_toolkit_calls_only_what_is_promised(self):
        """The fixture's builds are the only callers this repository can see,
        and none may lean on anything the table does not name."""
        callers = sorted(ROOT.glob("fixtures/*/build.py"))
        self.assertTrue(callers)
        for got in callers:
            for node in ast.walk(ast.parse(got.read_text(encoding="utf-8"))):
                if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                        and node.value.id == "kit"):
                    self.assertIn(node.attr, {*PROMISED, "MM"},
                                  f"{got.relative_to(ROOT)} calls kit.{node.attr}")


if __name__ == "__main__":
    unittest.main()
