"""A span is read through the camera (ADR 0032, issue 138).

The arithmetic alone: from a reference's directions and its anchor span, a
span's millimetres and its `±`. These tests cannot make an image, and do not
need one: what a render decides for this arithmetic is where each corner of
the object lands, to the nearest pixel. So each picture here is a box of known
size projected through a known pinhole camera, its corners rounded to pixels,
and read back.
"""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import camera  # noqa: E402

SIZE = (1600, 1200)
BOX = (300.0, 200.0, 150.0)  # mm along x, y, z


def unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def picture(eye, f=1400.0, box=BOX):
    """The box's corners as a camera at `eye` sees them, looking at the box's
    middle: `{(i, j, k): pixel}`, the corner at `i * x + j * y + k * z`."""
    target = [c / 2 for c in box]
    forward = unit([t - e for t, e in zip(target, eye)])
    right = unit(cross(forward, [0, 1, 0]))
    up = cross(right, forward)
    seen = {}
    for i in (0, 1):
        for j in (0, 1):
            for k in (0, 1):
                d = [i * box[0] - eye[0], j * box[1] - eye[1], k * box[2] - eye[2]]
                depth = sum(a * b for a, b in zip(d, forward))
                seen[i, j, k] = (round(SIZE[0] / 2 + f * sum(a * b for a, b in zip(d, right)) / depth),
                                 round(SIZE[1] / 2 - f * sum(a * b for a, b in zip(d, up)) / depth))
    return seen


def edge(seen, a, b):
    return (seen[a], seen[b])


def lines(seen, axis):
    """The four box edges along one axis, as traced lines."""
    found = []
    for c in seen:
        if c[axis] == 0:
            other = list(c)
            other[axis] = 1
            found.append(edge(seen, c, tuple(other)))
    return found


class StraightOnTest(unittest.TestCase):

    def setUp(self):
        self.seen = picture(eye=(150.0, 100.0, 1500.0))
        self.directions = {"x": lines(self.seen, 0), "y": lines(self.seen, 1)}
        self.anchor = {"ends": edge(self.seen, (0, 0, 1), (1, 0, 1)), "mm": BOX[0]}

    def test_an_edge_sharing_the_anchors_corner_reads_back_within_its_bar(self):
        got = camera.read(SIZE, self.directions, self.anchor,
                          {"m1": {"ends": edge(self.seen, (1, 0, 1), (1, 1, 1))}})["m1"]
        self.assertEqual(got["along"], "y")
        self.assertLessEqual(abs(got["mm"] - BOX[1]), got["tol"], got)


class RefusedTest(unittest.TestCase):
    """No number, and why: what the picture would need to give one."""

    def read(self, eye, axes, ends):
        seen = picture(eye)
        directions = {n: lines(seen, "xyz".index(n)) for n in axes}
        anchor = {"ends": edge(seen, (0, 0, 1), (1, 0, 1)), "mm": BOX[0]}
        return camera.read(SIZE, directions, anchor, {"m3": {"ends": edge(seen, *ends)}})["m3"]

    def test_a_diagonal_gives_no_number(self):
        got = self.read(STEEP, "xyz", ((0, 0, 1), (1, 1, 1)))
        self.assertEqual(set(got), {"why"})
        self.assertIn("along none of x, y and z", got["why"])

    def test_depth_in_a_straight_on_picture_gives_no_number(self):
        """Straight on to x and y, nothing in the picture says the lens, and
        a span into the depth reads longer or shorter by whichever lens is
        guessed."""
        got = self.read((150.0, 100.0, 1500.0), "xyz", ((1, 0, 1), (1, 0, 0)))
        self.assertEqual(set(got), {"why"})
        self.assertIn("along z", got["why"])
        self.assertIn("two directions that both recede", got["why"])

    def test_an_anchor_along_no_direction_scales_nothing(self):
        seen = picture(STEEP)
        directions = {n: lines(seen, "xyz".index(n)) for n in "xyz"}
        anchor = {"ends": edge(seen, (0, 0, 1), (1, 1, 1)), "mm": 360.6}
        got = camera.read(SIZE, directions, anchor,
                          {"m3": {"ends": edge(seen, (1, 1, 1), (1, 0, 1))}})["m3"]
        self.assertEqual(set(got), {"why"})
        self.assertIn("the anchor runs along none of x, y and z", got["why"])

    def test_two_directions_scale_only_the_anchors_own(self):
        got = self.read(STEEP, "xy", ((1, 0, 1), (1, 1, 1)))
        self.assertEqual(set(got), {"why"})
        self.assertIn("a third direction square to x and y", got["why"])


STEEP = (800.0, 650.0, 700.0)
"""A three-quarter view from above: every edge of the box recedes."""

DEEP = (300.0, 200.0, 600.0)


