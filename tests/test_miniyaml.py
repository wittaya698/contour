"""The reader every spec goes through (ADR 0002, ADR 0010).

`spec.yaml` is the definition of correct, and this is the only thing that reads
it: a misparse does not fail a check, it quietly changes what the check is
against. So each feature the module claims has a case here, written by hand, and
each construct it promises to refuse has one too — a refusal that stopped
refusing would hand back a spec that says something the file does not.

Hand-written rather than compared against PyYAML, because a test that skips on a
bare clone mostly does not run, and a bare clone is what ADR 0010 is for.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import miniyaml  # noqa: E402
from lib.miniyaml import YamlError, loads  # noqa: E402


class FeatureTest(unittest.TestCase):
    """What the docstring says is supported, one feature to a case."""

    def test_a_block_mapping_nests_by_indent(self):
        self.assertEqual(loads("dims:\n  width: 120\n  depth: 100\nname: plinth\n"),
                         {"dims": {"width": 120, "depth": 100}, "name": "plinth"})

    def test_a_block_sequence_of_scalars_and_of_mappings(self):
        self.assertEqual(loads("parts:\n  - cap\n  - name: pillar\n    count: 1\n"),
                         {"parts": ["cap", {"name": "pillar", "count": 1}]})

    def test_a_sequence_may_sit_at_its_keys_indent(self):
        self.assertEqual(loads("parts:\n- cap\n- pillar\nname: x\n"),
                         {"parts": ["cap", "pillar"], "name": "x"})

    def test_a_sequence_of_sequences(self):
        self.assertEqual(loads("- - 1\n  - 2\n- - 3\n"), [[1, 2], [3]])

    def test_an_empty_value_is_none(self):
        self.assertEqual(loads("a:\nb: ~\n"), {"a": None, "b": None})

    def test_flow_mappings_and_sequences_on_one_line(self):
        self.assertEqual(loads("size: [120, 100, 40]\nat: {x: 0, y: -1.5, tag: 'a, b'}\n"),
                         {"size": [120, 100, 40], "at": {"x": 0, "y": -1.5, "tag": "a, b"}})

    def test_flow_forms_nest(self):
        self.assertEqual(loads("m: {a: [1, {b: 2}], c: []}\n"),
                         {"m": {"a": [1, {"b": 2}], "c": []}})

    def test_plain_scalars_are_typed(self):
        self.assertEqual(loads("i: -3\nf: 2.5e-3\nd: .5\nt: true\nn: null\ns: 12mm\n"),
                         {"i": -3, "f": 0.0025, "d": 0.5, "t": True, "n": None, "s": "12mm"})

    def test_a_whole_number_is_an_int_not_a_float(self):
        """`count: 3` is three parts, and a check that prints `3.0/3` or
        compares with `is` would say otherwise; equality alone cannot see it."""
        got = loads("count: 3\nwidth: -120\nscale: 3.0\n")
        self.assertEqual([type(v) for v in got.values()], [int, int, float])

    def test_quoted_scalars_stay_strings(self):
        """A spec that says `version: "2"` means the text, not the number."""
        self.assertEqual(loads("a: \"2\"\nb: 'true'\nc: 'it''s'\nd: \"x\\ny\"\n"),
                         {"a": "2", "b": "true", "c": "it's", "d": "x\ny"})

    def test_a_colon_inside_quotes_or_a_word_is_not_a_key(self):
        self.assertEqual(loads("url: 'a: b'\ntime: 12:30\n"),
                         {"url": "a: b", "time": "12:30"})

    def test_a_literal_block_keeps_its_newlines(self):
        self.assertEqual(loads("note: |\n  one\n  two\nnext: 1\n"),
                         {"note": "one\ntwo\n", "next": 1})

    def test_a_folded_block_joins_lines_and_keeps_paragraphs(self):
        self.assertEqual(loads("note: >\n  one\n  two\n\n  three\n"),
                         {"note": "one two\nthree\n"})

    def test_strip_chomping_drops_the_last_newline(self):
        self.assertEqual(loads("a: |-\n  one\n  two\nb: >-\n  x\n  y\n"),
                         {"a": "one\ntwo", "b": "x y"})

    def test_keep_chomping_keeps_it(self):
        self.assertEqual(loads("a: |+\n  one\nb: >+\n  x\n"),
                         {"a": "one\n", "b": "x\n"})

    def test_a_block_keeps_indentation_past_its_own(self):
        self.assertEqual(loads("a: |\n  top\n    inner\n"), {"a": "top\n  inner\n"})

    def test_comments_are_dropped_but_a_hash_in_a_word_or_quote_is_not(self):
        self.assertEqual(loads("# heading\na: 1  # why\nb: 'x # y'\nc: a#b\n"),
                         {"a": 1, "b": "x # y", "c": "a#b"})

    def test_an_empty_document_is_none(self):
        self.assertIsNone(loads("# nothing but a comment\n\n"))

    def test_load_reads_a_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False,
                                         encoding="utf-8") as f:
            f.write("revision: 3\n")
        self.assertEqual(miniyaml.load(f.name), {"revision": 3})
        Path(f.name).unlink()


class RefusalTest(unittest.TestCase):
    """What the docstring promises to refuse, each refused out loud, naming the
    line it is on — so the person reading the error knows which field of the
    spec to look at without reading the parser."""

    def refused(self, text, line, what):
        with self.assertRaises(YamlError) as got:
            loads(text)
        said = str(got.exception)
        self.assertIn(f"line {line}", said)
        self.assertIn(what, said)
        return said

    def test_a_complex_key_is_refused(self):
        self.refused("? width\n: 120\n", 1, "complex keys")

    def test_a_complex_key_on_one_line_is_refused_not_read_as_a_name(self):
        """`? w: 1` would otherwise come back as a key called `? w`."""
        self.refused("dims:\n  ? width: 120\n", 2, "complex keys")

    def test_a_complex_key_as_a_value_is_refused_not_read_as_text(self):
        self.refused("dims:\n  ? width\n", 2, "complex keys")
        self.refused("parts:\n  - ? cap\n", 2, "complex keys")

    def test_an_anchor_is_refused_wherever_it_sits(self):
        """An anchor is harmless alone; it is refused because what it is for,
        the alias, would make one number in a spec stand for another."""
        self.refused("size: &big 10\n", 1, "anchors")
        self.refused("dims:\n  base: &b\n    x: 1\n", 2, "anchors")
        self.refused("parts:\n  - &p cap\n", 2, "anchors")
        self.refused("a: [1, &x 2]\n", 1, "anchors")
        self.refused("note: &n |\n  text\n", 1, "anchors")

    def test_an_alias_is_refused(self):
        self.refused("width: 10\ndepth: *big\n", 2, "aliases")
        self.refused("a: {b: *x}\n", 1, "aliases")

    def test_a_tag_is_refused(self):
        self.refused("size: !!int 10\n", 1, "tags")
        self.refused("parts:\n  - !box plinth\n", 2, "tags")
        self.refused("note: !!str |\n  text\n", 1, "tags")

    def test_a_marker_in_a_key_is_refused_too(self):
        self.refused("&k size: 1\n", 1, "anchors")

    def test_a_second_document_is_refused_not_dropped(self):
        """A spec with a `---` in it is two specs, and which one a check reads
        would be an accident."""
        self.refused("---\na: 1\n", 1, "multi-document")
        self.refused("a: 1\n---\nb: 2\n", 2, "multi-document")
        self.refused("a:\n  - 1\n--- \nb: 1\n", 3, "multi-document")
        self.refused("a: 1\n...\n", 2, "multi-document")

    def test_a_tab_in_the_indentation_is_refused(self):
        """A tab is as wide as the editor says, so the nesting it means is
        not in the file."""
        self.refused("a:\n\tb: 1\n", 2, "tab")
        self.refused("a:\n  b: 1\n \t c: 2\n", 3, "tab")
        self.refused("-\t1\n", 1, "tab")

    def test_a_tab_inside_a_value_is_only_text(self):
        self.assertEqual(loads("a: 'x\ty'\n"), {"a": "x\ty"})

    def test_a_question_mark_in_quotes_or_a_word_is_just_text(self):
        self.assertEqual(loads("a: '? no'\nb: why?\n\"? k\": 1\n"),
                         {"a": "? no", "b": "why?", "? k": 1})


if __name__ == "__main__":
    unittest.main()
