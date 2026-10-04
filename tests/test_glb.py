"""The reader behind the export round-trip (ADR 0006).

The round-trip is the only proof an export is right, and it is only as good as
this parser: a file it misreads is a file the round-trip measures wrong, and a
file it half-reads is a file it measures confidently wrong. So the container's
edges — where it ends, what it starts with, which chunk comes first, and the
padding that is not data — are pinned with bytes built by hand, and one file
Blender actually wrote is committed beside them, measured against the fixture's
own numbers.
"""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import glb  # noqa: E402

JSON, BIN = 0x4E4F534A, 0x004E4942
SMOKE = Path(__file__).resolve().parent / "data" / "smoke.glb"


def chunk(kind, body):
    return struct.pack("<II", len(body), kind) + body


def container(*chunks, magic=b"glTF", version=2, length=None):
    body = b"".join(chunks)
    total = 12 + len(body) if length is None else length
    return struct.pack("<4sII", magic, version, total) + body


def doc_bytes(doc):
    """JSON padded with spaces to four bytes, as the format says."""
    js = json.dumps(doc).encode()
    return js + b" " * (-len(js) % 4)


# One triangle: three positions, the smallest scene that has a volume of zero
# and a bounding box that is not.
TRIANGLE = {
    "asset": {"version": "2.0"},
    "scene": 0, "scenes": [{"nodes": [0]}],
    "nodes": [{"name": "tri", "mesh": 0}],
    "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
    "accessors": [{"bufferView": 0, "componentType": 5126, "type": "VEC3", "count": 3}],
    "bufferViews": [{"buffer": 0, "byteLength": 36}],
    "buffers": [{"byteLength": 36}],
}
POINTS = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 2, 0)


class GlbTest(unittest.TestCase):
    def write(self, data):
        path = Path(tempfile.mkdtemp()) / "x.glb"
        path.write_bytes(data)
        return path

    def refused(self, data, *words):
        with self.assertRaises(ValueError) as got:
            glb.load(self.write(data))
        for word in words:
            self.assertIn(word, str(got.exception))

    def good(self):
        return container(chunk(JSON, doc_bytes(TRIANGLE)), chunk(BIN, POINTS))


class ContainerTest(GlbTest):
    def test_a_well_formed_file_gives_its_document_and_its_buffer(self):
        doc, blob = glb.load(self.write(self.good()))
        self.assertEqual(doc, TRIANGLE)
        self.assertEqual(blob, POINTS)

    def test_the_wrong_magic_is_not_a_glb(self):
        self.refused(container(chunk(JSON, doc_bytes(TRIANGLE)), magic=b"glTX"), "glTX")

    def test_a_version_other_than_two_is_refused(self):
        self.refused(container(chunk(JSON, doc_bytes(TRIANGLE)), version=1), "v1")


class TruncationTest(GlbTest):
    """A file cut short is refused, wherever the cut falls — never read as
    whatever happened to arrive."""

    def test_cut_inside_the_header(self):
        self.refused(self.good()[:8], "truncated")

    def test_an_empty_file(self):
        self.refused(b"", "truncated")

    def test_cut_inside_a_chunk_header(self):
        self.refused(self.good()[:16], "truncated")

    def test_cut_inside_the_json(self):
        good = self.good()
        self.refused(good[:12 + 8 + 5], "truncated")

    def test_cut_inside_the_buffer_is_not_a_shorter_buffer(self):
        """The one that used to pass: the buffer came back two bytes long and
        the round-trip would have measured whatever those two bytes were."""
        self.refused(self.good()[:-2], "truncated")

    def test_a_chunk_that_says_it_is_longer_than_the_file_is_refused(self):
        """The header can be honest about the file and a chunk still lie
        about itself; what it claims past the end is not there to read."""
        good = self.good()
        lying = good[:-len(POINTS) - 8] + struct.pack("<II", 64, BIN) + POINTS
        self.refused(lying, "truncated")

    def test_a_chunk_header_cut_short_at_the_end_is_refused(self):
        good = self.good()
        cut = good + b"\0\0\0\0"
        cut = cut[:8] + struct.pack("<I", len(cut)) + cut[12:]
        self.refused(cut, "truncated")

    def test_a_file_longer_than_it_says_is_refused(self):
        """The header's length is the file's claim about itself; bytes past it
        are a file that is not what it says it is."""
        good = self.good()
        self.refused(good + b"\0\0\0\0", "length")


class ChunkOrderTest(GlbTest):
    def test_the_first_chunk_must_be_json(self):
        self.refused(container(chunk(BIN, POINTS), chunk(JSON, doc_bytes(TRIANGLE))),
                     "JSON", "first")

    def test_a_file_with_no_json_is_refused(self):
        self.refused(container(chunk(BIN, POINTS)), "JSON")
        self.refused(container(), "JSON")

    def test_a_second_json_chunk_is_refused_not_obeyed(self):
        """It used to replace the first, so the document measured was the one
        written last."""
        self.refused(container(chunk(JSON, doc_bytes(TRIANGLE)),
                               chunk(JSON, doc_bytes({"asset": {"version": "2.0"}}))),
                     "JSON")

    def test_a_second_buffer_is_refused(self):
        self.refused(container(chunk(JSON, doc_bytes(TRIANGLE)), chunk(BIN, POINTS),
                               chunk(BIN, POINTS)), "BIN")

    def test_a_chunk_of_a_kind_nobody_knows_is_skipped(self):
        """The format says an unknown chunk is ignored, so an extension a newer
        exporter adds does not stop the round-trip."""
        _, blob = glb.load(self.write(container(
            chunk(JSON, doc_bytes(TRIANGLE)), chunk(0x5845_5458, b"abcd"),
            chunk(BIN, POINTS))))
        self.assertEqual(blob, POINTS)


