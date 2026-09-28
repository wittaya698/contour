"""The mark store, and the one line `contour check` prints about it."""
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import marks

ROOT = Path(__file__).resolve().parent.parent


class StatusLineTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "marks.json"

    def write(self, *statuses):
        marks.save(self.path, [{"id": f"m{i}", "status": s}
                               for i, s in enumerate(statuses, 1)])

    def test_silent_when_there_is_no_file(self):
        self.assertIsNone(marks.status_line(self.path))

    def test_silent_when_nothing_is_open(self):
        self.write("closed", "closed")
        self.assertIsNone(marks.status_line(self.path))

    def test_counts_only_the_open_ones(self):
        self.write("open", "closed", "open")
        self.assertEqual(marks.status_line(self.path), "2 marks open")

    def test_says_mark_not_marks_when_there_is_one(self):
        self.write("open")
        self.assertEqual(marks.status_line(self.path), "1 mark open")


class BirthTest(unittest.TestCase):
    """The three ways a mark comes into being (ADR 0018)."""

    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "marks.json"

    def test_a_sheet_mark_carries_the_view_it_was_placed_on(self):
        """A click on one of our four views. The view is part of where it is:
        `too thin` on the front and `too thin` on the side are two findings."""
        born = marks.on_sheet(self.path, "front", [412, 208], "beak sits too low",
                              part="beak")
        self.assertEqual(marks.view(born), "front")
        self.assertEqual(marks.pixel(born), [412, 208])
        self.assertEqual(marks.part(born), "beak")
        self.assertEqual(marks.text(born), "beak sits too low")
        self.assertTrue(marks.is_open(born))

    def test_a_ref_mark_carries_the_photograph_and_no_part(self):
        """A photograph knows nothing about parts and was drawn by no view of
        ours, so the image is the whole of where it is (ADR 0018)."""
        born = marks.on_reference(self.path, "persp.webp", [880, 410],
                                  "the gap between the legs is what I meant")
        self.assertEqual(marks.reference(born), "persp.webp")
        self.assertEqual(marks.pixel(born), [880, 410])
        self.assertIsNone(marks.view(born))
        self.assertEqual(marks.part(born), "")

    def test_a_span_is_a_ref_mark_with_two_ends(self):
        """*This distance, right here* — the only shape that can aim
        `contour measure` at a separation."""
        span = marks.on_reference(self.path, "persp.webp", [412, 690],
                                  "what separates the legs", to=[498, 690])
        self.assertEqual(marks.span_end(span), [498, 690])
        plain = marks.on_reference(self.path, "persp.webp", [880, 410], "just here")
        self.assertIsNone(marks.span_end(plain))

    def test_an_agent_mark_names_a_part_and_no_point_on_it(self):
        """The agent never clicked, so it has no pixel to offer and no ray to
        have cast. It knows *which part* it has a question about, from the same
        tables verification reads, and lets the render decide where the badge
        goes (ADR 0018)."""
        born = marks.on_part(self.path, "neck", "12 mm gap to torso")
        self.assertEqual(marks.part(born), "neck")
        self.assertIsNone(marks.pixel(born))
        self.assertIsNone(marks.pin(born))
        self.assertEqual(born["author"], "agent")

    def test_an_agent_mark_names_its_part_at_the_top_level(self):
        """One place a part name lives, and `anchor` is not it. A **pin** is a
        position in the hit part's own coordinates, and a part's name is not a
        position — so they stop sharing a key (slice 19). This mark has no pin
        at all, and now says so by carrying no anchor."""
        born = marks.on_part(self.path, "neck", "12 mm gap to torso")
        self.assertEqual(born["part"], "neck")
        self.assertNotIn("anchor", born)

    def test_a_promoted_veto_says_which_moment_it_came_from(self):
        """A veto becomes a question about a part, and the author is the user:
        they wrote the sentence. A reader following it backwards has to land on
        the refusal it came from (ADR 0019, decision 15)."""
        born = marks.on_part(self.path, "neck", "not this", author="user",
                             came_from="v1")
        self.assertEqual(born["author"], "user")
        self.assertEqual(born["from"], "v1")


