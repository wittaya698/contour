"""`lib/` has two halves, and the Blender-free one stays importable on a bare
clone (ADR 0019, decision 32).

The split is a decision, not an inference: `cmd_api.py` imports nothing but
`importlib` and `inspect` yet exists to resolve `bpy.*` symbols inside Blender,
and `entry.py` is stdlib-only but is the module Blender runs. So the halves are
named here, and a module in neither is a finding.

The check imports each free module in a fresh interpreter and looks at what
arrived with it. That is the thing that actually breaks — a bare clone where
`./contour` must work with nothing installed — and it sees reach the imports
do not show: `cmd_export` has no `bpy` line of its own, only `ctx_override`,
which has one.
"""
import ast
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROBE = """
import sys
before = set(sys.modules)
import lib.%s
print(" ".join(sorted({n.split(".")[0] for n in set(sys.modules) - before}
                      - {"lib"} - sys.stdlib_module_names)))
"""


# Runs outside Blender: the launcher, the canvas, the stores. Standard library
# only, because `./contour` has to work on a clone with nothing installed.
FREE = ("agent", "badges", "canvas", "checks", "cli", "commands", "connector", "delete", "enter", "exported",
        "filmstrip", "gate", "git", "glb", "intent", "lobby", "lock", "marks", "mask", "miniyaml",
        "ops_whitelist", "page", "panel", "policy", "presence", "refs",
        "rename", "restore", "revision", "signals", "space", "span", "spend", "store",
        "units", "verdict", "vetoes", "views", "worksheet")

# Runs inside Blender, and may import anything in FREE — the ban is one way.
# Two of these are here by role rather than by their imports: `entry` is
# stdlib-only but is the module Blender runs, and `cmd_api` imports only
# `importlib` and `inspect` yet exists to resolve `bpy.*` symbols.
BLENDER = ("cmd_api", "cmd_build", "cmd_export", "cmd_filmstrip",
           "cmd_measure", "cmd_render",
           "cmd_resolve", "cmd_roundtrip", "cmd_worksheet", "ctx_override",
           "entry", "kit", "measure", "mutants", "pose", "scene", "worksheet_draw")


