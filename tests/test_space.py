"""Where a space keeps its files, asked of the space (slice 17, ADR 0015).

The layout was already written down once, in `lib/paths.py:resolve` — and was
unusable outside the Blender process, because the module read `$CONTOUR_PROJECT`
into a global at import. So the launcher and the console re-derived it by hand:
`out/<name>.blend` in five places, `marks.json` in nine. These tests ask the
layout the questions those copies were answering, which is what makes deleting
them safe.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lib import space


class LayoutTest(unittest.TestCase):
    """The two layouts. A space and the fixture disagree about where a
    deliverable goes, and that disagreement is the whole reason there are two."""

    def test_a_space_keeps_its_marks_at_its_root_and_the_fixture_under_out(self):
        here = space.layout(Path("/spaces/beaky"))
        smoke = space.fixture("smoke", Path("/toolkit"))
        self.assertEqual(here.marks, Path("/spaces/beaky/marks.json"))
        self.assertEqual(smoke.marks, Path("/toolkit/fixtures/smoke/out/marks.json"))

    def test_only_the_fixture_knows_itself_to_be_one(self):
        # `mutants` breaks the build on purpose and must run nowhere else.
        # Derived from where the layout sits rather than remembered from a flag
        # the constructor took, so there is no way to build a space layout that
        # claims to be the fixture.
        self.assertTrue(space.fixture("smoke", Path("/toolkit")).fixture)
        self.assertFalse(space.layout(Path("/spaces/beaky"),
                                      toolkit=Path("/toolkit")).fixture)
        self.assertFalse(space.layout(Path("/toolkit/fixtures/smoke")).fixture)
        # A space of the user's that happens to live in a directory called
        # `fixtures` is still a space: it is the toolkit's own that counts.
        self.assertFalse(space.layout(Path("/work/fixtures/beaky"),
                                      toolkit=Path("/toolkit")).fixture)

    def test_a_build_is_named_after_the_space_it_is_of(self):
        self.assertEqual(space.layout(Path("/spaces/beaky")).blend,
                         Path("/spaces/beaky/out/beaky.blend"))
        self.assertEqual(space.fixture("smoke", Path("/toolkit")).blend,
                         Path("/toolkit/fixtures/smoke/out/smoke.blend"))

    def test_what_a_space_ships_is_tracked_and_the_fixture_ships_nothing(self):
        # The one real difference between the layouts: a space's sheet and its
        # export are deliverables, so they sit where git can see them. Nothing
        # about the fixture is, so its two land in `out/` and the selftest
        # cannot dirty a tracked file by running.
        here = space.layout(Path("/spaces/beaky"))
        smoke = space.fixture("smoke", Path("/toolkit"))
        self.assertEqual(here.sheet, Path("/spaces/beaky/sheet.png"))
        self.assertEqual(here.glb, Path("/spaces/beaky/exports/beaky.glb"))
        self.assertEqual(smoke.sheet, Path("/toolkit/fixtures/smoke/out/sheet.png"))
        self.assertEqual(smoke.glb, Path("/toolkit/fixtures/smoke/out/smoke.glb"))

    def test_the_rest_of_the_table_is_the_same_in_both_and_reached_by_name(self):
        # The paths the two layouts agree about, asserted once because moving a
        # table is where a table gets a typo — and reached by attribute, which
        # is the point of a tuple: `P.parts` misspelled is an AttributeError
        # here, where `P["parts"]` misspelled was a KeyError somewhere later.
        here = space.layout(Path("/spaces/beaky"))
        self.assertEqual(here.spec, Path("/spaces/beaky/spec.yaml"))
        self.assertEqual(here.build, Path("/spaces/beaky/build.py"))
        self.assertEqual(here.refs, Path("/spaces/beaky/refs"))
        self.assertEqual(here.out, Path("/spaces/beaky/out"))
        self.assertEqual(here.dot, Path("/spaces/beaky/.contour"))
        self.assertEqual(here.mask, Path("/spaces/beaky/out/mask.png"))
        self.assertEqual(here.parts, Path("/spaces/beaky/out/parts.json"))
        self.assertEqual(here.views, Path("/spaces/beaky/out/views.json"))
        self.assertEqual(here.filmstrip, Path("/spaces/beaky/out/filmstrip.png"))
        self.assertEqual(here.release, Path("/spaces/beaky/release"))
        smoke = space.fixture("smoke", Path("/toolkit"))
        for field in ("spec", "build", "refs", "dot", "mask", "parts", "views",
                      "filmstrip", "release"):
            rel = getattr(here, field).relative_to(here.root)
            self.assertEqual(getattr(smoke, field), smoke.root / rel, field)


class FindTest(unittest.TestCase):
    """Walking up for the marker, the way git walks up for `.git`."""

    def setUp(self):
        # Resolved, because `find` resolves and macOS /var is a symlink.
        self.here = Path(tempfile.mkdtemp()).resolve()
        self.root = self.here / "beaky"
        (self.root / space.MARKER.parent).mkdir(parents=True)
        (self.root / space.MARKER).write_text("toolkit: abc123\n")

    def test_a_space_is_found_from_anywhere_inside_it(self):
        deep = self.root / "refs" / "side"
        deep.mkdir(parents=True)
        self.assertEqual(space.find(deep), self.root)
        self.assertEqual(space.find(self.root), self.root)

    def test_a_directory_with_no_marker_above_it_is_no_space(self):
        # Not an error and not a guess: `contour spaces` runs outside one, and
        # the answer *you are not standing in a model space* is what `contour
        # check` refuses on.
        self.assertIsNone(space.find(self.here))

    def test_a_contour_directory_alone_is_not_a_space(self):
        # The toolkit has a `.contour/` of its own, for its logs. If the
        # directory were the marker, every command run inside the toolkit would
        # decide it was standing in a model space — which is the one thing the
        # walk-up exists to rule out.
        (self.here / ".contour").mkdir()
        self.assertIsNone(space.find(self.here))


class DisplayTest(unittest.TestCase):
    """A path as a report should read it: relative to whichever root owns it.

    Every line a stage prints names a file, and an absolute path is both longer
    and less use than `out/beaky.blend` — the reader is standing in the space.
    """

    def test_a_space_path_reads_relative_to_the_space(self):
        here = space.layout(Path("/spaces/beaky"), toolkit=Path("/toolkit"))
        self.assertEqual(here.display(here.blend), "out/beaky.blend")

    def test_a_fixture_path_reads_relative_to_the_toolkit_that_holds_it(self):
        # Which fixture is the part worth printing: `out/smoke.blend` could be
        # any space's build, and the selftest is the one caller that is not
        # standing in the thing it is talking about.
        smoke = space.fixture("smoke", Path("/toolkit"))
        self.assertEqual(smoke.display(smoke.blend),
                         "fixtures/smoke/out/smoke.blend")

    def test_a_path_under_neither_root_is_shown_whole(self):
        here = space.layout(Path("/spaces/beaky"), toolkit=Path("/toolkit"))
        self.assertEqual(here.display(Path("/etc/hosts")), "/etc/hosts")


class ParseTest(unittest.TestCase):
    """Argv picks a layout, on the Blender side.

    The launcher tells the process which space it was started for, so this is
    the one function that reads the environment — and it reads it when it is
    called, not when the module is imported, which is what made the layout
    unaskable from the launcher and the console in the first place.
    """

    def setUp(self):
        self.space = Path(tempfile.mkdtemp()).resolve() / "beaky"
        self.toolkit = Path(tempfile.mkdtemp()).resolve()
        env = mock.patch.dict(os.environ, {"CONTOUR_ROOT": str(self.toolkit),
                                           "CONTOUR_PROJECT": str(self.space)})
        env.start()
        self.addCleanup(env.stop)

    def test_the_fixture_is_named_and_a_model_space_is_stood_in(self):
        # The one asymmetry ADR 0015 leaves: the selftest has no space to stand
        # in, so it addresses the fixture by name. Everything else is *here*.
        self.assertEqual(space.parse(["smoke", "--fixture"]).blend,
                         self.toolkit / "fixtures" / "smoke" / "out" / "smoke.blend")
        self.assertEqual(space.parse([]).blend, self.space / "out" / "beaky.blend")

    def test_naming_a_model_on_the_command_line_is_refused(self):
        with self.assertRaises(SystemExit) as caught:
            space.parse(["beaky"])
        self.assertIn("cd into the model space", str(caught.exception))
        with self.assertRaises(SystemExit):
            space.parse(["smoke", "beaky", "--fixture"])

    def test_outside_a_space_there_is_no_layout_to_fall_back_to(self):
        # `PROJECT or ROOT` used to answer here, which made the toolkit's own
        # directory readable as a model space — the one thing the walk-up
        # exists to prevent. Refusing is the answer.
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ["CONTOUR_ROOT"] = str(self.toolkit)
            with self.assertRaises(SystemExit) as caught:
                space.parse([])
        self.assertIn("not in a model space", str(caught.exception))


class WalkTest(unittest.TestCase):
    """Where spaces are, which lived in the launcher and so was unreachable
    from `contour-console` — the half of this that made *what a space is* and
    *where spaces are* two different modules' business."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()

    def make(self, *parts):
        here = self.root.joinpath(*parts)
        (here / space.MARKER.parent).mkdir(parents=True)
        (here / space.MARKER).write_text("toolkit: abc123\n")
        return here

    def test_a_space_is_found_by_its_marker_under_a_root(self):
        beaky = self.make("beaky")
        (self.root / "notes").mkdir()
        self.assertEqual(space.spaces([self.root]), [beaky])

    def test_the_walk_stops_at_a_space_and_stops_at_the_depth_bound(self):
        # Spaces do not nest, so `out/` and `refs/` of a found space are not
        # walked — and a root that is somebody's home directory has to come
        # back in a usable time, which is the whole reason for the bound.
        beaky = self.make("beaky")
        self.make("beaky", "out")             # a marker copied into out/ by a build
        deep = self.make("a", "b", "c", "d", "e", "buried")
        self.assertEqual(space.spaces([self.root]), [beaky])
        self.assertIn(deep, space.spaces([self.root], depth=9))

    def test_where_to_look_is_the_toolkits_neighbourhood_unless_told_otherwise(self):
        # Where to look, not what exists — so unlike a registry it cannot go
        # stale, and a space moved within a root is still found (ADR 0015).
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(space.roots(Path("/opt/contour")), [Path("/opt")])
            os.environ["CONTOUR_SPACES"] = "/work/models:/archive"
            self.assertEqual(space.roots(Path("/opt/contour")),
                             [Path("/work/models"), Path("/archive")])
