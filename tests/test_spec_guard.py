"""The guard asks what a call means, and keeps its own policy (ADR 0019, decision 20).

Rule 1 rests on this layer, not on the console's gate: a space's `PreToolUse`
hook fires before the SDK consults `can_use_tool`, so the guard is what stops a
reference being rewritten whatever the ask-list says. That is why it denies where
the gate only asks, and why the strict layer being the *narrower* one inverted
the design — a `Write` to a nested `refs/` was gated by the console and allowed
here, and `cat > refs/side.jpg` was invisible.

So the category comes from `lib.intent` and the policy stays here: tracked is
denied, untracked is how a space starts (ADR 0012). ADR 0016 explains why the
spec half of this guard left.

Driven the way the hook drives it — the PreToolUse JSON on stdin, the exit code
out — because that contract is the whole interface and a space never imports it.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import intent

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "tools" / "guards" / "spec.py"
CONTOUR = ROOT / "contour"

DENY = 2                       # exit 2 denies and shows stderr to the agent


class SpecGuardTest(unittest.TestCase):
    def setUp(self):
        self.space = Path(tempfile.mkdtemp()) / "widget"
        r = subprocess.run([sys.executable, str(CONTOUR), "init", "widget"],
                           cwd=str(self.space.parent), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.space), *args],
                              capture_output=True, text=True)

    def commit(self, rel, body=b"jpeg"):
        """A reference the user supplied: on disk and in the index."""
        path = self.space / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        self.assertEqual(self.git("add", rel).returncode, 0)
        return path

    def guard(self, tool, payload, env=None):
        ev = json.dumps({"cwd": str(self.space), "tool_name": tool,
                         "tool_input": payload})
        return subprocess.run([sys.executable, str(GUARD)], input=ev,
                              capture_output=True, text=True,
                              env=dict(os.environ, CLAUDE_PROJECT_DIR=str(self.space),
                                       **(env or {})))

    def test_a_write_to_a_nested_reference_is_denied(self):
        """The hole this slice closes. The guard read `refs` as the *first*
        component, so a user who kept a variant's references beside it had rule 1
        silently not apply to them — while the console's gate, reading any `refs`
        component, stopped the same write. The strict layer was the narrow one.
        """
        self.commit("variants/tall/refs/front.png")
        r = self.guard("Write",
                       {"file_path": str(self.space / "variants/tall/refs/front.png")})
        self.assertEqual(r.returncode, DENY, r.stdout + r.stderr)
        self.assertIn("variants/tall/refs/front.png", r.stderr)

    def test_a_shell_call_writing_a_tracked_reference_is_denied(self):
        """`cat > refs/front.png` was invisible: the guard read
        `tool_input.file_path` and a Bash call has none. A rule enforced against
        one tool and not the tool an agent in auto mode reaches for first is not
        enforced. The path is named because *which* reference decides what the
        agent does next — measure that one and propose a revision."""
        self.commit("refs/front.png")
        for call in ("cat sketch.png > refs/front.png",
                     "cp ~/Downloads/new.png refs/front.png",
                     "python3 -c \"open('refs/front.png','wb').write(b'')\""):
            with self.subTest(call=call):
                r = self.guard("Bash", {"command": call})
                self.assertEqual(r.returncode, DENY, r.stdout + r.stderr)
                self.assertIn("refs/front.png", r.stderr)

    def test_saving_a_new_reference_is_allowed_through_either_tool(self):
        """How a space starts, and the reason the policy is trackedness and not
        the path. A guard that denied this would deny the first thing anyone does
        in a fresh space, and would be removed within the day."""
        self.assertEqual(
            self.guard("Write", {"file_path": str(self.space / "refs/front.png")}
                       ).returncode, 0)
        r = self.guard("Bash", {"command": "cp ~/Downloads/side.jpg refs/side.jpg"})
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_tracked_reference_beside_an_untracked_one_is_still_denied(self):
        """One call, several references: the answer is per reference, so a
        tracked one does not get through by being named second."""
        self.commit("refs/front.png")
        r = self.guard("Bash", {"command": "cp a refs/new.png refs/front.png"})
        self.assertEqual(r.returncode, DENY, r.stdout + r.stderr)
        self.assertIn("refs/front.png", r.stderr)

    def test_a_shell_call_that_only_reads_a_reference_is_allowed(self):
        """Measuring a reference is the sanctioned thing to do with one — rule 1
        says measure them, never rewrite one. A guard that fired on every `cat`
        would make the sanctioned act the noisy one."""
        self.commit("refs/front.png")
        for call in ("cat refs/front.png", "git diff refs/front.png",
                     "./contour measure refs/front.png"):
            with self.subTest(call=call):
                r = self.guard("Bash", {"command": call})
                self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_reference_git_cannot_be_asked_about_is_denied(self):
        """An error is not an answer. The guard's whole policy is trackedness, so
        a guard that guessed *untracked* when it could not ask would allow the
        write it exists to stop — and would do it exactly when something is
        already wrong. This path is what makes the reference to it in `tracked`
        load-bearing rather than decorative.
        """
        self.space.joinpath("refs/new.png").write_bytes(b"png")   # untracked
        r = self.guard("Write", {"file_path": str(self.space / "refs/new.png")},
                       env={"PATH": ""})
        self.assertEqual(r.returncode, DENY, r.stdout + r.stderr)
        self.assertIn("cannot ask git", r.stderr)

    def test_an_unparseable_call_is_denied_only_if_it_names_a_reference(self):
        """`classify` raises on a call it cannot split, which is right for a gate
        — None there would mean *not gated*. A guard must answer, and both
        answers are available: deny when the text names a tracked reference, and
        allow otherwise, because `echo it's fine` is a quoting accident the guard
        has no business refusing.
        """
        self.commit("refs/front.png")
        r = self.guard("Bash", {"command": 'cp new.png refs/front.png "'})
        self.assertEqual(r.returncode, DENY, r.stdout + r.stderr)
        self.assertIn("refs/front.png", r.stderr)
        self.assertEqual(self.guard("Bash", {"command": "echo it's fine"}).returncode, 0)

    def test_writing_the_spec_is_not_this_guards_business(self):
        """ADR 0016 sanctioned a confirmed spec write, so a blanket deny here
        would refuse the sanctioned path. The spec is guarded by `contour check`
        comparing it against HEAD — prevention became detection, knowingly.

        Weaker than the others by construction: it passes both because the
        category is not a ref write and because no reference is named, so only
        reinstating the blanket deny whole breaks it. Kept for what it records.
        """
        self.commit("spec.yaml", b"height: 200\n")
        self.assertEqual(
            self.guard("Write", {"file_path": str(self.space / "spec.yaml")}
                       ).returncode, 0)


# Tools a space's agent could rewrite a reference with. A roster and not an
# inference: the question is which tools *exist* to be matched, which no module
# here knows. A tool nobody decided about is a finding.
COULD_WRITE = {
    "Write": "the plain spelling",
    "Edit": "the same intent through a different tool",
    "Bash": "a heredoc or a redirect, which is how an agent in auto mode writes",
    "NotebookEdit": "not classified today; here so that teaching `intent` about "
                    "it fails this test rather than silently missing the hook",
}


class MatcherTest(unittest.TestCase):
    """The guard can only judge a call it is handed (ADR 0019, decision 20).

    A guard that reads Bash calls correctly and a hook that never passes one is
    the same hole in a different place — and it is the quieter place, because the
    tests of the guard all pass.
    """

    def matcher(self):
        settings = json.loads((ROOT / "templates" / "space" / ".claude"
                               / "settings.json").read_text())
        pre = settings["hooks"]["PreToolUse"]
        spec = [e for e in pre if any("hook spec" in h.get("command", "")
                                      for h in e["hooks"])]
        self.assertEqual(len(spec), 1, "one entry runs the spec guard")
        return spec[0]["matcher"].split("|")

    def test_the_hook_is_handed_every_tool_that_can_write_a_reference(self):
        """Derived from `intent` rather than listed, so the day a tool starts
        classifying as a ref write is the day this fails."""
        reference = {"file_path": "/m/widget/refs/front.png",
                     "command": "cp a refs/front.png"}
        missed = [tool for tool in sorted(COULD_WRITE)
                  if intent.classify(tool, reference) == "ref-write"
                  and tool not in self.matcher()]
        self.assertEqual(missed, [], "add these to the PreToolUse matcher, or "
                                     "rule 1 is unenforced for them")


if __name__ == "__main__":
    unittest.main()
