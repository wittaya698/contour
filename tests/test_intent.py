"""What a call *means*, in Contour's vocabulary (ADR 0019, decision 20).

The gate asks the launcher rather than pattern-matching the call's text,
because one intent has several spellings and a permission list needing one
rule per spelling will still have a hole — and a gap in that list is a rule
that has silently stopped being enforced.

These drive `classify` the way the console's gate will: a tool name and the
input the SDK handed over, unchanged.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import intent


class ClassifyTest(unittest.TestCase):
    def test_every_spelling_of_a_build_is_one_category(self):
        """The four in the ADR: with and without the `./`, a `cd` into the
        space first, and `render`, which builds on the way to the sheet."""
        for call in ("./contour check", "contour check",
                     "cd widget && ./contour check", "contour render"):
            self.assertEqual(intent.classify("Bash", {"command": call}),
                             "build", call)

    def test_writing_the_spec_is_its_own_category(self):
        """Rule 1's subject: a spec changes only as propose -> confirm -> write,
        and under a console the confirm is the gate. Edit and Write are the same
        intent, so the tool name is not the thing that decides."""
        for tool in ("Write", "Edit"):
            self.assertEqual(
                intent.classify(tool, {"file_path": "/m/widget/spec.yaml"}),
                "spec-write", tool)

    def test_writing_a_reference_is_its_own_category(self):
        """Not because it is approvable — rule 1 says no measurement argument
        justifies rewriting a reference, and the guard keeps denying it. It is
        a category so that *every* category can be gated, which is what makes
        the strictest list definable at all."""
        said = intent.classify("Write", {"file_path": "/m/widget/refs/front.png"})
        self.assertEqual(said, "ref-write")

    def test_gits_own_refs_are_not_the_users_references(self):
        """Every space has a second directory called `refs`, and it holds
        branch heads. A gate that asked about rewriting a reference image when
        git moved a branch would be asking about the wrong thing, and a gate
        that asks about the wrong thing is one the user learns to click."""
        said = intent.classify("Write", {"file_path": "/m/widget/.git/refs/heads/main"})
        self.assertNotEqual(said, "ref-write")

    def test_a_commit_is_a_commit_wherever_the_repo_is_named(self):
        """Rule 5's subject. `git -C` is the spelling that reaches a space from
        outside it, so a rule keyed on the words `git commit` adjacent misses
        exactly the call made from the toolkit into a model space."""
        for call in ('git commit -m "widget: taller cap"',
                     'git -C widget commit -m "x"',
                     'cd widget && git commit --amend --no-edit'):
            self.assertEqual(intent.classify("Bash", {"command": call}),
                             "commit", call)

    def test_a_push_is_its_own_category_not_a_kind_of_commit(self):
        """A commit is local and a push leaves the machine, which is why rule 5
        names them together and rule 8 names only one. The ask-list has to be
        able to let one through and hold the other."""
        for call in ("git push", "git push --force origin main",
                     "git -C widget push -u origin HEAD"):
            self.assertEqual(intent.classify("Bash", {"command": call}),
                             "push", call)

    def test_carrying_no_intent_is_not_the_same_answer_as_unreadable(self):
        """The ask-list is an allow-list: None means the call is not gated and
        runs. So a call this module could not read must not come back as None,
        or a quoting accident around `git push` becomes a silent allow."""
        self.assertIsNone(intent.classify("Bash", {"command": "ls -la out/"}))
        self.assertIsNone(intent.classify("Read", {"file_path": "/m/widget/build.py"}))
        with self.assertRaises(ValueError):
            intent.classify("Bash", {"command": 'git push "origin'})

    def test_an_unreadable_call_says_which_call(self):
        """This message reaches a person at a gate, and `No closing quotation`
        on its own names neither the call nor the fact that nothing was
        classified."""
        with self.assertRaises(ValueError) as caught:
            intent.classify("Bash", {"command": 'git push "origin'})
        self.assertIn('git push "origin', str(caught.exception))
    def test_a_call_wrapped_in_contour_run_keeps_its_intent(self):
        """`contour run` holds the space for whatever is inside it, so the
        intent is the inner call's. This is what INTENTLESS means when it
        exempts `run` itself."""
        self.assertEqual(intent.classify("Bash", {"command": "contour run ./contour check"}),
                         "build")
        self.assertEqual(intent.classify("Bash", {"command": "contour run git push"}),
                         "push")

    def test_a_call_inside_a_nested_shell_keeps_its_intent(self):
        """`bash -c "git push"` is one word to anything splitting on spaces, and
        an agent reaching for a subshell is ordinary rather than evasive — a
        gate that misses it is a rule that has stopped being enforced."""
        self.assertEqual(intent.classify("Bash", {"command": 'bash -c "git push"'}),
                         "push")
        self.assertEqual(intent.classify("Bash", {"command": "sh -c 'cd widget && ./contour check'"}),
                         "build")

    def test_a_call_inside_a_substitution_keeps_its_intent(self):
        """A substitution is a whole call inside one word. The first spelling is
        how an agent captures output it wants to read; both run."""
        self.assertEqual(intent.classify("Bash", {"command": 'echo "$(./contour check)"'}),
                         "build")
        self.assertEqual(intent.classify("Bash", {"command": "echo `git push`"}),
                         "push")

    def test_writing_the_spec_through_the_shell_is_still_a_spec_write(self):
        """The tool name is not the intent. An agent editing a file with `sed`
        or a heredoc — which is how an agent in auto mode edits everything —
        never issues a Write, and rule 1 does not care which tool was used."""
        for call in ('echo "height: 210" > spec.yaml',
                     "sed -i '' 's/200/210/' widget/spec.yaml",
                     "python3 - <<'EOF'\nopen('spec.yaml', 'w').write(x)\nEOF"):
            self.assertEqual(intent.classify("Bash", {"command": call}),
                             "spec-write", call)

    def test_reading_the_spec_through_the_shell_is_not_a_write(self):
        """A gate that fires on every `cat spec.yaml` is a gate the user learns
        to dismiss, which costs more than the one it was protecting."""
        for call in ("cat spec.yaml", "grep revision widget/spec.yaml",
                     "git diff spec.yaml"):
            self.assertIsNone(intent.classify("Bash", {"command": call}), call)

    def test_a_compound_call_is_classified_by_its_highest_stakes_intent(self):
        """One call, one answer — and chaining a gated write onto a build must
        not let the write through because the build was seen first. The order
        the categories are declared in is the order of stakes."""
        said = intent.classify("Bash", {"command":
            "sed -i '' 's/200/210/' spec.yaml && ./contour check"})
        self.assertEqual(said, "spec-write")


# Launcher commands that carry no intent, each for a stated reason. This is a
# roster and not an inference: a command is exempt because somebody decided it
# is, so a command nobody decided about is a finding rather than a default.
INTENTLESS = {
    "api": "reads a signature out of Blender and writes nothing",
    "measure": "reads pixels out of a reference image; never writes one",
    "canvas": "serves the sheet and takes marks — the user's own writes",
    "mark": "the agent pinning a finding, which is what it is for",
    "run": "carries whatever the call inside it carries, tested separately",
    "selftest": "builds the toolkit's own fixture, never the user's model",
    "install-hooks": "installs the push guard; refusing it protects nothing",
    "init": "creates a space, and there is no space yet to have policy about",
    "doctor": "compares a space against the toolkit and writes nothing",
    "spaces": "lists spaces on this machine",
    "intents": "prints this very vocabulary",
    "hook": "is a guard, run by git and Claude Code rather than by an agent",
}


class RosterTest(unittest.TestCase):
    def commands(self):
        """Every subcommand the launcher documents, from its own help table."""
        usage = subprocess.run([sys.executable, str(ROOT / "contour"), "--help"],
                               capture_output=True, text=True, timeout=60).stdout
        return sorted({line.split()[1] for line in usage.splitlines()
                       if line.startswith("    contour ")})

    def test_every_launcher_command_is_classified_or_declared_intentless(self):
        """A launcher command that carries an intent and is not classified is a
        gate that silently does not exist — which is the failure this whole
        category vocabulary is here to prevent."""
        stranded = [cmd for cmd in self.commands()
                    if cmd not in INTENTLESS
                    and intent.classify("Bash", {"command": f"./contour {cmd}"}) is None]
        self.assertEqual(stranded, [], "classify these, or say why they are "
                                       "intentless in INTENTLESS")


class EnumerateTest(unittest.TestCase):
    """Slice 05's file is meaningful only against the current set of
    categories, and a list that cannot be printed cannot be audited."""

    def intents(self, cwd=None, env=None):
        return subprocess.run([sys.executable, str(ROOT / "contour"), "intents"],
                              cwd=str(cwd or ROOT), env=env, capture_output=True,
                              text=True, timeout=60)

    def test_the_launcher_prints_the_categories_it_knows(self):
        r = self.intents()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split(), list(intent.categories()))
        self.assertIn("build", r.stdout.split())

    def test_the_order_does_not_move_between_runs(self):
        """An audit compares two lists; one that reorders itself makes every
        comparison a diff."""
        self.assertEqual(self.intents().stdout, self.intents().stdout)

    def test_the_list_prints_with_no_blender_and_from_anywhere(self):
        """The console asks for this before it has a space, and the gate asks
        what a call means on every call. Neither can afford a Blender run, and
        BLENDER pointing at nothing must not matter."""
        r = self.intents(cwd=tempfile.mkdtemp(),
                         env=dict(os.environ, BLENDER="/nowhere/blender"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split(), list(intent.categories()))


if __name__ == "__main__":
    unittest.main()