class TransitionTest(unittest.TestCase):
    """Every state change ADR 0018 defines, named and owned here."""

    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "marks.json"

    def on_disk(self, mark_id):
        return next(m for m in marks.load(self.path) if m["id"] == mark_id)

    def test_anchoring_spends_the_pixel_and_keeps_the_pin(self):
        """A mark is born unresolved and carries a pixel; once a ray has landed
        it carries a point in the hit part\'s own coordinates instead. The pixel
        goes, so no mark ever carries two answers to the same question."""
        born = marks.on_sheet(self.path, "front", [412, 208], "cap too round")
        done = marks.anchor(self.path, {born["id"]: {"part": "cap",
                                                     "local": [0.0, 0.0, 0.03]}})
        self.assertEqual(done, [born["id"]])
        now = self.on_disk(born["id"])
        self.assertEqual(marks.pin(now), [0.0, 0.0, 0.03])
        self.assertEqual(marks.part(now), "cap")
        self.assertIsNone(marks.pixel(now))

    def test_a_landed_ray_names_its_part_beside_the_pin_and_not_inside_it(self):
        """What the ray found is two answers, and they are stored as two: which
        part it hit, at the top level where every part name lives, and where on
        that part it landed, which is the anchor and the whole of it (slice 19).
        """
        born = marks.on_sheet(self.path, "front", [412, 208], "cap too round")
        marks.anchor(self.path, {born["id"]: {"part": "cap",
                                              "local": [0.0, 0.0, 0.03]}})
        now = self.on_disk(born["id"])
        self.assertEqual(now["part"], "cap")
        self.assertEqual(now["anchor"], {"local": [0.0, 0.0, 0.03]})

    def test_a_mark_on_a_photograph_is_never_anchored(self):
        """A photograph has no parts to be anchored in, and no build of ours
        casts a ray into one (ADR 0018)."""
        born = marks.on_reference(self.path, "persp.webp", [880, 410], "here")
        done = marks.anchor(self.path, {born["id"]: {"part": "cap",
                                                     "local": [0.0, 0.0, 0.03]}})
        self.assertEqual(done, [])
        self.assertEqual(marks.pixel(self.on_disk(born["id"])), [880, 410])

    def test_a_pin_whose_part_went_is_said_to_be_homeless(self):
        """Deleting a part does not answer the question asked about it, so the
        pin is said to be orphaned rather than re-projected onto whatever
        happens to be nearest (ADR 0018)."""
        born = marks.on_sheet(self.path, "front", [412, 208], "cap too round")
        marks.anchor(self.path, {born["id"]: {"part": "cap", "local": [0, 0, 0]}})
        gone = marks.orphan(self.path, {"torso"})
        self.assertEqual(gone, [born["id"]])
        self.assertTrue(marks.orphaned(self.on_disk(born["id"])))

    def test_a_part_that_comes_back_takes_its_pins_back_with_it(self):
        """The flag is what the last build found, not a scar: a rename undone is
        a part back in `build.py`, and its pins point at it again."""
        born = marks.on_sheet(self.path, "front", [412, 208], "cap too round")
        marks.anchor(self.path, {born["id"]: {"part": "cap", "local": [0, 0, 0]}})
        marks.orphan(self.path, {"torso"})
        marks.orphan(self.path, {"torso", "cap"})
        self.assertFalse(marks.orphaned(self.on_disk(born["id"])))

    def test_a_mark_still_waiting_on_a_ray_is_not_orphaned(self):
        """The mask read a part under the click, but no ray has landed yet, so
        which part this turns out to be about is nobody\'s answer. Orphaning it
        would put *its part is not in the build* on a finding that has not been
        placed — and slice 19 converges the two spellings precisely so this
        distinction survives."""
        born = marks.on_sheet(self.path, "front", [412, 208], "cap too round",
                              part="cap")
        self.assertEqual(marks.orphan(self.path, {"torso"}), [])
        self.assertFalse(marks.orphaned(self.on_disk(born["id"])))

    def test_a_mark_that_already_has_a_pin_is_not_sent_for_another_ray(self):
        """A pixel and a pin at once is not a shape any birth makes, and it is
        the shape a half-finished write would leave. It already has its answer,
        and casting a second ray would overwrite the one that landed against the
        build the sheet was drawn from."""
        marks.save(self.path, [{"id": "m1", "status": "open", "pixel": [4, 4],
                                "anchor": {"part": "cap", "local": [0, 0, 0]}}])
        self.assertEqual(marks.unresolved(marks.load(self.path)), [])

    def test_a_mark_that_points_at_no_part_is_not_called_homeless(self):
        """`orphaned` means *the part this points at is gone*, so a record that
        points at no part has not been asked the question. Without this the
        empty name is compared against the build\'s list, matches nothing, and a
        mark about nothing in particular is reported as a part the build
        deleted."""
        marks.save(self.path, [{"id": "m1", "status": "open",
                                "text": "this gap is too wide"}])
        self.assertEqual(marks.orphan(self.path, {"torso"}), [])
        self.assertFalse(marks.orphaned(self.on_disk("m1")))

    def test_no_build_of_ours_orphans_a_mark_on_a_photograph(self):
        born = marks.on_reference(self.path, "persp.webp", [880, 410], "here")
        self.assertEqual(marks.orphan(self.path, set()), [])
        self.assertFalse(marks.orphaned(self.on_disk(born["id"])))

    def test_addressing_stamps_the_build_and_leaves_the_finding_standing(self):
        """The agent may say *I believe this build deals with it*. It dims the
        badge; it is not a close, because a finding is not disposed of by the
        party it is aimed at (ADR 0018)."""
        born = marks.on_part(self.path, "neck", "12 mm gap to torso")
        done = marks.address(self.path, born["id"], "a1b2c3d4e5f6")
        self.assertEqual(marks.addressed(done), "a1b2c3d4e5f6")
        self.assertTrue(marks.is_open(self.on_disk(born["id"])))

    def test_addressing_a_mark_that_is_not_on_file_says_so(self):
        """The page can be looking at a list the store no longer has."""
        self.assertIsNone(marks.address(self.path, "m9", "a1b2c3d4e5f6"))

    def test_only_the_marks_still_waiting_on_a_ray_are_unresolved(self):
        """A pixel and no pin yet. A ref mark is never among them: it points into
        a photograph, which has no parts and never gets rebuilt, so its pixel is
        the whole answer (ADR 0018)."""
        waiting = marks.on_sheet(self.path, "front", [412, 208], "cap too round")
        landed = marks.on_sheet(self.path, "front", [10, 10], "and this")
        marks.anchor(self.path, {landed["id"]: {"part": "cap", "local": [0, 0, 0]}})
        marks.on_reference(self.path, "persp.webp", [880, 410], "here")
        marks.on_part(self.path, "neck", "12 mm gap")
        todo = marks.unresolved(marks.load(self.path))
        self.assertEqual([m["id"] for m in todo], [waiting["id"]])


