"""A script reads a locked reference (ADR 0036, issue 160).

The agent measures colour with a short script that opens the photo. Which of
a script's calls write is guessing from its text (issue 152), so the picture
is made read-only instead: a script that reads runs, and one that writes fails
before anything changes. Every picture in `refs/` is locked, tracked or not,
because a new space's photo is not committed yet, and that is the one the
agent samples first.

Driven the way the hook drives it, the PreToolUse JSON on stdin and the exit
code out, as `test_spec_guard` drives it.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import one_run    # noqa: E402,F401  one suite run per machine (issue 94)
from console.run import Run    # noqa: E402
from lib import locked    # noqa: E402
from test_run_record import RecordCase, WAIT_S    # noqa: E402

GUARD = ROOT / "tools" / "guards" / "spec.py"
CONTOUR = ROOT / "contour"

DENY = 2

SAMPLE = ("python3 -c \"from PIL import Image; im=Image.open('refs/side.png')"
          ".convert('RGB'); print(im.getpixel((4, 8)))\"")


def writable(path):
    return bool(path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


class GuardCase(unittest.TestCase):

    def setUp(self):
        top = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, top, ignore_errors=True)
        self.space = top / "widget"
        r = subprocess.run([sys.executable, str(CONTOUR), "init", "widget"],
                           cwd=str(top), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def picture(self, rel, tracked=True):
        path = self.space / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"png")
        if tracked:
            subprocess.run(["git", "-C", str(self.space), "add", rel], check=True)
        return path

    def guard(self, command, event="PreToolUse"):
        ev = json.dumps({"cwd": str(self.space), "tool_name": "Bash",
                         "hook_event_name": event, "tool_use_id": "toolu_1",
                         "tool_input": {"command": command}})
        return subprocess.run([sys.executable, str(GUARD)], input=ev,
                              capture_output=True, text=True,
                              env=dict(os.environ, CLAUDE_PROJECT_DIR=str(self.space)))


class ReadTest(GuardCase):

    def test_a_script_that_reads_a_tracked_reference_runs_and_it_is_locked(self):
        side = self.picture("refs/side.png")
        r = self.guard(SAMPLE)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(writable(side))

    def test_a_new_spaces_photo_is_locked_though_git_does_not_track_it(self):
        side = self.picture("refs/side.png", tracked=False)
        front = self.picture("refs/front.png", tracked=False)
        self.assertEqual(self.guard(SAMPLE).returncode, 0)
        self.assertFalse(writable(side))
        self.assertFalse(writable(front), "every picture, not only the one named")

    def test_the_calls_issue_160_was_asked_about_run(self):
        self.picture("refs/walkie.png")
        for call in (SAMPLE + " 2>&1 | head -40",
                     ".venv/bin/python -c \"import numpy as np; from PIL import Image; "
                     "a=np.asarray(Image.open('refs/walkie.png').convert('RGB')); "
                     "print(a[40:60, 10:30].mean(axis=(0, 1)))\" 2>&1 | head -40",
                     "python3 - <<'EOF'\nfrom PIL import Image\n"
                     "im = Image.open('refs/walkie.png')\nprint(im.size)\nEOF",
                     # The first call of the live try, gated: the `ls` named the
                     # folder, and the interpreter left behind read as a write.
                     "ls refs/ && python3 -c \"from PIL import Image; "
                     "im=Image.open('refs/walkie.png'); print(im.size, im.mode)\"",
                     "ls -la refs/ && python3 - <<'EOF'\nfrom PIL import Image\n"
                     "print(Image.open('refs/walkie.png').size)\nEOF"):
            with self.subTest(call=call):
                r = self.guard(call)
                self.assertEqual(r.returncode, 0, r.stderr)


@unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                 "root writes through a read-only file")
class WriteTest(GuardCase):

    def test_a_script_that_writes_a_reference_fails_before_it_changes(self):
        side = self.picture("refs/side.png")
        call = "python3 -c \"open('refs/side.png', 'wb').write(b'drawn over')\""
        self.assertEqual(self.guard(call).returncode, 0)
        ran = subprocess.run(call, shell=True, cwd=self.space,
                             capture_output=True, text=True)
        self.assertNotEqual(ran.returncode, 0)
        self.assertIn("PermissionError", ran.stderr)
        self.assertEqual(side.read_bytes(), b"png")


class UnchangedTest(GuardCase):

    def test_a_new_picture_can_still_be_saved_beside_locked_ones(self):
        self.picture("refs/side.png")
        self.assertEqual(self.guard(SAMPLE).returncode, 0)
        (self.space / "refs" / "front.png").write_bytes(b"a second photo")
        self.assertEqual(self.guard("cp ~/Downloads/top.png refs/top.png").returncode, 0)

    def test_every_other_write_to_a_tracked_picture_is_denied_before_it_runs(self):
        self.picture("refs/side.png")
        for call in ("cp new.png refs/side.png", "mv new.png refs/side.png",
                     "cat new.png > refs/side.png", "sips -z 10 10 refs/side.png",
                     "tee refs/side.png < new.png"):
            with self.subTest(call=call):
                self.assertEqual(self.guard(call).returncode, DENY)


class ReachTest(unittest.TestCase):
    """Which pictures a call's lock reaches."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        for rel in ("refs/side.png", "variants/tall/refs/front.png", ".git/refs/heads/master",
                    "build.py"):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_bytes(b"x")

    def test_the_folder_a_named_picture_is_in_and_nothing_else(self):
        locked.lock(self.root, ["variants/tall/refs/front.png"])
        self.assertFalse(writable(self.root / "variants/tall/refs/front.png"))
        for rel in ("refs/side.png", ".git/refs/heads/master", "build.py"):
            self.assertTrue(writable(self.root / rel), rel)

    def test_gits_own_refs_are_never_a_reference(self):
        locked.lock(self.root, [".git/refs/heads/master", "/etc/refs/x"])
        self.assertTrue(writable(self.root / ".git/refs/heads/master"))


