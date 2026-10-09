"""A stand-in a test writes is checked by the OS once per run, not per test (issue 95).

macOS assesses an executable the first time it runs, about a quarter of a
second, and a script written in `setUp` is a new executable every test. The
helper keeps one file per distinct body and gives each test a link to it at the
path it asked for, so a stub finds its test's files beside its own `$0`.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from executables import executable  # noqa: E402

BESIDE = '#!/bin/sh\necho "$1" >> "$(dirname "$0")/said"\n'


class ExecutableTest(unittest.TestCase):
    def test_it_runs_where_it_was_asked_for_and_writes_beside_itself(self):
        here = Path(tempfile.mkdtemp())
        stub = executable(here / "browser", BESIDE)
        self.assertEqual(stub, here / "browser")
        subprocess.run([str(stub), "hello"], check=True)
        self.assertEqual((here / "said").read_text(), "hello\n")

    def test_two_tests_asking_for_one_body_share_one_file(self):
        """The point: what the OS checked for the first test, it has already
        checked for the second."""
        one = executable(Path(tempfile.mkdtemp()) / "browser", BESIDE)
        two = executable(Path(tempfile.mkdtemp()) / "browser", BESIDE)
        self.assertEqual(one.resolve(), two.resolve())

    def test_two_bodies_are_two_files(self):
        quiet = executable(Path(tempfile.mkdtemp()) / "browser", "#!/bin/sh\nexit 0\n")
        loud = executable(Path(tempfile.mkdtemp()) / "browser", "#!/bin/sh\nexit 1\n")
        self.assertNotEqual(quiet.resolve(), loud.resolve())
        self.assertEqual(subprocess.run([str(quiet)]).returncode, 0)
        self.assertEqual(subprocess.run([str(loud)]).returncode, 1)

    def test_asking_twice_at_one_path_replaces_the_link(self):
        """A test that rewrites its stub mid-test, as `stub_blender`'s callers
        do, gets the new body and not an error."""
        at = Path(tempfile.mkdtemp()) / "blender-stub"
        executable(at, "#!/bin/sh\nexit 0\n")
        executable(at, "#!/bin/sh\nexit 3\n")
        self.assertEqual(subprocess.run([str(at)]).returncode, 3)


if __name__ == "__main__":
    unittest.main()
