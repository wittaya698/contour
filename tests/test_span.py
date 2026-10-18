"""A span: two pins on a reference that mean one distance (ADR 0018, 0018-7).

The payoff of ref marks. A single pin says *here is what I meant*; two say
*this distance, right here* — and `contour measure` reads between them instead
of sweeping a scanline the agent guessed at. `beaky-solo`'s open question 3 is
the waiting case: what separates the legs, on a picture where nothing else can
say.

The arithmetic lives outside Blender so these tests can make it. What they
cannot make is the image, so the scale arrives as a number here, the way the
silhouette hands it over in `cmd_measure`.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import marks as marks_store
from lib import span
from lib.canvas import Canvas
from client import post

PNG = b"\x89PNG\r\n\x1a\nreference"


class SpanMarkTest(unittest.TestCase):
    """The canvas end: two clicks, one line of text, one mark."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "sheet.png").write_bytes(PNG)
        self.marks = self.tmp / "marks.json"
        self.canvas = Canvas(sheet=self.tmp / "sheet.png", marks=self.marks)
        self.addCleanup(self.canvas.stop)
        self.canvas.start()

    def test_a_span_is_one_mark_carrying_both_of_its_ends(self):
        """Not two marks that happen to be near each other: the distance is
        the comment, so it has one id, one line of text and one status."""
        status, _ = post(self.canvas, "/marks",
                         {"ref": "persp.webp", "pixel": [412, 690],
                          "to": [498, 690], "text": "what separates the legs"})
        self.assertEqual(status, 200)
        stored = json.loads(self.marks.read_text())
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["pixel"], [412, 690])
        self.assertEqual(stored[0]["to"], [498, 690])
        self.assertEqual(stored[0]["text"], "what separates the legs")


class SpanReadingTest(unittest.TestCase):
    """The arithmetic, with the image already read: pixels and mm per pixel in,
    a distance out."""

    def test_a_span_is_the_distance_between_its_ends_not_its_width(self):
        """Two pins are rarely level. A user pointing at what separates the
        legs clicks the two outer edges wherever they are, so the reading is
        the length of the line they drew and not its horizontal extent — a
        3-4-5 triangle, which only Pythagoras gets right.
        """
        got = span.reading([100, 200], [130, 240], 2.0)
        self.assertAlmostEqual(got["px"], 50.0, places=9)
        self.assertAlmostEqual(got["mm"], 100.0, places=9)

    def test_a_reading_carries_the_error_bar_the_image_gives_it(self):
        """A pixel is the finest thing the image can say, and a span has two
        ends, so the honest bar is one pixel at each — in millimetres, at this
        picture's own scale. Stated, because a bare `126 mm` from a 1080px
        photograph reads as precision it does not have.
        """
        got = span.reading([100, 200], [130, 240], 2.0)
        self.assertAlmostEqual(got["tol"], 4.0, places=9)
        self.assertEqual(span.line(got), "100 mm \u00b14 mm  (50 px at 2.000 mm/px)")