def declared(path):
    """Every top-level package name this file's import statements name.

    Reading beats running for one case: an import inside a function body never
    happens when the module is imported, so the probe below sees nothing and
    the missing package surfaces as a crash in the field instead. Relative
    imports and `lib` itself are somebody else's question — the roster's.
    """
    names = []
    for node in ast.walk(ast.parse(Path(path).read_text())):
        if isinstance(node, ast.Import):
            names += [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            names.append(node.module.split(".")[0])
    return [n for n in names if n != "lib" and n not in sys.stdlib_module_names]


def leans_on(path):
    """The siblings in `lib/` this file imports, however it spells it.

    Reading again rather than running, because the half a module belongs to is
    a decision and not every member of the Blender half imports bpy: `entry`
    is stdlib-only and merely happens to be what Blender runs. Leaning on one
    of those imports cleanly, so only the source says it happened.
    """
    names = []
    for node in ast.walk(ast.parse(Path(path).read_text())):
        if isinstance(node, ast.Import):
            names += [a.name.split(".")[1] for a in node.names
                      if a.name.startswith("lib.")]
        elif isinstance(node, ast.ImportFrom):
            inside = node.level or (node.module or "").split(".")[0] == "lib"
            if not inside:
                continue
            within = (node.module or "").removeprefix("lib").lstrip(".")
            names += [within.split(".")[0]] if within \
                else [a.name for a in node.names]
    return names


def route(stderr, name):
    """Which siblings the failed import went through, from the traceback.

    A module in the free half rarely reaches Blender itself; it reaches a
    module that does. Without the route the finding names one file and leaves
    the reader to work out which of its imports was the one.
    """
    seen, chain = {f"lib/{name}.py"}, []
    for got in re.findall(r"lib[/\\](\w+)\.py", stderr):
        if f"lib/{got}.py" not in seen:
            seen.add(f"lib/{got}.py")
            chain.append(f"lib/{got}.py")
    return f" (through {' -> '.join(chain)})" if chain else ""


def offences(root, free, blender):
    """Every way this tree breaks the split, in lines a reader can act on.

    `root` is the directory holding `lib/`, so a test can point this at a
    fabricated tree and a real check can point it at the toolkit.
    """
    found, condemned = [], set()
    # `__init__.py` is in neither list and needs no assignment: every probe
    # below imports it on the way to its module, so it is already covered.
    for got in sorted((Path(root) / "lib").glob("*.py")):
        if got.stem not in (*free, *blender, "__init__"):
            found.append(f"lib/{got.name} is in neither half — add it to FREE "
                         f"if it runs outside Blender, BLENDER if it needs bpy")
    for name in free:
        r = subprocess.run([sys.executable, "-c", PROBE % name],
                           cwd=str(root), capture_output=True, text=True)
        if r.returncode != 0:
            found.append(f"lib/{name}.py does not import outside Blender"
                         + route(r.stderr, name) + ": "
                         + r.stderr.strip().splitlines()[-1])
            condemned.add(name)
            continue
        for got in r.stdout.split():
            found.append(f"lib/{name}.py is Blender-free but imports {got}, "
                         f"which is not in the standard library")
            condemned.add(name)
    for name in free:
        if name in condemned:
            continue                  # already named, with the route it took
        src = Path(root) / "lib" / f"{name}.py"
        for got in declared(src):
            found.append(f"lib/{name}.py names {got} in an import statement "
                         f"that does not run until it is called, and {got} is "
                         f"not in the standard library")
        for got in leans_on(src):
            if got in blender:
                found.append(f"lib/{name}.py is Blender-free but imports "
                             f"lib/{got}.py, which is in the Blender half — "
                             f"the ban runs one way and this is that way")
    return found


def above_lib(root, blender, *globs):
    """Every way a file that is not in `lib/` reaches the Blender half.

    Read rather than run, and that is the whole point: the console may import
    anything it likes from its environment, so a probe would need that
    environment to exist and the check has to work on a bare clone. What is
    being asked is narrower than the free half's question — not *is this
    stdlib-only* but *does this pull Blender into the process that spawns it*.
    """
    found = []
    for got in sorted(p for g in globs for p in Path(root).glob(g)):
        rel = got.relative_to(root)
        for name in leans_on(got):
            if name in blender:
                found.append(f"{rel} imports lib/{name}.py, which is in the "
                             f"Blender half — the console spawns Blender and "
                             f"must never contain it")
    return found


def into_console(root, *globs):
    """Every way a file the launcher runs reaches up into the console.

    The mirror of `above_lib`, and the same boundary read from the other side:
    the console imports `lib/`'s Blender-free half, and nothing the launcher runs
    may import the console back. Two things rest on it. `./contour` has to work
    on a clone with nothing installed, and `console/` is the one directory
    allowed a dependency — so a single import upwards would make the launcher
    need an environment to run. And the veto store's only door lives up there on
    purpose (ADR 0019, decision 27): a veto is written by the user at a gate and
    by nobody else, which stays true structurally for as long as this line holds.

    Read rather than run, for `above_lib`'s reason: the check has to work where
    the console's environment does not exist.
    """
    found = []
    for got in sorted(p for g in globs for p in Path(root).glob(g)):
        if "console" in declared(got):
            found.append(f"{got.relative_to(root)} imports the console, which "
                         f"nothing the launcher runs may do — `./contour` works "
                         f"on a bare clone, and the console's store of vetoes has "
                         f"one writer because it is only reachable from up there")
    return found


def untested(root, free):
    """Every module in the free half that no test file imports (issue 26).

    The free half is the half a pure test *can* reach, so a module in it with
    no test on its interface is an oversight nothing else will name. This file
    does not count: it imports each module only to see what arrives, which
    proves it loads and nothing about what it does. Not a coverage threshold,
    since a coverage tool is a dependency and having none is what the roster
    above protects.
    """
    tested = {name for got in Path(root).glob("tests/test_*.py")
              if got.name != Path(__file__).name for name in leans_on(got)}
    return [f"lib/{name}.py is in the free half and no test imports it — "
            f"give it a tests/test_*.py that exercises its interface"
            for name in free if name not in tested]


class LibSplitTest(unittest.TestCase):
    def fabricate(self, **modules):
        """A throwaway tree shaped like the toolkit: a `lib/` package holding
        the named modules, and room beside it for a package to be found."""
        tree = Path(tempfile.mkdtemp())
        (tree / "lib").mkdir()
        (tree / "lib" / "__init__.py").write_text("")
        for name, body in modules.items():
            (tree / "lib" / f"{name}.py").write_text(body)
        return tree

    def test_a_blender_free_module_that_reaches_a_pip_package_is_named(self):
        """The one that breaks a bare clone: one installed import in the free
        half and `./contour` needs an environment before it can run at all."""
        tree = self.fabricate(reader="import json\nimport shipwright\n")
        (tree / "shipwright").mkdir()
        (tree / "shipwright" / "__init__.py").write_text("")
        said = " ".join(offences(tree, ["reader"], []))
        self.assertIn("lib/reader.py", said)
        self.assertIn("shipwright", said)

    def test_a_blender_free_module_that_reaches_bpy_is_named_with_the_route(self):
        """Reach, not lines: `cmd_export` has no `bpy` of its own, only
        `ctx_override`, which has one. A finding that says the free module
        failed and nothing else leaves twelve siblings to hunt through, so it
        names the module in the free half *and* the one that pulled Blender in.
        """
        tree = self.fabricate(shape="from . import turner\n",
                              turner="import bpy\n")
        said = " ".join(offences(tree, ["shape"], ["turner"]))
        self.assertIn("lib/shape.py", said)
        self.assertIn("lib/turner.py", said)
        self.assertIn("bpy", said)

    def test_a_blender_free_module_that_imports_bpy_outright_is_named(self):
        """The ban is one way: a Blender-half module may import a free one,
        and this is the direction that is not allowed. Covered by the same
        code path as the transitive case above, kept because it is the
        property, not a consequence of one."""
        tree = self.fabricate(shape="import bpy\n")
        said = " ".join(offences(tree, ["shape"], []))
        self.assertIn("lib/shape.py", said)
        self.assertIn("bpy", said)

    def test_a_free_module_leaning_on_a_blender_half_sibling_is_named(self):
        """Not every Blender-half module imports bpy — `entry` is stdlib-only
        and is simply the module Blender runs. A free module importing one of
        those imports cleanly and would pass a check that only watches what
        arrives, while the one-way ban has already been broken. It is the two
        modules inference gets wrong that can slip through here."""
        tree = self.fabricate(shape="from . import turner\n",
                              turner="import json\n")
        said = " ".join(offences(tree, ["shape"], ["turner"]))
        self.assertIn("lib/shape.py", said)
        self.assertIn("turner", said)

    def test_a_new_module_belongs_to_a_half_or_the_check_says_so(self):
        """The roster is the decision, so it has to be complete. A module
        nobody assigned is unchecked, and unchecked is where the pip import
        gets in."""
        tree = self.fabricate(shape="import json\n", turner="import bpy\n",
                              newcomer="import json\n")
        said = " ".join(offences(tree, ["shape"], ["turner"]))
        self.assertIn("lib/newcomer.py", said)

    def test_a_console_module_reaching_the_blender_half_is_named(self):
        """The console reads state by importing `lib/`'s free half. Reaching
        into the other half would put Blender inside the process whose whole job
        is to spawn it — and it would import cleanly right up until it ran."""
        tree = self.fabricate(turner="import bpy\n")
        (tree / "console").mkdir()
        (tree / "console" / "server.py").write_text("from lib import turner\n")
        said = " ".join(above_lib(tree, ["turner"], "console/*.py"))
        self.assertIn("console/server.py", said)
        self.assertIn("lib/turner.py", said)

    def test_a_launcher_module_that_imports_the_console_is_named(self):
        """The direction that is not allowed, and the one that makes a rule into
        a mechanism: a store whose only door is in `console/` cannot be written
        by a subcommand unless somebody first reaches up for it."""
        tree = self.fabricate(marks="from console import vetoes\n")
        (tree / "console").mkdir()
        (tree / "console" / "vetoes.py").write_text("")
        said = " ".join(into_console(tree, "lib/*.py"))
        self.assertIn("lib/marks.py", said)
        self.assertIn("console", said)

    def test_the_toolkit_keeps_its_own_split(self):
        """The live check, and the reason this file is in `tests/`: selftest
        runs the unit tests before it starts Blender, so a violation surfaces
        in the command that proves a bare clone works, at no Blender cost."""
        self.assertEqual(offences(ROOT, FREE, BLENDER), [])

    def test_nothing_the_launcher_runs_imports_the_console(self):
        """The live check on the other direction. `contour` and `verify.py` are
        in it because they are the two files a bare clone runs, and `lib/*.py`
        because that is everything they reach. The launcher's code is
        `lib/cli.py` now and `contour` a shim that calls it (issue 24), so the
        file that matters most here is named on its own: a glob that stopped
        matching it would pass by checking nothing."""
        self.assertTrue(list(ROOT.glob("lib/cli*.py")))
        self.assertEqual(into_console(ROOT, "lib/cli*.py", "lib/*.py", "contour",
                                      "verify.py"), [])

    def test_the_console_and_its_shim_keep_out_of_the_blender_half(self):
        """The live check on the layer above the launcher (ADR 0019, decision
        32). `contour-console` is in it because it is the file a bare clone runs
        to be told it needs an environment, and a Blender import there would
        break the one message that has to survive having nothing installed."""
        self.assertEqual(above_lib(ROOT, BLENDER, "console/*.py",
                                   "contour-console"), [])

    def test_a_free_module_no_test_imports_is_named(self):
        """The gap issue 26 closed, kept closed: a new Blender-free module
        arrives without a test and is a finding rather than an oversight."""
        tree = self.fabricate(shape="import json\n", reader="import json\n")
        (tree / "tests").mkdir()
        (tree / "tests" / "test_shape.py").write_text("from lib import shape\n")
        said = untested(tree, ["shape", "reader"])
        self.assertEqual(len(said), 1)
        self.assertIn("lib/reader.py", said[0])

    def test_a_helper_beside_the_tests_is_not_a_test(self):
        """`tests/client.py` imports the canvas to drive it; that is a helper
        the tests share, and a module only it reaches is still untested."""
        tree = self.fabricate(shape="import json\n")
        (tree / "tests").mkdir()
        (tree / "tests" / "client.py").write_text("from lib import shape\n")
        self.assertIn("lib/shape.py", " ".join(untested(tree, ["shape"])))

    def test_every_free_module_has_a_test(self):
        """The live check: everything in the free half is imported by a test."""
        self.assertEqual(untested(ROOT, FREE), [])

    def test_a_pip_import_hidden_in_a_function_body_is_found(self):
        """Importing the module cannot see this one: the statement never runs
        until somebody calls the function, and by then it is a crash in the
        field rather than a finding here."""
        tree = self.fabricate(
            reader="import json\n\n\ndef fetch():\n    import shipwright\n")
        said = " ".join(offences(tree, ["reader"], []))
        self.assertIn("lib/reader.py", said)
        self.assertIn("shipwright", said)


if __name__ == "__main__":
    unittest.main()
