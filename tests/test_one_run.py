"""One suite run per machine at a time, held and not just asked for (issue 94).

`SignalTest` counts every `console.server` on the machine, on purpose: an
orphan has no parent left to report it. A second run alongside, from another
terminal, worktree or agent session, starts consoles of its own, and they read
as leaks. The README asked for one run at a time and an agent session ran two;
now a second run is refused at the door, naming the one already running.
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import one_run  # noqa: E402

STARTS_A_CONSOLE = re.compile(
    r'CONTOUR_CONSOLE_PYTHON|\bCONSOLE\b|"/enter"|"/create"|"/vary"|open\("console"')
"""What a test file names when it can start a `console.server`. The `.venv`
beside the toolkit means a console can start without the env hatch, so the
lobby's routes that launch one count too."""

HOLDS = re.compile(r"^(import one_run|from test_console import)", re.M)


def holder(code, env=None):
    return subprocess.run([sys.executable, "-c", code], cwd=str(HERE), env=env,
                          capture_output=True, text=True, timeout=30)


class OneRunTest(unittest.TestCase):
    def test_a_second_run_is_refused_and_told_whose_run_it_is(self):
        r = holder("import one_run")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("already running", r.stderr)
        self.assertIn(f"pid {os.getpid()}", r.stderr)

    def test_the_hold_goes_with_the_process(self):
        """A run that crashed, or was killed outright, leaves nothing to clean
        up: the OS lets go of the lock with the last descriptor on it. On a
        lock of its own, so this run's hold is not in the way."""
        env = dict(os.environ, CONTOUR_SUITE_LOCK=str(Path(tempfile.mkdtemp()) / "lock"))
        killed = subprocess.Popen([sys.executable, "-c",
                                   "import one_run, sys, time; print('held', flush=True); time.sleep(60)"],
                                  cwd=str(HERE), env=env, stdout=subprocess.PIPE, text=True)
        self.addCleanup(killed.wait)
        self.addCleanup(killed.stdout.close)
        self.assertEqual(killed.stdout.readline().strip(), "held")
        self.assertNotEqual(holder("import one_run", env).returncode, 0)
        killed.kill()
        killed.wait(timeout=10)
        r = holder("import one_run", env)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_every_file_that_can_start_a_console_holds_the_run(self):
        """A file left off would start consoles another run's `SignalTest` sees,
        which is issue 94 again, from one `-p` run of the wrong file."""
        loose = [f.name for f in sorted(HERE.glob("test_*.py"))
                 if STARTS_A_CONSOLE.search(f.read_text())
                 and not HOLDS.search(f.read_text())]
        self.assertEqual(loose, [])


if __name__ == "__main__":
    unittest.main()