class AroundTest(GuardCase):
    """The lock is on the file and not the folder, so a script can still
    delete a picture and save another in its place (ADR 0036, decision 3)."""

    def test_a_script_naming_a_way_round_the_lock_is_still_denied(self):
        self.picture("refs/side.png")
        for call in ("python3 -c \"import os; os.remove('refs/side.png'); "
                     "open('refs/side.png', 'wb').write(b'x')\"",
                     "python3 -c \"import os; os.chmod('refs/side.png', 0o644)\"",
                     "python3 -c \"from pathlib import Path; "
                     "Path('new.png').replace('refs/side.png')\"",
                     "python3 - <<'EOF'\nimport shutil\n"
                     "shutil.copy('new.png', 'refs/side.png')\nEOF",
                     "python3 -c \"import subprocess; "
                     "subprocess.run(['cp', 'new.png', 'refs/side.png'])\"",
                     "perl -e 'unlink \"refs/side.png\"'",
                     "ruby -e 'File.delete(\"refs/side.png\")'"):
            with self.subTest(call=call):
                self.assertEqual(self.guard(call).returncode, DENY)

    def test_a_script_from_a_file_cannot_be_read_and_is_still_denied(self):
        self.picture("refs/side.png")
        for call in ("python3 tools/sample.py refs/side.png",
                     # Taking out the second's interpreter must not let the first by.
                     "python3 tools/sample.py refs/side.png && python3 -c 'print(1)'",
                     "python3 tools/sample.py refs/side.png && python3 - <<'EOF'\n"
                     "print(1)\nEOF"):
            with self.subTest(call=call):
                self.assertEqual(self.guard(call).returncode, DENY)