class PaddingTest(GlbTest):
    def test_padding_is_not_data(self):
        """Spaces after the JSON and zeros after the buffer are there to align
        the next chunk; the triangle measures the same with them present."""
        data = container(chunk(JSON, doc_bytes(TRIANGLE)), chunk(BIN, POINTS + b"\0" * 4))
        got = glb.measure(self.write(data))
        self.assertEqual(got["tris"], 1)
        self.assertEqual(got["lo"], [0, 0, 0])
        self.assertEqual(got["hi"], [1, 2, 0])

    def test_a_chunk_not_padded_to_four_bytes_is_refused(self):
        """Every chunk starts on a four-byte boundary; one that does not means
        the writer was wrong about the rest of the file too."""
        self.refused(container(chunk(JSON, b'{"asset":{"version":"2.0"}}')), "4")

    def test_what_write_packs_is_padded_and_reads_back(self):
        doc = dict(TRIANGLE, extras={"odd": "x"})      # a length that needs padding
        path = Path(tempfile.mkdtemp()) / "w.glb"
        glb.write(path, doc, POINTS)
        data = path.read_bytes()
        self.assertEqual(struct.unpack_from("<I", data, 8)[0], len(data))
        self.assertEqual(glb.load(path)[0], doc)


class RigTest(GlbTest):
    """A rig as the file holds it (ADR 0023, issue 54): its joints, and each
    animation's length in seconds — the file has no frames and no rate."""

    def test_joints_and_how_long_each_animation_runs(self):
        times = struct.pack("<3f", 0.0, 0.5, 0.8333)
        doc = dict(TRIANGLE,
                   nodes=TRIANGLE["nodes"] + [{"name": "a"}, {"name": "b"}],
                   skins=[{"joints": [1, 2]}],
                   accessors=TRIANGLE["accessors"] + [
                       {"bufferView": 1, "componentType": 5126, "type": "SCALAR", "count": 3}],
                   bufferViews=TRIANGLE["bufferViews"] + [
                       {"buffer": 0, "byteOffset": 36, "byteLength": 12}],
                   buffers=[{"byteLength": 48}],
                   animations=[{"name": "sway", "samplers": [{"input": 1, "output": 1}],
                                "channels": [{"sampler": 0,
                                              "target": {"node": 1, "path": "rotation"}}]}])
        got = glb.measure(self.write(container(chunk(JSON, doc_bytes(doc)),
                                               chunk(BIN, POINTS + times))))
        self.assertEqual(got["joints"], 2)
        self.assertEqual(list(got["clips"]), ["sway"])
        self.assertAlmostEqual(got["clips"]["sway"], 0.8333, places=6)

    def test_a_file_with_no_rig_has_no_joints_and_no_clips(self):
        got = glb.measure(self.write(self.good()))
        self.assertEqual((got["joints"], got["clips"]), (0, {}))


class BlenderWroteThisTest(unittest.TestCase):
    """`tests/data/smoke.glb` is `contour export` of `fixtures/smoke/`, committed
    so the parser is shown a file it did not write. The fixture is the toolkit's
    own and no model's, so rule 8 does not touch it. Every number below is the
    fixture's `build.py` read in glTF's frame (Y up, metres), not the parser's
    earlier answer: a plinth 120 x 100 x 40 mm, a pillar 40 x 40 x 100 mm on it,
    and a cap that is a 30 mm sphere whose top is at 200 mm."""

    @classmethod
    def setUpClass(cls):
        cls.got = glb.measure(SMOKE)

    def near(self, got, want, places=6):
        for g, w in zip(got, want):
            self.assertAlmostEqual(g, w, places=places)

    def test_the_bounds_are_the_fixtures_in_glTF_space(self):
        self.near(self.got["lo"], [-0.060, 0.000, -0.050])
        self.near(self.got["hi"], [0.060, 0.200, 0.050])

    def test_each_part_is_a_node_with_the_volume_its_build_gives_it(self):
        vols = self.got["meshes"]
        self.assertEqual(sorted(vols), ["cap", "pillar", "plinth"])
        self.assertAlmostEqual(vols["plinth"], 0.120 * 0.100 * 0.040, places=9)
        self.assertAlmostEqual(vols["pillar"], 0.040 * 0.040 * 0.100, places=9)
        sphere = 4 / 3 * 3.141592653589793 * 0.030 ** 3
        self.assertTrue(0.97 * sphere < vols["cap"] < sphere,   # faceted 32 x 24, inscribed
                        f"cap is {vols['cap']:.4e} m^3 against a sphere's {sphere:.4e}")

    def test_the_triangles_and_materials_are_what_the_build_made(self):
        """1,496 is the build's own count; two boxes are 24 of them."""
        self.assertEqual(self.got["tris"], 1496)
        self.assertEqual(self.got["materials"], {"stone", "accent"})
        self.assertEqual(self.got["det_min"], 1.0)


if __name__ == "__main__":
    unittest.main()