class SteepTest(unittest.TestCase):

    def read(self, eye, spans, box=BOX):
        seen = picture(eye, box=box)
        directions = {"x": lines(seen, 0), "y": lines(seen, 1), "z": lines(seen, 2)}
        anchor = {"ends": edge(seen, (0, 0, 1), (1, 0, 1)), "mm": box[0]}
        return camera.read(SIZE, directions, anchor,
                           {name: {"ends": edge(seen, *ends)} for name, ends in spans.items()})

    def test_edges_sharing_the_anchors_corner_read_back_within_their_bars(self):
        got = self.read(STEEP, {"up": ((1, 0, 1), (1, 1, 1)), "back": ((1, 0, 1), (1, 0, 0))})
        self.assertEqual((got["up"]["along"], got["back"]["along"]), ("y", "z"))
        self.assertLessEqual(abs(got["up"]["mm"] - BOX[1]), got["up"]["tol"], got)
        self.assertLessEqual(abs(got["back"]["mm"] - BOX[2]), got["back"]["tol"], got)

    def test_an_edge_at_another_depth_reads_back_through_a_chain_of_corners(self):
        """The top face's back edge, as far behind the anchor as the box is
        deep: tied by a corner it shares with an edge already read, itself
        tied to one shared with the anchor. Listed first, read last.

        A box deeper than it is wide, so the far edge is enough farther from
        the camera that the anchor's scale alone reads it near 237 mm."""
        got = self.read((700.0, 600.0, 1200.0), {"far": ((1, 1, 0), (0, 1, 0)),
                                                 "top": ((1, 1, 1), (1, 1, 0)),
                                                 "up": ((1, 0, 1), (1, 1, 1))}, DEEP)
        self.assertEqual(got["far"]["along"], "x")
        self.assertLessEqual(abs(got["far"]["mm"] - BOX[0]), got["far"]["tol"], got)

    def test_the_same_edge_untied_gives_no_number(self):
        got = self.read(STEEP, {"far": ((1, 1, 0), (0, 1, 0)),
                                "up": ((1, 0, 1), (1, 1, 1))})["far"]
        self.assertEqual(set(got), {"why"})
        self.assertIn("tied to nothing", got["why"])
        self.assertIn("An end shared with the anchor or a span already read", got["why"])

    def test_an_edge_on_the_anchors_face_reads_back_through_its_plane(self):
        """The front face's top edge shares no corner with the anchor along
        its bottom, but lies on the plane through it spanned by x and y."""
        seen = picture(STEEP)
        directions = {"x": lines(seen, 0), "y": lines(seen, 1), "z": lines(seen, 2)}
        anchor = {"ends": edge(seen, (0, 0, 1), (1, 0, 1)), "mm": BOX[0]}
        top = edge(seen, (0, 1, 1), (1, 1, 1))
        got = camera.read(SIZE, directions, anchor, {"top": {"ends": top, "on": ("x", "y")}})
        self.assertLessEqual(abs(got["top"]["mm"] - BOX[0]), got["top"]["tol"], got)
        loose = camera.read(SIZE, directions, anchor, {"top": {"ends": top}})
        self.assertIn("on the plane through the anchor", loose["top"]["why"])

    def test_a_span_off_the_plane_it_names_gives_no_number(self):
        seen = picture(STEEP)
        directions = {"x": lines(seen, 0), "y": lines(seen, 1), "z": lines(seen, 2)}
        anchor = {"ends": edge(seen, (0, 0, 1), (1, 0, 1)), "mm": BOX[0]}
        got = camera.read(SIZE, directions, anchor,
                          {"side": {"ends": edge(seen, (0, 1, 1), (0, 1, 0)), "on": ("x", "y")}})
        self.assertIn("runs along z, which does not lie on the plane of x and y",
                      got["side"]["why"])

    def test_a_steeper_view_earns_a_wider_bar(self):
        """The edge up the anchor's face, as the camera turns away from that
        face. Steep is steep to a span: an edge into the picture's depth goes
        the other way, its bar widest when the view is nearly straight on and
        it is only a few pixels long."""
        def up(degrees):
            turn = math.radians(degrees)
            eye = (150 + 960 * math.sin(turn), 100 + 720 * math.sin(turn), 75 + 1200 * math.cos(turn))
            return self.read(eye, {"up": ((1, 0, 1), (1, 1, 1))})["up"]
        gentle, steep = up(15), up(60)
        self.assertLessEqual(abs(gentle["mm"] - BOX[1]), gentle["tol"], gentle)
        self.assertLessEqual(abs(steep["mm"] - BOX[1]), steep["tol"], steep)
        self.assertGreater(steep["tol"], 1.5 * gentle["tol"])


if __name__ == "__main__":
    unittest.main()