class BackstopTest(GuardCase):
    """After the call, git says whether a tracked picture still matches
    (ADR 0036, decision 4): what the lock and the word list miss."""

    # Spells the way round in pieces, so the word list does not see it.
    HIDDEN = ("python3 -c \"import os; getattr(os, 'ch' + 'mod')('refs/side.png', 0o644); "
              "open('refs/side.png', 'wb').write(b'drawn over')\"")

    def ran(self, command):
        """The call through both hooks, run between them as the agent's tool
        would run it, and what the second hook said."""
        self.assertEqual(self.guard(command).returncode, 0)
        subprocess.run(command, shell=True, cwd=self.space, capture_output=True)
        return self.guard(command, event="PostToolUse")

    def test_a_tracked_picture_changed_anyway_is_put_back_and_locked(self):
        side = self.picture("refs/side.png")
        after = self.ran(self.HIDDEN)
        self.assertEqual(after.returncode, DENY)
        self.assertIn("refs/side.png", after.stderr)
        self.assertIn("refused", after.stderr)
        self.assertEqual(side.read_bytes(), b"png")
        self.assertFalse(writable(side))

    def test_a_call_that_fails_is_checked_after_as_well(self):
        """Claude Code sends a failed call a hook event of its own, and a
        script can change a picture and then fail (found on the live try)."""
        side = self.picture("refs/side.png")
        call = self.HIDDEN + " && false"
        self.assertEqual(self.guard(call).returncode, 0)
        subprocess.run(call, shell=True, cwd=self.space, capture_output=True)
        after = self.guard(call, event="PostToolUseFailure")
        self.assertEqual(after.returncode, DENY)
        self.assertEqual(side.read_bytes(), b"png")

    def test_a_read_says_nothing_after(self):
        self.picture("refs/side.png")
        after = self.ran(SAMPLE)
        self.assertEqual((after.returncode, after.stderr), (0, ""))

    def test_a_change_the_user_made_before_the_call_is_left_alone(self):
        """Putting back their own unsaved change would be the agent changing
        their picture."""
        side = self.picture("refs/side.png")
        side.write_bytes(b"the user's new photo")
        after = self.ran(SAMPLE)
        self.assertEqual(after.returncode, 0, after.stderr)
        self.assertEqual(side.read_bytes(), b"the user's new photo")


    def test_a_space_runs_the_guard_after_every_shell_call(self):
        """The backstop is only as good as the hook that hands it the call,
        and a failed call is handed to a hook of its own."""
        settings = json.loads((ROOT / "templates" / "space" / ".claude"
                               / "settings.json").read_text())
        for event in ("PostToolUse", "PostToolUseFailure"):
            after = [e for e in settings["hooks"].get(event, [])
                     if any("hook spec" in h.get("command", "") for h in e["hooks"])]
            self.assertEqual(len(after), 1, event)
            self.assertIn("Bash", after[0]["matcher"].split("|"), event)


class ConsoleTest(RecordCase):
    """Under a console the gate asks nothing, and the console locks the
    pictures itself rather than lean on the hook having run first."""

    def called(self, command):
        """What a watched run's gate gave a call, and the run's events."""
        given = []

        def drive(prompt, options, gate, say):
            given.append(gate("Bash", {"command": command}))
        run = Run(self.space, drive=drive)
        self.addCleanup(lambda: run.live and run.end())
        run.start("sample the colour", ceiling=10**6)
        deadline = time.monotonic() + WAIT_S
        while not given:
            self.assertLess(time.monotonic(), deadline, "the call was never answered")
            self.assertIsNone(run.pending, "the call was gated")
            time.sleep(0.01)
        return given[0], run.events

    def test_a_script_that_reads_a_reference_raises_no_gate_and_is_locked(self):
        side = self.space / "refs" / "side.png"
        side.parent.mkdir()
        side.write_bytes(b"png")
        given, events = self.called(SAMPLE)
        self.assertEqual(given, (True, None))
        self.assertEqual([e for e in events if e["kind"] == "gate"], [])
        self.assertFalse(writable(side))

    def test_a_script_naming_a_way_round_is_still_gated(self):
        """A new space's photo: the guard lets it by untracked, as before, and
        the gate is what asks."""
        (self.space / "refs").mkdir()
        (self.space / "refs" / "side.png").write_bytes(b"png")
        run = Run(self.space, drive=lambda prompt, options, gate, say: gate(
            "Bash", {"command": "python3 -c \"import os; os.remove('refs/side.png')\""}))
        self.addCleanup(lambda: run.live and run.end())
        run.start("sample the colour", ceiling=10**6)
        deadline = time.monotonic() + WAIT_S
        while run.pending is None:
            self.assertLess(time.monotonic(), deadline, "the call was not gated")
            time.sleep(0.01)
        self.assertEqual(run.pending["category"], "ref-write")


if __name__ == "__main__":
    unittest.main()