class SpellingTest(unittest.TestCase):
    """One spelling for a part, and the migration that gets a space there
    (slice 19).

    A mark that is about a part used to store that name in one of two places
    depending on how it was born — top level, or under the anchor beside the
    pin. Slice 18 hid that behind one accessor; this ends it, in the storage.
    Nothing here runs on load: `marks.json` is tracked, and it holds the user's
    own findings, so the rewrite is a state they choose and see (rule 5).
    """

    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "marks.json"

    def mixed(self):
        """A file as a space that has been marked on since before this slice
        actually holds it: both spellings, and records that are neither."""
        marks.save(self.path, [
            {"id": "m1", "status": "open", "text": "12 mm gap",
             "anchor": {"part": "neck"}},
            {"id": "m2", "status": "open", "text": "cap too round",
             "anchor": {"part": "cap", "local": [0.0, 0.0, 0.03]}},
            {"id": "m3", "status": "open", "text": "and this", "part": "torso",
             "anchor": {"local": [0.0, 0.1, 0.0]}},
            {"id": "m4", "status": "open", "text": "here", "ref": "persp.webp",
             "pixel": [880, 410]},
        ])

    def test_a_part_named_under_the_anchor_is_the_old_spelling(self):
        """Both of the old shapes and neither of the new ones: an agent mark
        whose anchor held a name and no pin, and a landed ray whose anchor held
        both."""
        self.mixed()
        found = marks.old_spelling(marks.load(self.path))
        self.assertEqual([m["id"] for m in found], ["m1", "m2"])


    def test_a_space_nobody_migrated_still_reads(self):
        """Which is the point of leaving the reader bilingual: a space may never
        be migrated at all, and until someone asks, every question about it has
        to answer the same in either spelling. Orphaning is asked here because
        it is the reader that *writes* on what it finds — a build that could not
        see an old pin's part would call it homeless and dim a finding that is
        perfectly well anchored."""
        self.mixed()
        by = {m["id"]: m for m in marks.load(self.path)}
        self.assertEqual(marks.part(by["m1"]), "neck")
        self.assertEqual(marks.part(by["m2"]), "cap")
        self.assertEqual(marks.pin(by["m2"]), [0.0, 0.0, 0.03])
        self.assertEqual(marks.orphan(self.path, {"neck", "cap", "torso"}), [])
        self.assertEqual(sorted(marks.orphan(self.path, {"torso"})), ["m1", "m2"])

    def test_migrating_moves_the_part_up_and_leaves_the_pin_where_it_is(self):
        """The name goes to the top level; what the ray found stays exactly
        where it was. An anchor that held nothing but the name goes altogether,
        rather than staying behind as an empty dict — that record never had a
        pin, and `{}` would be a third way of saying so."""
        self.mixed()
        self.assertEqual(marks.migrate(self.path), ["m1", "m2"])
        by = {m["id"]: m for m in marks.load(self.path)}
        self.assertEqual(by["m1"]["part"], "neck")
        self.assertNotIn("anchor", by["m1"])
        self.assertEqual(by["m2"]["part"], "cap")
        self.assertEqual(by["m2"]["anchor"], {"local": [0.0, 0.0, 0.03]})
        self.assertEqual(marks.old_spelling(marks.load(self.path)), [])

    def test_migrating_leaves_alone_what_it_was_not_asked_about(self):
        """A mark already in the new spelling, and one on a photograph that
        names no part at all. A migration that touched either would be a diff
        the user did not cause in a file git tracks."""
        self.mixed()
        before = {m["id"]: dict(m) for m in marks.load(self.path)}
        marks.migrate(self.path)
        by = {m["id"]: m for m in marks.load(self.path)}
        self.assertEqual(by["m3"], before["m3"])
        self.assertEqual(by["m4"], before["m4"])

    def test_a_migrated_name_lands_where_it_came_from(self):
        """`marks.json` is tracked and this is the one commit that rewrites it
        wholesale, so the diff has to be readable by the person reviewing it.
        The name takes the anchor's place in the record rather than being
        appended at the end, which puts the line that went and the line that
        arrived in the same hunk, next to each other."""
        self.mixed()
        was = {m["id"]: list(m) for m in marks.load(self.path)}
        marks.migrate(self.path)
        by = {m["id"]: list(m) for m in marks.load(self.path)}
        self.assertEqual(by["m2"].index("part") + 1, by["m2"].index("anchor"))
        self.assertEqual(by["m1"].index("part"), was["m1"].index("anchor"))

    def test_migrating_never_changes_which_part_a_mark_is_about(self):
        """A record can carry both spellings at once — the canvas wrote the
        mask's reading at the top level as the mark was born, and a ray later
        wrote the surface it actually hit under the anchor — and the two can
        disagree. Every reader since has answered with the top-level one, so
        that is the one the migration keeps.

        Deciding that the ray is the better answer may well be right, and it is
        not a decision a rewrite gets to make on the way past: it would change
        which part a finding is about, in a tracked file, in a commit whose
        subject says the spelling was converged.
        """
        marks.save(self.path, [{"id": "m1", "status": "open", "text": "x",
                                "part": "neck",
                                "anchor": {"part": "torso",
                                           "local": [0.0, 0.1, 0.0]}}])
        before = marks.part(marks.load(self.path)[0])
        self.assertEqual(marks.migrate(self.path), ["m1"])
        now = marks.load(self.path)[0]
        self.assertEqual(marks.part(now), before)
        self.assertEqual(now["part"], "neck")
        self.assertEqual(now["anchor"], {"local": [0.0, 0.1, 0.0]})

    def test_migrating_twice_is_migrating_once(self):
        """Nothing to move, nothing said, and not one byte written: the second
        run is a read of the file. Which is what makes this safe to put in
        front of a user who cannot remember whether they ran it."""
        self.mixed()
        marks.migrate(self.path)
        settled = self.path.read_bytes()
        self.path.chmod(0o444)          # nothing to move: nothing is opened to write
        try:
            self.assertEqual(marks.migrate(self.path), [])
        finally:
            self.path.chmod(0o644)
        self.assertEqual(self.path.read_bytes(), settled)


