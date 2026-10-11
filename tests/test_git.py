"""`lib/git.py`: the questions this toolkit asks git, each asked once.

Five wrappers used to ask them — `lib/marks.py`, `console/vetoes.py`, `contour`,
and eight ad-hoc calls inside the launcher — and three of them independently
decided that a non-zero exit means *no answer* rather than an error. The
duplication was never the defect; the divergence was (ADR 0019, decision 37).

So the tests here are about the answers and about the silences: what each
question returns when git can answer it, and what it returns when there is no
repository, no commit, no git at all. A repository is built on disk for each one
— asking git what git says is the only thing worth asserting here.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import git


class GitCase(unittest.TestCase):
    """A repository on disk, made the way a space is made."""

    def repo(self, **files):
        where = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", str(where)], check=True)
        for name, body in files.items():
            got = where / name.replace("__", "/")
            got.parent.mkdir(parents=True, exist_ok=True)
            got.write_text(body)
        if files:
            # Dated, not clocked. A test that lets the machine time-stamp its
            # own history cannot then say one thing happened after another.
            self.commit(where, "first", when="2026-01-01T09:00:00")
        return where

    def commit(self, where, message, when=None):
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
               "PATH": __import__("os").environ.get("PATH", "")}
        if when:
            # A lightweight tag's creatordate is its commit's, so this is how a
            # test says one tag was cut after another rather than in the same
            # second as it.
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
        subprocess.run(["git", "-C", str(where), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(where), "commit", "-q", "-m", message],
                       check=True, env=env)

    def bare_ground(self):
        """A directory that is not a repository — which is most of the cases
        these questions are actually asked in: a space before `contour init`,
        a clone someone unzipped."""
        return Path(tempfile.mkdtemp())


class ShowTest(GitCase):

    def test_a_ref_gives_back_the_file_as_it_held_it(self):
        """What both archive readers are for: the tag *is* the archive of closed
        marks, and `HEAD` is what says which vetoes are committed. Neither
        stamps a claim of its own — git is asked what it actually holds."""
        where = self.repo(**{".contour__marks.json": '[{"id": "m1"}]\n'})
        (where / ".contour" / "marks.json").write_text('[{"id": "m2"}]\n')
        self.assertEqual(git.show(where, "HEAD", ".contour/marks.json"),
                         '[{"id": "m1"}]\n')

    def test_the_file_comes_back_byte_for_byte(self):
        """Unstripped, because one caller compares a spec against `HEAD` to ask
        whether it moved, and a trailing newline stripped off one side of that
        comparison is a spec change nobody made."""
        where = self.repo(**{"spec.yaml": "revision: 3\n\n"})
        self.assertEqual(git.show(where, "HEAD", "spec.yaml"), "revision: 3\n\n")

    def test_a_path_the_ref_does_not_hold_is_no_answer_at_all(self):
        """Not an empty file. The launcher reads *nothing there* as *this spec
        is new, and creation is not mutation*; an empty string would be a spec
        that had been emptied, which is a change it must report."""
        where = self.repo(**{"spec.yaml": "revision: 3\n"})
        self.assertIsNone(git.show(where, "HEAD", "refs/side.jpg"))

    def test_a_directory_that_is_no_repository_is_no_answer_either(self):
        """A space before `contour init`, or a machine with no git: not an
        error to raise at a page, but a place where nothing is committed."""
        self.assertIsNone(git.show(self.bare_ground(), "HEAD", "spec.yaml"))


class ReleasesTest(GitCase):

    def tag(self, where, *names):
        for name in names:
            subprocess.run(["git", "-C", str(where), "tag", name], check=True)

    def test_the_last_release_is_the_highest_n(self):
        """N is one past the highest when a release is cut (ADR 0013), so the
        highest is the last. `v9` cut after `v10` is drift, and drift is
        refused at the next release rather than resolved by a date here. Also
        why it is a number and not text: `v10` sorts under `v9` as text."""
        where = self.repo(**{"spec.yaml": "revision: 1\n"})
        self.tag(where, "v10")
        (where / "spec.yaml").write_text("revision: 2\n")
        self.commit(where, "second", when="2026-06-01T09:00:00")
        self.tag(where, "v9")
        self.assertEqual(git.releases(where), ["v10", "v9"])

    def test_only_v_and_a_number_is_a_release(self):
        """The name is what makes a tag a release, so the near-misses are the
        point: the old `<space>-v<N>` form a rename would orphan, a semver tag,
        and spellings of N a release never makes. Each is the user's own."""
        where = self.repo(**{"spec.yaml": "revision: 1\n"})
        self.tag(where, "v1", "beaky-v2", "v3.0.0", "v0", "v04", "V5",
                 "before-rig-rewrite")
        self.assertEqual(git.releases(where), ["v1"])

    def test_a_space_nobody_has_released_has_nothing_to_archive_into(self):
        """Empty, not None: there is no such thing as a failed question here.
        A space nobody has released is a space with no archive, and the mark
        store prunes nothing."""
        self.assertEqual(git.releases(self.repo(**{"spec.yaml": "x\n"})), [])

    def test_no_repository_has_no_releases_rather_than_an_error(self):
        self.assertEqual(git.releases(self.bare_ground()), [])