class SpanAnchorTest(unittest.TestCase):
    """Where the millimetres come from. A picture carries proportion and never
    scale (ADR 0017), so a span is a pixel count until something states one
    real dimension."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.spec = self.tmp / "spec.yaml"

    def test_an_anchor_span_claims_a_size_the_spec_already_states(self):
        """Not a second number to author and keep in step with the first: the
        span claims one the spec states, any of them (ADR 0032, decision 3)."""
        self.spec.write_text("dimensions:\n"
                             "  height: { value: 1700, tol: 5 }\n"
                             "  width:  { value: 820, tol: 60 }\n")
        self.assertEqual(span.claimed(self.spec, "height")["mm"], 1700.0)
        self.assertEqual(span.claimed(self.spec, "width")["mm"], 820.0)

    def test_a_space_that_has_stated_no_height_has_no_anchor(self):
        """A space may be drafted before the user has said how big the thing
        is — `beaky-solo` spent its first day that way, measured in pixels
        with no `dimensions` in its spec at all. There is then no scale to be
        had, and none is invented."""
        self.assertIn("refused", span.claimed(self.spec, "height"))
        self.spec.write_text("model: beaky-solo\nparts:\n  - { name: head }\n")
        self.assertIn("refused", span.claimed(self.spec, "height"))


class SpanMeasureTest(unittest.TestCase):
    """Measuring a span end to end, with the image's scale already in hand.

    What `cmd_measure` does once the silhouette has told it mm per pixel.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.marks = self.tmp / "marks.json"

    def span_mark(self, a=(412, 690), b=(498, 690)):
        return marks_store.append(self.marks,
                                  {"ref": "persp.webp", "pixel": list(a),
                                   "to": list(b),
                                   "text": "what separates the legs"})

    def test_the_reading_comes_back_as_an_agent_mark_between_the_two_pins(self):
        """On the same reference, pinned in the middle of the span it answers,
        and open: a measurement is a finding the user may act on, not a
        receipt the toolkit files away (ADR 0018)."""
        asked = self.span_mark()
        rep = span.measure(self.marks, asked["id"], 2.0)
        self.assertTrue(rep["ok"], rep["lines"])
        got = [m for m in marks_store.load(self.marks) if m["id"] != asked["id"]]
        self.assertEqual(len(got), 1)
        said = got[0]
        self.assertEqual(said["ref"], "persp.webp")
        self.assertEqual(said["pixel"], [455, 690])
        self.assertEqual(said["author"], "agent")
        self.assertEqual(said["status"], "open")
        self.assertIn("172 mm", said["text"])
        self.assertIn(asked["id"], said["text"])

    def test_a_span_with_no_anchor_is_refused_rather_than_answered_in_pixels(self):
        """No scale, no millimetres. Answering in pixels would be a number
        that looks like a measurement and is not one, and pinning it would
        leave that on the picture for good."""
        asked = self.span_mark()
        rep = span.measure(self.marks, asked["id"], None)
        self.assertFalse(rep["ok"])
        self.assertIn("anchor", rep["lines"][0])
        self.assertEqual([m["id"] for m in marks_store.load(self.marks)],
                         [asked["id"]])

    def test_a_mark_that_is_not_a_span_cannot_be_measured(self):
        """One pin says *here is what I meant*; it does not say *how far*.
        Measuring it would have to invent the other end, and a second point
        the user never chose is the guessed scanline this slice exists to
        replace. An id that is on no mark at all is refused the same way."""
        one = marks_store.append(self.marks, {"ref": "persp.webp",
                                              "pixel": [412, 690],
                                              "text": "shoes should be like this"})
        rep = span.measure(self.marks, one["id"], 2.0)
        self.assertFalse(rep["ok"])
        self.assertIn("two ends", rep["lines"][0])
        gone = span.measure(self.marks, "m404", 2.0)
        self.assertFalse(gone["ok"])
        self.assertIn("m404", gone["lines"][0])
        self.assertEqual(len(marks_store.load(self.marks)), 1)

    def test_a_span_that_goes_nowhere_is_refused(self):
        """A slipped drag lands both ends on one pixel. Zero is not a
        measurement, and the scale it implies is a division by nothing."""
        asked = self.span_mark(a=(412, 690), b=(412, 690))
        rep = span.measure(self.marks, asked["id"], 2.0)
        self.assertFalse(rep["ok"])
        self.assertEqual([m["id"] for m in marks_store.load(self.marks)],
                         [asked["id"]])