class OwnershipTest(unittest.TestCase):
    """One owner for the record, made load-bearing without a class.

    `lib/marks.py` is the only module that touches `marks.json`, and that was
    never the problem: the problem was that nothing owned what is *inside* it.
    The lifecycle ADR 0018 describes — pixel to pin to badge, orphaned when the
    part goes, addressed but never closed — was enforced across fourteen files,
    with its transition rules living as comments in whichever module happened to
    perform them.

    A convention alone is a convention the eleventh reader un-converges, and
    slice 19\'s migration depends on this one holding.
    """

    FIELDS = {"id", "author", "status", "text", "view", "pixel", "part", "ref",
              "to", "anchor", "local", "orphaned", "addressed", "from"}
    """Every field a mark record has. `local` is inside the anchor and `from` is
    only on a promoted veto\'s mark, and both are here because the roster is what
    a reader checks a new field against."""

    WRITERS = {"lib/marks.py"}
    """Who may write one. Readable as a roster on purpose: adding a name here is
    a decision somebody makes in a diff, which is the whole mechanism."""

    def writes(self, path):
        """Every write of a record field in this file: `(line, what)`.

        A subscript store is the obvious way to edit a record in place, and
        `pop` is the other one — dropping the pixel as a pin lands is a
        transition exactly as setting the pin is, and a guard that watched only
        assignment would wave it through.
        """
        found = []
        for node in ast.walk(ast.parse(path.read_text())):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                targets = [node.target]
            elif isinstance(node, ast.Delete):
                targets = node.targets
            for t in targets:
                if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) \
                        and t.slice.value in self.FIELDS:
                    found.append((node.lineno, ast.unparse(t)))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in ("pop", "setdefault") and node.args \
                    and isinstance(node.args[0], ast.Constant) \
                    and node.args[0].value in self.FIELDS:
                found.append((node.lineno, ast.unparse(node)))
        return found

    def test_no_module_outside_the_store_writes_a_record_field(self):
        """The three writers this slice removed were `anchor.apply`,
        `anchor.orphan` and `agent.addressed`, each editing records in place and
        calling `save` behind the store\'s back, plus the canvas naming the part
        under a click. Every one of them is a transition ADR 0018 defines, and
        every one now has a name in `lib/marks.py`."""
        for d in ("lib", "console"):
            for f in sorted((ROOT / d).glob("*.py")):
                rel = f"{d}/{f.name}"
                if rel in self.WRITERS:
                    continue
                for line, what in self.writes(f):
                    self.fail(f"{rel}:{line} writes a mark record field: {what}"
                              f" — ask lib/marks.py for the transition instead")


if __name__ == "__main__":
    unittest.main()
