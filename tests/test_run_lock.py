"""A run holds the space, and a second caller is refused (ADR 0019, open
question 11).

These drive the launcher as a user does, from two processes at once, because
that is the only way the race they close can appear at all. The holder is a
plain `contour run` around a script that touches a file and then sleeps, so the
second caller arrives while the first is provably still alive.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTOUR = ROOT / "contour"
sys.path.insert(0, str(ROOT))

from lib import lock


class RunLockTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.space = self.tmp / "widget"
        (self.space / ".contour").mkdir(parents=True)
        (self.space / ".contour" / "project").write_text("toolkit: stub\n")
        self.flag = self.tmp / "holding"
        stub = self.tmp / "blender-stub"
        stub.write_text('#!/bin/sh\nprintf \'%s\' \'{"ok": true, "lines": '
                        '["ok   build  stub"]}\' > "$CONTOUR_REPORT"\n')
        stub.chmod(0o755)
        self.env = dict(os.environ, BLENDER=str(stub))

    def contour(self, *args, env=None):
        return subprocess.run([sys.executable, str(CONTOUR), *args],
                              cwd=str(self.space), env=env or self.env,
                              capture_output=True, text=True, timeout=60)

    def holder(self, seconds=30):
        """A live run over this space. Returns once it is provably holding."""
        script = (f"import pathlib, time; "
                  f"pathlib.Path({str(self.flag)!r}).write_text('x'); "
                  f"time.sleep({seconds})")
        p = subprocess.Popen([sys.executable, str(CONTOUR), "run",
                              sys.executable, "-c", script],
                             cwd=str(self.space), env=self.env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True)
        self.addCleanup(self._end, p)
        for _ in range(100):
            if self.flag.exists():
                return p
            time.sleep(0.05)
        self.fail("the holding run never started")

    def _end(self, p):
        if p.poll() is None:
            p.send_signal(signal.SIGINT)
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=10)
        # The pipes are files and they are ours. Left open they warn from
        # inside `doCleanups`, which is noise on top of the suite's own output
        # and the place a real leak would have shown (issue 27).
        for pipe in (p.stdout, p.stderr):
            if pipe is not None and not pipe.closed:
                pipe.close()

    def test_a_check_in_a_held_space_is_refused_rather_than_queued(self):
        self.holder()
        t0 = time.time()
        r = self.contour("check")
        self.assertLess(time.time() - t0, 10, "it waited instead of refusing")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("held", (r.stdout + r.stderr).lower())

    def test_the_refusal_names_what_holds_the_space(self):
        """A refusal the user cannot act on is a wedged space. It has to name
        the process, because deciding what to do about it means finding it."""
        p = self.holder()
        r = self.contour("check")
        said = r.stdout + r.stderr
        self.assertIn(str(p.pid), said)
        self.assertIn("python", said.lower())

    def test_a_check_inside_its_own_run_is_not_refused_by_its_own_lock(self):
        """The holder is a session that builds. If its own builds were refused
        the lock would be unusable for the thing it exists to protect."""
        r = self.contour("run", sys.executable, str(CONTOUR), "check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ok   build  stub", r.stdout)

    def test_the_space_is_free_again_once_the_run_has_finished(self):
        self.contour("run", sys.executable, "-c", "pass")
        r = self.contour("check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_run_that_failed_still_gives_the_space_back(self):
        r = self.contour("run", sys.executable, "-c", "raise SystemExit(7)")
        self.assertEqual(r.returncode, 7)
        self.assertEqual(self.contour("check").returncode, 0)

    def test_an_interrupted_run_gives_the_space_back(self):
        """Ctrl-C is how a run normally ends when the user has seen enough."""
        p = self.holder(seconds=3)
        p.send_signal(signal.SIGINT)
        p.wait(timeout=15)
        self.assertEqual(self.contour("check").returncode, 0)

    def test_a_hold_left_by_a_dead_run_does_not_wedge_the_space(self):
        """Killed outright, so nothing of the holder's ran on the way out. The
        space has to come back without the user learning about lock files."""
        p = self.holder(seconds=3)
        p.kill()
        p.wait(timeout=15)
        r = self.contour("check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(str(p.pid), r.stdout)

    def test_the_hold_is_not_something_a_space_commits(self):
        """A lock is about this machine right now. Committing one would hand a
        clone a hold by a pid that never existed there."""
        repo = self.tmp / "clean"
        (repo / ".contour").mkdir(parents=True)
        (repo / ".gitignore").write_text(
            (ROOT / "templates" / "space" / "gitignore").read_text())
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / ".contour" / lock.NAME).write_text("{}")
        r = subprocess.run(["git", "-C", str(repo), "status", "--porcelain",
                            "--ignored=no"], capture_output=True, text=True)
        self.assertNotIn(lock.NAME, r.stdout)

    def test_two_terminals_building_at_once_get_the_same_refusal(self):
        """The case that races today, with no console anywhere near it: one
        person, two shells, one space. Blender is stubbed slow so the second
        caller provably arrives while the first is still inside its build."""
        started = self.tmp / "building"
        slow = self.tmp / "blender-slow"
        slow.write_text(f'#!/bin/sh\ntouch {started}\nsleep 5\n'
                        f'printf \'%s\' \'{{"ok": true, "lines": ["ok   build  stub"]}}\''
                        f' > "$CONTOUR_REPORT"\n')
        slow.chmod(0o755)
        first = subprocess.Popen([sys.executable, str(CONTOUR), "check"],
                                 cwd=str(self.space),
                                 env=dict(os.environ, BLENDER=str(slow)),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True)
        self.addCleanup(self._end, first)
        for _ in range(200):
            if started.exists():
                break
            time.sleep(0.05)
        else:
            self.fail("the first build never started")
        second = self.contour("check")
        self.assertEqual(second.returncode, 3)
        self.assertIn("held by", second.stderr)
        self.assertIn(str(first.pid), second.stderr)

    def test_a_run_inside_a_run_does_not_hand_the_space_back_early(self):
        """A nested call belongs to the same session, so it takes nothing — and
        must therefore release nothing, or the space opens mid-session while
        the outer run is still editing `build.py`."""
        p = self.holder()
        inner = self.contour("run", sys.executable, "-c", "pass",
                             env=dict(self.env,
                                      CONTOUR_RUN=lock.holder(self.space)["run"]))
        self.assertEqual(inner.returncode, 0, inner.stdout + inner.stderr)
        self.assertEqual(self.contour("check").returncode, 3)
        self.assertTrue(lock.path(self.space).exists())
        self.assertEqual(lock.holder(self.space)["pid"], p.pid)

    def test_a_hold_nobody_can_read_does_not_wedge_the_space(self):
        """A truncated write, a half-synced folder. A record that names no
        process cannot be honoured — there is nobody to wait for."""
        lock.path(self.space).write_text("{not json")
        r = self.contour("check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
