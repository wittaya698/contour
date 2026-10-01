"""The launcher, run as the user runs it.

Blender is stubbed: `contour check` shells out to $BLENDER and reads the JSON
report it leaves behind, so a four-line shell script stands in for it and these
stay fast. What is under test is the launcher's own behaviour around that call,
not Blender's.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTOUR = ROOT / "contour"


def stages(dirpath):
    """Which stages a stubbed Blender was asked for, in order — one process
    each. Read from the trace `stub_blender` leaves, and shared with the console
    tests, which watch for a stage the console spawned rather than ran."""
    trace = Path(dirpath) / "stages"
    return [line.rsplit(" -- ", 1)[-1].split()[0]
            for line in trace.read_text().splitlines()] \
        if trace.exists() else []


def stub_blender(dirpath, ok=True, crash=False):
    """A Blender that writes the report the launcher reads, names the stage it
    was asked for, and records it.

    `ok=False` is a verify-red check: the build saved, the spec was not met — so
    it is the *build* stage that reports red and a render of that build still
    succeeds. `crash` is a `build.py` that raised, which leaves no report at all
    and no geometry, and is a different event with a different sheet (ADR 0019,
    decision 29). The trace is how a test can tell what the launcher did.
    """
    verdict = "true" if ok else "false"
    script = dirpath / "blender-stub"
    lines = [
        "#!/bin/sh",
        f'echo "$@" >> "{dirpath / "stages"}"',
        'for a in "$@"; do last="$a"; done',
        "ok=true; code=0",
        f'if [ "$last" = build ]; then ok={verdict}; code={0 if ok else 1}; fi',
    ]
    if crash:
        lines.append("exit 1")                # no report: Blender died mid-stage
    else:
        lines += [
            'printf \'{"ok": %s, "lines": ["stub ran %s"], '
            '"results": [{"name": "stub", "ok": %s}]}\' '
            '"$ok" "$last" "$ok" > "$CONTOUR_REPORT"',
            "exit $code",
        ]
    script.write_text("\n".join(lines) + "\n")
    script.chmod(0o755)
    return script


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.space = self.tmp / "widget"
        (self.space / ".contour").mkdir(parents=True)
        (self.space / ".contour" / "project").write_text("toolkit: stub\n")

    def run_contour(self, *args, cwd=None, blender=None, run=None):
        env = dict(os.environ, BLENDER=str(blender or stub_blender(self.tmp)))
        if run:
            env["CONTOUR_RUN"] = run          # this call belongs to that run
        return subprocess.run([sys.executable, str(CONTOUR), *args],
                              cwd=str(cwd or self.space), env=env,
                              capture_output=True, text=True, timeout=60)

    def stages(self):
        """Which stages the launcher ran, in order — one Blender process each."""
        return stages(self.tmp)

    def mark(self, status="open"):
        path = self.space / "marks.json"
        stored = json.loads(path.read_text()) if path.exists() else []
        stored.append({"id": f"m{len(stored) + 1}", "view": "front",
                       "pixel": [1, 2], "text": "x", "author": "user",
                       "status": status})
        path.write_text(json.dumps(stored))

    def old_spelling_mark(self):
        """A mark as a space marked on before slice 19 holds it: the part named
        under the anchor, beside the pin."""
        path = self.space / "marks.json"
        stored = json.loads(path.read_text()) if path.exists() else []
        stored.append({"id": f"m{len(stored) + 1}", "text": "x",
                       "anchor": {"part": "neck", "local": [0, 0, 0]},
                       "author": "user", "status": "open"})
        path.write_text(json.dumps(stored))

    def test_doctor_counts_the_marks_in_the_old_spelling(self):
        """Reported and not repaired. `marks.json` is tracked and holds the
        user's own findings, so the rewrite is a state they choose and see —
        doctor says how many and what to type (rule 5, slice 19)."""
        self.old_spelling_mark()
        self.old_spelling_mark()
        r = self.run_contour("doctor")
        self.assertIn("2 marks in the old spelling", r.stdout)
        self.assertIn("contour migrate-marks", r.stdout)

    def test_doctor_says_nothing_about_spelling_when_there_is_none(self):
        """A space that has nothing to migrate must not carry a line about
        migrating. A report that always mentions it is furniture, and an ok
        beside it reads as a thing the user has to keep checking."""
        self.mark()
        r = self.run_contour("doctor")
        self.assertNotIn("spelling", r.stdout)

    def test_migrate_marks_rewrites_them_and_names_what_it_moved(self):
        """The one command that rewrites a tracked file the user did not just
        edit, so it says which records moved: a diff nobody can attribute is a
        diff nobody can review."""
        self.old_spelling_mark()
        r = self.run_contour("migrate-marks")
        self.assertEqual(r.returncode, 0)
        self.assertIn("1 mark migrated", r.stdout)
        self.assertIn("m1", r.stdout)
        stored = json.loads((self.space / "marks.json").read_text())
        self.assertEqual(stored[0]["part"], "neck")
        self.assertEqual(stored[0]["anchor"], {"local": [0, 0, 0]})

    def test_migrate_marks_a_second_time_says_so_and_writes_nothing(self):
        """Idempotent where the user can see it. Someone who cannot remember
        whether they ran it must be able to run it again and get an answer
        rather than a diff."""
        self.old_spelling_mark()
        self.run_contour("migrate-marks")
        settled = (self.space / "marks.json").read_bytes()
        r = self.run_contour("migrate-marks")
        self.assertEqual(r.returncode, 0)
        self.assertIn("nothing to migrate", r.stdout)
        self.assertEqual((self.space / "marks.json").read_bytes(), settled)

    def test_nothing_else_migrates_a_space(self):
        """Nothing rewrites tracked user data on load. A check builds, renders
        and reads the marks, and a space in the old spelling comes out of it
        byte-identical — the migration is a thing the user asks for by name
        (rule 5, slice 19)."""
        self.old_spelling_mark()
        before = (self.space / "marks.json").read_bytes()
        self.assertEqual(self.run_contour("check").returncode, 0)
        self.assertIn("in the old spelling", self.run_contour("doctor").stdout)
        self.assertEqual((self.space / "marks.json").read_bytes(), before)

    def test_canvas_outside_a_model_space_says_so_and_fails(self):
        r = self.run_contour("canvas", cwd=self.tmp)
        self.assertEqual(r.returncode, 2)
        self.assertIn("not in a model space", r.stderr)

    def test_resolve_outside_a_model_space_says_so_and_fails(self):
        """Resolution is about one space's marks and one space's build, so being
        in a space is the whole of what makes it meaningful. The console always
        passes one; a person who typed it in the wrong directory gets the
        launcher's own sentence rather than a stage that quietly anchors nothing.
        """
        r = self.run_contour("resolve", cwd=self.tmp)
        self.assertEqual(r.returncode, 2)
        self.assertIn("not in a model space", r.stderr)

    def test_check_reports_open_marks(self):
        self.mark()
        self.mark()
        r = self.run_contour("check")
        self.assertEqual(r.returncode, 0)
        self.assertIn("2 marks open", r.stdout)

    def test_check_says_nothing_about_marks_when_none_are_open(self):
        self.mark(status="closed")
        r = self.run_contour("check")
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("open", r.stdout)

    def test_check_says_the_same_thing_whether_or_not_vetoes_exist(self):
        """A veto is never open, so a veto line would never go away — and a
        status line that is always present is furniture nobody reads (ADR 0019,
        decision 28). Byte-identical and not merely quiet: the check\'s report is
        a token budget, and a line about records the user cannot act on here is
        the one thing a terse report cannot afford.
        """
        self.mark()
        before = self.run_contour("check")
        (self.space / "vetoes.json").write_text(json.dumps(
            [{"id": "v1", "category": "spec-write", "tool": "Edit",
              "call": {"file_path": "spec.yaml"}, "reason": "measure it first",
              "author": "user", "build": "b0b0b0b0b0b0"}], indent=2) + "\n")
        after = self.run_contour("check")
        self.assertEqual(after.returncode, before.returncode)
        self.assertEqual(after.stdout, before.stdout)
        self.assertEqual(after.stderr, before.stderr)
        self.assertIn("1 mark open", after.stdout)   # the marks line still works

    def test_the_marks_line_never_changes_the_exit_code(self):
        self.mark()
        red = self.run_contour("check", blender=stub_blender(self.tmp, ok=False))
        self.assertEqual(red.returncode, 1)
        self.assertIn("1 mark open", red.stdout)

    def test_a_green_check_leaves_every_mark_exactly_as_it_was(self):
        """Only the user closes a mark. Green does not dispose of a finding —
        a mark exists precisely because the spec did not catch the thing."""
        self.mark()
        self.mark(status="closed")
        before = (self.space / "marks.json").read_bytes()
        r = self.run_contour("check")
        self.assertEqual(r.returncode, 0)
        self.assertEqual((self.space / "marks.json").read_bytes(), before)

    def test_a_green_check_renders_for_the_page(self):
        """Every build renders; only a checkpoint renders for the agent (ADR
        0019, decision 24). The sheet was rate-limited because it cost the
        agent's context, not because rendering is expensive — and a sheet going
        to a page costs no context at all, so the panel can be current."""
        r = self.run_contour("check")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.stages(), ["build", "render"])

    def test_a_verify_red_check_still_renders(self):
        """Red is the common state inside a fix loop, and a red verify has
        geometry: the build saved before verify judged it. The wrong model is
        exactly what the user needs to see, so the panel shows it. What must
        never be drawn is a scene that was never finished — that is the next
        test, and it is a different event."""
        r = self.run_contour("check", blender=stub_blender(self.tmp, ok=False))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.stages(), ["build", "render"])

    def test_the_check_report_says_nothing_about_the_render(self):
        """The render is for the page, and the page costs no context. If the
        check's report named it — or named the sheet — the agent would be
        invited to read a picture outside a checkpoint, which is the one thing
        ADR 0019's decision 24 keeps intact while making the panel current."""
        r = self.run_contour("check")
        self.assertEqual(r.returncode, 0)
        self.assertIn("stub ran build", r.stdout)
        self.assertNotIn("render", r.stdout)
        self.assertNotIn("sheet", r.stdout)

    def test_resolving_waits_for_whoever_is_holding_the_space(self):
        """Resolution reads the build and rewrites `marks.json`, so a build
        running underneath it would move the geometry its rays are aimed at. It
        takes the same hold every other stage takes rather than a lock of its
        own — and the console's own resolve is not refused by the run that asked
        for it, because a run's hold is re-entrant within that run (slice 02).
        """
        sys.path.insert(0, str(ROOT))
        from lib import lock
        held = lock.take(self.space, "another terminal's check")
        refused = self.run_contour("resolve")
        self.assertEqual(refused.returncode, 3, refused.stdout + refused.stderr)
        self.assertIn("is held by", refused.stderr)
        self.assertEqual(self.stages(), [], "it cast rays into a live build")
        mine = self.run_contour("resolve", run=held["run"])
        self.assertEqual(mine.returncode, 0, mine.stdout + mine.stderr)
        self.assertEqual(self.stages(), ["resolve"])

    def test_the_canvas_still_resolves_at_session_close_without_a_console(self):
        """ADR 0018's trigger, kept for the host that has no better one.

        The console resolves at the instant it approves a build, because it owns
        the build and so knows when geometry is about to change (ADR 0019,
        decision 10). `contour canvas` owns no build and cannot know that, so for
        it the last moment before anything can change is still the moment the
        user says Done.
        """
        (self.space / "sheet.png").write_bytes(b"\x89PNG\r\n\x1a\npixels")
        self.mark()
        quiet = self.tmp / "no-browser"
        quiet.write_text("#!/bin/sh\nexit 0\n")     # $BROWSER, so none opens
        quiet.chmod(0o755)
        proc = subprocess.Popen(
            [sys.executable, str(CONTOUR), "canvas"], cwd=str(self.space),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            env=dict(os.environ, BLENDER=str(stub_blender(self.tmp)),
                     BROWSER=str(quiet)))
        self.addCleanup(proc.stdout.close)     # a pipe is a file, and it is ours
        self.addCleanup(proc.kill)
        url = re.search(r"http://\S+", proc.stdout.readline()).group(0)
        origin, token = url.split("/?")[0], url.split("t=")[1]
        done = urllib.request.Request(
            origin + "/done", data=b"{}", method="POST",
            headers={"X-Contour-Token": token,
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(done, timeout=10) as r:
            r.read()
        said = proc.stdout.read()
        self.assertEqual(proc.wait(timeout=30), 0, said)
        self.assertEqual(self.stages(), ["resolve"], said)

    def test_a_build_that_never_finished_renders_nothing(self):
        """The most dangerous option available, refused: a picture of a model
        that has never existed, in the panel where every other picture is real.
        A `build.py` that raised leaves the scene unfinished and the previous
        `.blend` untouched, so there is nothing new to draw and drawing anyway
        would draw whatever half a scene happens to hold (ADR 0019, 27)."""
        r = self.run_contour("check", blender=stub_blender(self.tmp, crash=True))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.stages(), ["build"])


class SpacesTest(unittest.TestCase):
    """`contour spaces`, in both its forms, over spaces `contour init` made in
    a temporary directory that `$CONTOUR_SPACES` points at (slice 28)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                                   capture_output=True, text=True).stdout.strip()

    def contour(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(CONTOUR), *args],
                              cwd=str(cwd or self.tmp),
                              env=dict(os.environ, CONTOUR_SPACES=str(self.tmp)),
                              capture_output=True, text=True, timeout=60)

    def init(self, name):
        r = self.contour("init", name)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return self.tmp / name

    def listing(self):
        r = self.contour("spaces", "--json")
        self.assertEqual(r.returncode in (0, 1), True, r.stderr)
        return json.loads(r.stdout)["spaces"]

    def test_the_text_form_reads_exactly_as_it_did(self):
        """Pinned before the JSON form existed, against the code as it was:
        the lobby is a second rendering of one reading and must not move the
        first (ADR 0021, decision 3)."""
        alpha, beta = self.init("alpha"), self.init("beta")
        (alpha / ".contour" / "project").write_text("# no toolkit line\n")
        subprocess.run(["git", "-C", str(beta), "remote", "add", "origin", "x"], check=True)
        r = self.contour("spaces")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "".join([
            f"  alpha        {str(alpha):<34} toolkit ? (unknown)     0 commits\n",
            f"  beta         {str(beta):<34} toolkit {self.head} (current)     0 commits\n",
            "  WARN beta has a remote (origin) — a model space is never pushed\n"]))
        r = self.contour("spaces", "beta")
        self.assertEqual((r.returncode, r.stdout), (0, f"{beta}\n"))

    def test_the_json_form_lists_every_space_the_text_form_lists(self):
        """Name and path, and no others: a directory that only looks like a
        space, with no marker, is in neither."""
        alpha, beta = self.init("alpha"), self.init("beta")
        (self.tmp / "gamma" / ".contour").mkdir(parents=True)
        self.assertEqual([(s["name"], s["path"]) for s in self.listing()],
                         [("alpha", str(alpha)), ("beta", str(beta))])

    def test_a_fresh_space_is_current_and_in_step(self):
        """What `contour init` leaves behind is the healthy row: this toolkit,
        nothing committed, no remote, scaffolding as the template wrote it, and
        a copy of the rules of its own."""
        self.init("alpha")
        [row] = self.listing()
        self.assertEqual({k: row[k] for k in ("toolkit", "commits", "remotes",
                                              "scaffold", "rules")},
                         {"toolkit": {"commit": self.head, "state": "current"},
                          "commits": 0, "remotes": [],
                          "scaffold": {"drift": [], "missing": []}, "rules": True})

    def test_drifted_and_missing_scaffolding_is_what_doctor_would_say(self):
        """The same findings `contour doctor` prints in that space, as data."""
        alpha = self.init("alpha")
        with open(alpha / "CLAUDE.md", "a") as f:
            f.write("\nan edit the template never made\n")
        (alpha / ".claude" / "skills" / "release-model" / "SKILL.md").unlink()
        [row] = self.listing()
        self.assertEqual(row["scaffold"],
                         {"drift": ["CLAUDE.md"],
                          "missing": [".claude/skills/release-model/SKILL.md"]})
        said = self.contour("doctor", cwd=alpha).stdout
        self.assertIn("DRIFT CLAUDE.md", said)
        self.assertIn("MISS .claude/skills/release-model/SKILL.md", said)

    def test_a_space_with_a_remote_is_reported_and_fails_the_listing(self):
        """Rule 8 is a warning in the text form and an exit code in both: a
        client reading the JSON gets the same non-zero a person does."""
        beta = self.init("beta")
        subprocess.run(["git", "-C", str(beta), "remote", "add", "origin", "x"], check=True)
        r = self.contour("spaces", "--json")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads(r.stdout)["spaces"][0]["remotes"], ["origin"])

    def test_no_spaces_is_an_empty_list_and_not_an_error(self):
        """The lobby's empty state is onboarding, not a failure (ADR 0021,
        decision 1)."""
        r = self.contour("spaces", "--json")
        self.assertEqual((r.returncode, json.loads(r.stdout)["spaces"]), (0, []))

    def test_a_marker_that_names_no_toolkit_is_unknown(self):
        """No commit to compare, so neither current nor behind; the text form
        prints `?` for the same reading."""
        alpha = self.init("alpha")
        (alpha / ".contour" / "project").write_text("# no toolkit line\n")
        [row] = self.listing()
        self.assertEqual(row["toolkit"], {"commit": None, "state": "unknown"})

    def test_a_space_outside_the_toolkit_with_no_rules_of_its_own_cannot_see_them(self):
        """Open question 13: Claude Code walks up for `CLAUDE.md`, and from a
        temporary directory the toolkit's is not on the way."""
        alpha = self.init("alpha")
        (alpha / "CLAUDE.md").unlink()
        [row] = self.listing()
        self.assertFalse(row["rules"])
        self.assertEqual(row["scaffold"]["missing"], ["CLAUDE.md"])


if __name__ == "__main__":
    unittest.main()
