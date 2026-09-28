"""A JSON file on disk, read or written the one way (slice 16).

Four modules answered *read this file or a default*, *write it back* and *what
is the next id* separately, and `lib/marks.py` and `console/vetoes.py` had
drifted into near-copies down to the compiled id regex. The store owns those
mechanics and nothing else: which files exist, what they are called and what
their ids are prefixed with stay facts about marks, vetoes, the panel and the
views, because a store that knew every file in the system would be the thing
this batch is undoing.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import marks, store


class LoadTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "records.json"

    def test_a_file_that_is_not_there_reads_as_the_default_it_was_given(self):
        """Two callers want two different answers to an absent file: marks and
        vetoes want an empty list to append to, the panel and the views want
        None, because *no sheet has ever been drawn* is a state the page shows
        and an empty sheet is not. So the default is the caller's to name."""
        self.assertEqual(store.load(self.path, []), [])
        self.assertIsNone(store.load(self.path, None))

    def test_a_file_that_is_not_json_raises_rather_than_reading_as_empty(self):
        """A truncated store is a finding, not an empty one. Reading it as the
        default would be believed by the next append, which writes the whole
        file back — so the recovery that looked kind is how every mark in it is
        deleted, quietly, by the tool that was meant to be keeping them."""
        self.path.write_text("[{\"id\": \"m1\"")
        with self.assertRaises(ValueError):
            store.load(self.path, [])


class SaveTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "records.json"

    def test_what_was_saved_is_what_loads_back(self):
        store.save(self.path, [{"id": "m1", "text": "too deep"}])
        self.assertEqual(store.load(self.path, []),
                         [{"id": "m1", "text": "too deep"}])

    def test_a_record_lands_in_bytes_a_diff_can_be_read_in(self):
        """One field per line and a newline at the end, which is the shape
        `marks.json` and `vetoes.json` are already committed in: a record
        arrives at the bottom and nothing above it moves, so `git diff` shows
        the sentence that was added and not a reformatted file."""
        store.save(self.path, [{"id": "v1"}])
        self.assertEqual(self.path.read_text(encoding="utf-8"),
                         '[\n  {\n    "id": "v1"\n  }\n]\n')


class NextIdTest(unittest.TestCase):
    def test_it_counts_past_the_highest_ever_used_not_past_the_count(self):
        """Closed marks are pruned (0018-2), so two records can be `m1` and
        `m3` with nothing between them. One past the count would hand out `m3`
        again, and an id that points at two different findings is worse than a
        gap in the numbering, which costs nothing and tells the truth."""
        records = [{"id": "m1"}, {"id": "m3"}]
        self.assertEqual(store.next_id(records, "m"), "m4")

    def test_nothing_on_file_starts_at_one(self):
        self.assertEqual(store.next_id([], "v"), "v1")

    def test_an_id_of_another_kind_is_not_counted(self):
        """The two stores sit side by side in a space and a record can carry a
        reference to the other — a promoted veto's mark names `from: v3`. Only
        the id under this prefix decides the next one."""
        self.assertEqual(store.next_id([{"id": "v3"}], "m"), "m1")

    def test_an_id_that_is_not_a_number_is_not_counted(self):
        """Hand-edited or from an older shape. It is skipped rather than
        refused: it is somebody's real record, and the numbering only has to
        avoid colliding with what it can read."""
        self.assertEqual(store.next_id([{"id": "m12x"}, {}, {"id": "m2"}], "m"),
                         "m3")


class SameBytesTest(unittest.TestCase):
    """What the stores were committing before the mechanics moved.

    `marks.json` and `vetoes.json` are tracked, so the shape of the file is
    part of what a space's history holds: a refactor that reindented them would
    put a whole-file diff in the next commit and hide whatever real record
    arrived in it. Written out here in full, from the shape on disk today,
    because the point is the bytes and not a round-trip.
    """
    MARKS = ('[\n  {\n    "id": "m1",\n    "anchor": {\n      "part": "beak"\n'
             '    },\n    "text": "too deep",\n    "author": "user",\n'
             '    "status": "open"\n  }\n]\n')

    def test_a_mark_is_stored_in_the_bytes_it_always_was(self):
        path = Path(tempfile.mkdtemp()) / marks.NAME
        marks.append(path, {"anchor": {"part": "beak"}, "text": "too deep"})
        self.assertEqual(path.read_text(encoding="utf-8"), self.MARKS)