class SpanAimTest(unittest.TestCase):
    """Which reference a span is asking about (ADR 0018).

    The first real drag on `beaky-solo` failed before it reached any
    arithmetic: a mark records `persp.webp`, `contour measure` resolves a
    path, and so the user had to name the same picture twice, in two
    spellings, and get the second one right. A span is pinned to a reference
    and can say which.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.marks = self.tmp / "marks.json"

    def span_mark(self, ref="persp.webp"):
        return marks_store.append(self.marks,
                                  {"ref": ref, "pixel": [412, 690],
                                   "to": [498, 690], "text": "the legs"})

    def test_a_span_names_the_reference_it_is_pinned_to(self):
        """So `--span` needs no reference argument at all. The mark is the
        one place that already knows, and a second place to say it is a
        second place to say it wrong."""
        made = self.span_mark()
        got = span.aim(self.marks, made["id"], None)
        self.assertTrue(got["ok"], got.get("lines"))
        self.assertEqual(got["ref"], "persp.webp")


    def test_a_reference_named_against_the_mark_is_refused(self):
        """Neither side silently wins. If the command line and the mark
        disagree about which picture this is, one of the two is a mistake,
        and choosing either would read the wrong image at the wrong scale and
        pin the answer to a third place."""
        made = self.span_mark()
        got = span.aim(self.marks, made["id"], "front.jpg")
        self.assertFalse(got["ok"])
        self.assertIn("persp.webp", got["lines"][0])
        self.assertIn("front.jpg", got["lines"][0])


    def test_the_same_picture_named_as_a_path_agrees(self):
        """`refs/persp.webp` and `persp.webp` are one reference under two
        spellings -- the path `measure` resolves and the bare name a mark
        records. Comparing them whole would refuse the one invocation that
        already worked."""
        made = self.span_mark()
        got = span.aim(self.marks, made["id"], "refs/persp.webp")
        self.assertTrue(got["ok"], got.get("lines"))
        self.assertEqual(got["ref"], "persp.webp")


    def test_an_id_that_is_on_no_mark_is_refused_before_anything_is_loaded(self):
        """`aim` runs first, so it meets a typo'd id before the image does,
        and has to say so rather than fall over reaching into a mark that is
        not there."""
        got = span.aim(self.marks, "m404", None)
        self.assertFalse(got["ok"])
        self.assertIn("m404", got["lines"][0])


    def test_a_mark_on_the_render_sheet_has_no_reference_to_aim_at(self):
        """A view mark is pinned to a render of the model, not to a picture
        of the thing -- so there is no reference to open and no anchor the
        spec can lend it. Refused, and not by way of a missing key."""
        one = marks_store.append(self.marks, {"view": "front", "pixel": [412, 690],
                                              "text": "I think arms should round"})
        got = span.aim(self.marks, one["id"], None)
        self.assertFalse(got["ok"])
        self.assertIn("reference", got["lines"][0])


class SpanIsNotGeometryTest(unittest.TestCase):
    """A span points at a photograph, so no build of ours resolves it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.marks = self.tmp / "marks.json"

    def test_a_span_never_waits_on_a_ray(self):
        """Both ends are pixels on an image no camera of ours rendered. A
        pixel plus a missing anchor is exactly the shape the resolver looks
        for, so this is the case that would be quietly mis-anchored if the
        store ever stopped saying *a photograph has no parts*."""
        made = marks_store.append(self.marks,
                                  {"ref": "persp.webp", "pixel": [412, 690],
                                   "to": [498, 690], "text": "the legs"})
        self.assertEqual(marks_store.unresolved(marks_store.load(self.marks)), [])
        self.assertEqual(marks_store.load(self.marks), [made])

    def test_measuring_a_span_writes_nothing_under_the_references(self):
        """Rule 1, at the one place in the toolkit that now has an image, a
        number and an opinion about it at the same moment. The answer goes to
        the marks file; the picture is evidence and stays untouched, bytes and
        timestamp both."""
        refs = self.tmp / "refs"
        refs.mkdir()
        pic = refs / "persp.webp"
        pic.write_bytes(PNG)
        before = (sorted(p.name for p in refs.iterdir()), pic.read_bytes(),
                  pic.stat().st_mtime_ns)
        asked = marks_store.append(self.marks,
                                   {"ref": "persp.webp", "pixel": [412, 690],
                                    "to": [498, 690], "text": "the legs"})
        self.assertTrue(span.measure(self.marks, asked["id"], 2.0)["ok"])
        self.assertEqual((sorted(p.name for p in refs.iterdir()),
                          pic.read_bytes(), pic.stat().st_mtime_ns), before)


if __name__ == "__main__":
    unittest.main()
