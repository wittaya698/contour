"""Rule 4 over the toolkit's own code: the whitelist is the only door to `bpy.ops`.

`lib/ops_whitelist.py` names the operators this repository may call, and
`lib/ctx_override.py` refuses the rest when it is asked. Neither can see a call
that goes around it, and neither is exercised until Blender runs. So this reads
the source: every operator the toolkit asks for is on the list, nothing but
`ctx_override` touches `bpy.ops` at all, and every entry says why it exists
(ADR 0004).
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.ops_whitelist import ALLOWED  # noqa: E402


def sources():
    """What this repository runs inside Blender: `lib/` and the fixtures' builds."""
    return sorted([*ROOT.glob("lib/*.py"), *ROOT.glob("fixtures/*/build.py")])


def asked_for(tree):
    """Every operator named in a `ctx_override.call("...")`, with its line."""
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "call"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "ctx_override"):
            first = node.args[0] if node.args else None
            yield node.lineno, first.value if isinstance(first, ast.Constant) else None


def reaches_ops(tree):
    """Every line that spells `bpy.ops`, however it is imported."""
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and node.attr == "ops"
                and isinstance(node.value, ast.Name) and node.value.id == "bpy"):
            yield node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module == "bpy" and any(
                a.name == "ops" for a in node.names):
            yield node.lineno
        elif isinstance(node, ast.Import) and any(a.name == "bpy.ops" for a in node.names):
            yield node.lineno


class OpsWhitelistTest(unittest.TestCase):
    def test_every_operator_the_toolkit_asks_for_is_on_the_list(self):
        seen = 0
        for got in sources():
            for line, op in asked_for(ast.parse(got.read_text(encoding="utf-8"))):
                seen += 1
                where = f"{got.relative_to(ROOT)}:{line}"
                self.assertIsNotNone(op, f"{where} asks for an operator by a name "
                                         f"that is not written down, so no list can hold it")
                self.assertIn(op, ALLOWED, f"{where} asks for bpy.ops.{op}")
        self.assertTrue(seen, "no ctx_override.call found — the reader has gone blind")

    def test_nothing_but_ctx_override_touches_bpy_ops(self):
        for got in sources():
            if got.name == "ctx_override.py":
                continue
            lines = list(reaches_ops(ast.parse(got.read_text(encoding="utf-8"))))
            self.assertEqual(lines, [], f"{got.relative_to(ROOT)} reaches bpy.ops "
                                        f"directly; go through lib.ctx_override.call")

    def test_the_reader_sees_every_way_of_spelling_it(self):
        """The check above is only as good as this: each spelling is caught."""
        for src in ("import bpy\nbpy.ops.mesh.primitive_cube_add()\n",
                    "from bpy import ops\n", "import bpy.ops\n"):
            self.assertTrue(list(reaches_ops(ast.parse(src))), src)

    def test_every_entry_is_an_operator_with_no_data_api_equivalent(self):
        """The one ground ADR 0004 gives for a line here, said on the line."""
        for op, why in ALLOWED.items():
            self.assertRegex(op, r"^\w+\.\w+$")
            self.assertIn("no data-API equivalent", why,
                          f"bpy.ops.{op} is allowed without saying why: {why!r}")


if __name__ == "__main__":
    unittest.main()
