"""The agent's own marks: a finding as a badge, not as a paragraph (ADR 0018).

The canvas was built so the user could point at the build. This is the return
path: the agent pins what it already computes, and the finding arrives on the
picture. The discipline the ADR sets is that a mark is a question or a
measurement, never narration — a canvas that fills with the agent describing
what it did is a canvas the user stops opening.

What is under test here is the half of that which is enforceable: that an agent
mark is authored as one, points where the agent actually knows something, and
can never be the thing that closes itself.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
CONTOUR = ROOT / "contour"


class AgentMarkTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.space = self.tmp / "widget"
        (self.space / ".contour").mkdir(parents=True)
        (self.space / ".contour" / "project").write_text("toolkit: stub\n")
        self.marks = self.space / "marks.json"

    def mark(self, *args):
        return subprocess.run([sys.executable, str(CONTOUR), "mark", *args],
                              cwd=str(self.space), env=dict(os.environ),
                              capture_output=True, text=True, timeout=60)

    def stored(self):
        return json.loads(self.marks.read_text())

    def test_the_agent_can_append_a_mark_and_it_is_authored_as_the_agent(self):
        done = self.mark("--part", "neck", "12 mm gap to torso, spec says flush")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        mark, = self.stored()
        self.assertEqual(mark["author"], "agent")
        self.assertEqual(mark["text"], "12 mm gap to torso, spec says flush")
        self.assertEqual(mark["status"], "open")

    def test_an_agent_mark_names_a_part_and_no_point_on_it(self):
        """The agent has not clicked anything, so it has no pixel and no point
        in any part's own space. What it does have is the part — the same name
        verification and the mask already deal in. Where on that part the badge
        goes is the render's business, decided against the build in front of it
        rather than guessed here."""
        self.mark("--part", "neck", "12 mm gap to torso")
        mark, = self.stored()
        self.assertEqual(mark["part"], "neck")
        self.assertNotIn("anchor", mark)          # a name is not a position
        self.assertNotIn("pixel", mark)
        self.assertNotIn("view", mark)

    def test_the_agent_can_mark_a_reference_too(self):
        """Measuring a reference is exactly the case ADR 0018 was written for:
        the agent read a proportion off the picture, and the user should see
        where. A photograph has no parts, so this one carries a pixel and the
        image, like any ref mark, and is never sent for resolution."""
        done = self.mark("--ref", "persp.webp", "--pixel", "538,821",
                         "leg gap reads 1.4 x leg width here")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        mark, = self.stored()
        self.assertEqual(mark["author"], "agent")
        self.assertEqual(mark["ref"], "persp.webp")
        self.assertEqual(mark["pixel"], [538, 821])
        self.assertNotIn("anchor", mark)

    def build(self, content=b"a blend, for hashing purposes"):
        """A stand-in for `out/widget.blend`: what is under test is that the
        build Contour stamps is the build on disk, not what is inside it."""
        out = self.space / "out"
        out.mkdir(exist_ok=True)
        (out / "widget.blend").write_bytes(content)

    def test_the_agent_can_say_a_finding_is_addressed_and_contour_names_the_build(self):
        """The agent passes a flag and nothing else. The build id is the one
        Contour already computes for `views.json`, so the agent cannot invent a
        number, and a later reader can tell whether the build has moved on since
        the claim was made."""
        from lib import anchor
        self.build()
        self.mark("--part", "neck", "12 mm gap to torso")
        done = self.mark("--addressed", "m1")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        mark, = self.stored()
        self.assertEqual(mark["addressed"],
                         anchor.fingerprint(self.space / "out" / "widget.blend"))

    def test_saying_it_is_addressed_is_not_saying_it_is_closed(self):
        """A finding is not disposed of by the party it is aimed at. The badge
        dims; the finding stands until the user closes it (ADR 0018)."""
        self.build()
        self.mark("--part", "neck", "12 mm gap to torso")
        self.mark("--addressed", "m1")
        mark, = self.stored()
        self.assertEqual(mark["status"], "open")

    def test_an_addressed_finding_is_still_an_open_finding(self):
        """`contour check` counts what is outstanding. The agent believing it
        has fixed something is not the same as the user agreeing, and the line
        the user reads must not quietly shrink because the agent says so."""
        from lib import marks as marks_store
        self.build()
        self.mark("--part", "neck", "12 mm gap to torso")
        self.mark("--part", "arm_L", "origin sits 1 m from the arm")
        self.assertEqual(marks_store.status_line(self.marks), "2 marks open")
        self.mark("--addressed", "m1")
        self.assertEqual(marks_store.status_line(self.marks), "2 marks open")

    def parts(self, *names):
        out = self.space / "out"
        out.mkdir(exist_ok=True)
        (out / "parts.json").write_text(
            json.dumps({str(i + 1): n for i, n in enumerate(names)}))

    def test_a_part_the_build_does_not_have_is_refused(self):
        """A mark that names nothing is worse than no mark: it draws no badge,
        it cannot be orphaned, and it sits in the file looking like a finding.
        The agent is the party most able to typo a part name and least able to
        notice, so the name is checked against the build's own table."""
        self.parts("neck", "torso", "arm_L")
        done = self.mark("--part", "wing", "this part does not exist")
        self.assertEqual(done.returncode, 1)
        self.assertIn("wing", done.stdout)
        self.assertFalse(self.marks.exists())

    def test_a_space_that_has_never_been_rendered_is_taken_at_its_word(self):
        """There is no table to check against, so there is nothing to refuse
        with. Silence is not evidence of a bad name."""
        done = self.mark("--part", "neck", "12 mm gap to torso")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(self.stored()), 1)

    def test_no_agent_path_can_close_a_mark(self):
        """Only the user closes a finding, because a finding is not disposed of
        by the party it is aimed at (ADR 0018). Auto-closing on a green check
        was rejected outright in the ADR: a mark exists precisely because the
        spec did not catch the thing, so green would erase the findings that
        matter most.

        A guard. `lib/agent` has no function that writes a status, and this is
        what will notice if one ever appears.
        """
        from lib import agent
        self.build()
        self.mark("--part", "neck", "12 mm gap to torso")
        for args in (["--close", "m1"], ["--status", "closed", "m1"],
                     ["--addressed", "m1"]):
            self.mark(*args)
            mark, = self.stored()
            self.assertEqual(mark["status"], "open", args)
        self.assertFalse([n for n in dir(agent) if "clos" in n.lower()])

    def test_writing_a_mark_writes_neither_the_spec_nor_the_references(self):
        """An agent mark is a proposal, never an edit. Rule 1 is untouched by
        it: propose, the user confirms, then the spec is written with
        `revision:` bumped. The canvas makes a proposal visible; it does not
        become the gate.

        A guard, like the one above, and for the same reason: `lib/agent`
        imports nothing that can write either of them.
        """
        spec = self.space / "spec.yaml"
        spec.write_text("model: widget\nrevision: 3\n")
        refs = self.space / "refs"
        refs.mkdir()
        (refs / "persp.webp").write_bytes(b"\x89PNG\r\n\x1a\nreference")
        before = {p.relative_to(self.space): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in [spec, refs / "persp.webp"]}
        self.parts("neck")
        self.build()
        self.mark("--part", "neck", "12 mm gap to torso")
        self.mark("--ref", "persp.webp", "--pixel", "538,821", "leg gap reads wide")
        self.mark("--addressed", "m1")
        after = {p.relative_to(self.space): (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in [spec, refs / "persp.webp"]}
        self.assertEqual(after, before)
        self.assertEqual(sorted(p.name for p in refs.iterdir()), ["persp.webp"])

    def test_agent_marks_prune_by_the_same_rule_as_the_users(self):
        """One rule, not two. A closed finding the last release tag already
        holds is dropped whoever wrote it, and an open one is never dropped at
        any age, whoever wrote it — an unanswered finding does not expire and
        does not expire faster for having come from the agent (0018-2)."""
        from lib import marks as marks_store
        git = lambda *a: subprocess.run(("git",) + a, cwd=str(self.space),
                                        capture_output=True, text=True)
        git("init", "-q")
        git("config", "user.email", "t@t"), git("config", "user.name", "t")
        self.mark("--part", "neck", "closed, and released")
        self.mark("--part", "torso", "open, and released")
        marks_store.close(self.marks, "m1")
        git("add", "-A"), git("commit", "-qm", "release")
        git("tag", "v1")

        dropped = marks_store.prune(self.marks)
        self.assertEqual(dropped, "1 mark pruned, closed at v1")
        kept, = self.stored()
        self.assertEqual((kept["id"], kept["author"]), ("m2", "agent"))


class AgentBadgeTest(unittest.TestCase):
    """Where an agent's badge goes, which is the one thing about these marks
    that geometry decides. The fixture cannot make this claim — every part of
    it is centred on its own origin, so it cannot tell the right answer from
    the wrong one — so it is made here, against corners written by hand.
    """

    def test_a_badge_lands_on_a_part_that_is_not_convex(self):
        """beaky's arm is an L — up from the shoulder, out, and down — so the
        middle of its pixels is in the hole beside the torso, on background.
        This is the case that made the fixture an insufficient witness: a box
        and a sphere are both convex and cannot fail it."""
        from lib import anchor
        arm = ell()
        self.assertNotIn((mean(arm, 0), mean(arm, 1)), arm)   # the trap
        self.assertIn(anchor.nearest(arm), arm)

    def test_and_it_is_the_nearest_such_pixel_to_the_middle(self):
        """Not just any pixel of the part. A badge at the far tip of an arm is
        on the arm and still the wrong place to leash a remark about it."""
        from lib import anchor
        arm = ell()
        mx, my = mean(arm, 0), mean(arm, 1)
        best = min((p[0] - mx) ** 2 + (p[1] - my) ** 2 for p in arm)
        got = anchor.nearest(arm)
        self.assertAlmostEqual((got[0] - mx) ** 2 + (got[1] - my) ** 2, best)


def ell():
    """An L of pixels: up one side, then out along the bottom."""
    return ([(0, y) for y in range(10)] + [(x, 0) for x in range(1, 10)])


def mean(points, i):
    return sum(p[i] for p in points) / len(points)


if __name__ == "__main__":
    unittest.main()