class HeadTest(GitCase):

    def test_the_short_hash_of_what_is_checked_out(self):
        """Stamped into every space at `contour init` and read back by `doctor`
        and `spaces`, which is how a space says which toolkit built it."""
        where = self.repo(**{"spec.yaml": "revision: 1\n"})
        full = subprocess.run(["git", "-C", str(where), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        got = git.head(where)
        # A prefix and a short one. `startswith` alone is happy with the whole
        # hash and happier still with the empty string, and the marker line a
        # person reads this off has room for neither.
        self.assertTrue(full.startswith(got), f"{got} is not {full}")
        self.assertTrue(4 <= len(got) < len(full), got)

    def test_a_checkout_with_no_commit_yet_has_no_head(self):
        """None, and the launcher spells it `unknown` at the one place a person
        reads it. A repository with nothing committed is the state `git init`
        leaves behind, so this is the ordinary case and not a broken one."""
        self.assertIsNone(git.head(self.repo()))

    def test_no_repository_has_no_head_either(self):
        self.assertIsNone(git.head(self.bare_ground()))


class CommitsTest(GitCase):

    def test_how_many_commits_the_branch_holds(self):
        """`contour spaces` prints it beside each space — the one number that
        says whether anything has happened in there."""
        where = self.repo(**{"spec.yaml": "revision: 1\n"})
        (where / "spec.yaml").write_text("revision: 2\n")
        self.commit(where, "second")
        self.assertEqual(git.commits(where), 2)

    def test_nothing_committed_counts_as_none_rather_than_no_answer(self):
        """Zero, not None: a fresh space genuinely holds nothing, and the
        column it is printed in is a count. A repository with no commit makes
        `rev-list` fail, which is the divergence this module exists to settle —
        three wrappers each decided what that meant."""
        self.assertEqual(git.commits(self.repo()), 0)
        self.assertEqual(git.commits(self.bare_ground()), 0)


class RemotesTest(GitCase):

    def test_every_remote_this_repository_has(self):
        """The one that matters most: a model space is never pushed, so
        `doctor` and `spaces` both warn when one has grown a remote (rule 8)."""
        where = self.repo(**{"spec.yaml": "x\n"})
        subprocess.run(["git", "-C", str(where), "remote", "add", "origin",
                        "git@example.invalid:someone/beaky.git"], check=True)
        self.assertEqual(git.remotes(where), ["origin"])

    def test_a_space_with_no_remote_says_so_plainly(self):
        """Empty, and a directory that is not a repository is empty too. Both
        are *nothing to warn about*, which is the safe answer in the one
        direction that matters: this question never invents a remote."""
        self.assertEqual(git.remotes(self.repo(**{"spec.yaml": "x\n"})), [])
        self.assertEqual(git.remotes(self.bare_ground()), [])


class HooksTest(GitCase):

    def test_where_this_repository_keeps_its_hooks(self):
        """An absolute path, resolved, because the caller writes files into it.
        Asked of git rather than assumed to be `.git/hooks`: a worktree keeps
        them elsewhere, and the push guard silently ceasing to exist is the
        failure this question is asked to prevent."""
        where = self.repo(**{"spec.yaml": "x\n"})
        got = git.hooks_dir(where)
        self.assertTrue(got.is_absolute())
        self.assertEqual(got, (where / ".git" / "hooks").resolve())

    def test_no_repository_has_nowhere_to_put_a_hook(self):
        """None, and `contour install-hooks` reports it rather than writing a
        guard into a directory nothing will ever read."""
        self.assertIsNone(git.hooks_dir(self.bare_ground()))

    def test_a_hooks_path_override_is_reported_when_one_is_set(self):
        """`core.hooksPath` silently overrides everything installed, so the
        install has to be able to say the guard it just wrote is not the one
        that will run."""
        where = self.repo(**{"spec.yaml": "x\n"})
        self.assertEqual(git.hooks_override(where), "")
        subprocess.run(["git", "-C", str(where), "config", "core.hooksPath",
                        "/tmp/elsewhere"], check=True)
        self.assertEqual(git.hooks_override(where), "/tmp/elsewhere")


class StartTest(GitCase):

    def test_a_new_repository_is_made_where_a_space_is(self):
        """The one write in this module. A model space is its own repository
        (ADR 0015), and `contour init` makes it."""
        where = self.bare_ground()
        self.assertIsNone(git.start(where))
        self.assertTrue((where / ".git").is_dir())

    def test_a_repository_that_cannot_be_made_says_why(self):
        """The one question here that reports rather than shrugs, because a
        space with no repository is not a space and the caller stops. It
        returns the message git gave, so the report names the real cause."""
        # Under a regular file, which is the one thing `git init` will not
        # make a directory inside of — it creates missing parents happily.
        blocked = Path(tempfile.mkdtemp()) / "spec.yaml"
        blocked.write_text("revision: 1\n")
        said = git.start(blocked / "space")
        self.assertIsInstance(said, str)
        self.assertTrue(said)


if __name__ == "__main__":
    unittest.main()
