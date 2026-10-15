"""The questions this toolkit asks git, each asked once (ADR 0019, decision 37).

Five hand-rolled wrappers used to live here instead — in `lib/marks.py`,
`console/vetoes.py`, `contour`, and eight ad-hoc `subprocess.run(["git", ...])`
calls besides. The duplication was never the defect. Three of them
independently decided that a non-zero exit means *no answer* rather than an
error, and nothing said so out loud, so the next one to be written would have
decided again, on its own, in whichever direction the day suggested.

What is exported is therefore **named questions**, not a runner. No caller
assembles argv, no caller reads a return code, and each function says in its own
docstring what it does when git cannot answer — because that is the part that
diverged, and a policy written down once beside its question is the only version
of it that stays true.

One question deliberately stays outside: `tools/guards/spec.py:tracked` denies on
any git error, which is right there and wrong in every caller here (slice 15).
The reason belongs next to the deny, not in a shared default that would quietly
hand it to everyone.

Blender-free, because everything that asks these is: the launcher before it
starts anything, the mark store, the console.
"""
import re
import subprocess
from pathlib import Path


def _ask(repo, *args, timeout=10):
    """Run one git question in `repo` and hand back `(ok, stdout)`.

    Private, and the only place in the toolkit that builds a git argv. `ok` is
    *git answered*: a false one carries no message, because every caller above
    turns it into a silence of its own choosing and none of them wants a
    traceback about a directory that simply is not a repository yet.
    """
    try:
        done = subprocess.run(["git", "-C", str(repo), *args],
                              capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return False, ""          # no git on this machine, or it hung
    return done.returncode == 0, done.stdout


def show(repo, ref, path):
    """The file at `path` as `ref` holds it, or None when it holds no such file.

    **None is not an empty string,** and the difference is load-bearing: the
    launcher reads *no answer* as *this spec is new, and creation is not
    mutation*, where an empty answer would be a spec somebody emptied. Returned
    byte for byte, unstripped, for the same comparison's sake.

    Not a repository, no commit yet, no git at all — all of them are None. A
    space before `contour init` is not an error to raise at a page; it is a
    place where nothing is committed, which is what the answer then says.
    """
    ok, out = _ask(repo, "show", f"{ref}:./{path}")
    return out if ok else None


_RELEASE = re.compile(r"v([1-9][0-9]*)")


def is_release(tag):
    """Whether `tag` names a release: `v<N>` and nothing else (ADR 0013, amended)."""
    return bool(_RELEASE.fullmatch(tag))


def releases(repo):
    """Every release tag, newest first, or `[]` when there are none.

    No failed question here: a space nobody has released has no tags, and so
    does a directory that is not a repository. Both mean *there is no archive*,
    which is what the mark store does something about either way.

    A release tag is `v<N>` and nothing else (ADR 0013, amended): any other tag
    in a space is the user's own, and Contour does not see it. Newest is the
    highest N, compared as a number, because N is one past the highest when a
    release is cut; a lower N cut later is drift, which the next release
    refuses rather than this choosing by date.
    """
    ok, out = _ask(repo, "tag", "--list")
    found = [(int(m.group(1)), t) for t in (out.split() if ok else [])
             if (m := _RELEASE.fullmatch(t))]
    return [t for _, t in sorted(found, reverse=True)]


def head(repo):
    """The short hash of what is checked out, or None when nothing is.

    None covers three states a caller cannot tell apart and does not need to:
    no commit yet, no repository, no git. `contour init` stamps this into a
    space's marker and `doctor` reads it back to say which toolkit built it, so
    the one thing it must never do is invent a hash — the report spells a
    missing one `unknown` where a person will read it.
    """
    ok, out = _ask(repo, "rev-parse", "--short", "HEAD")
    return out.strip() if ok and out.strip() else None


def commits(repo):
    """How many commits the current branch holds, or 0.

    A count, so *nothing committed* is 0 and never None: a fresh space
    genuinely holds nothing, and the column `contour spaces` prints it in is a
    number. `rev-list` fails outright on a repository with no commit, and that
    is the exact case three separate wrappers each decided the meaning of.
    """
    ok, out = _ask(repo, "rev-list", "--count", "HEAD")
    try:
        return int(out.strip()) if ok else 0
    except ValueError:
        return 0


def remotes(repo):
    """Every remote this repository has, or `[]`.

    Read by the one rule that has a hook behind it: a model space is never
    pushed (ADR 0011, ADR 0015), so `doctor` and `spaces` both warn when one
    has grown a remote. `[]` on any failure is safe in the direction that
    matters here — this question can fail to find a remote that exists, which
    the pre-push guard still stops, but it can never invent one and condemn a
    space that is clean.
    """
    ok, out = _ask(repo, "remote")
    return out.split() if ok else []


def changes(repo):
    """Every path with a change no commit holds, untracked ones included, or
    None when git cannot say.

    None is not `[]`: the one caller deletes a space on an empty answer, so
    *could not ask* must never read as *nothing to lose*. Ignored files are
    not changes — they are what a bundle is allowed to leave behind.
    """
    ok, out = _ask(repo, "status", "--porcelain", "--untracked-files=all")
    return [line[3:] for line in out.splitlines() if line] if ok else None


def hooks_dir(repo):
    """Where this repository keeps its hooks, absolute, or None.

    Asked of git rather than assumed to be `.git/hooks`, because a worktree
    keeps them elsewhere and a guard written into the wrong directory is a
    guard that silently does not exist. None when there is no repository to
    ask, and the caller reports that rather than writing a file nothing reads.
    """
    ok, out = _ask(repo, "rev-parse", "--git-path", "hooks")
    return (Path(repo) / out.strip()).resolve() if ok and out.strip() else None


def hooks_override(repo):
    """`core.hooksPath` if it is set, otherwise `""`.

    Set, it silently overrides every hook installed anywhere else, so
    `install-hooks` has to be able to say that the guard it just wrote is not
    the guard that will run. Unset is the ordinary case and makes `config` exit
    non-zero, so here a failed question and an empty answer are the same thing
    and saying so is the whole point.
    """
    ok, out = _ask(repo, "config", "--get", "core.hooksPath")
    return out.strip() if ok else ""


def start(repo):
    """Make a repository at `repo`. Returns None, or what git said if it could not.

    The one write here, and so the one question with the opposite error policy:
    everything above shrugs, because a directory that is not a repository is an
    ordinary state. This one cannot shrug — a model space *is* its own
    repository (ADR 0015), and a space created without one is not a space. So
    the failure is returned rather than swallowed, and the caller stops on it.
    """
    try:
        done = subprocess.run(["git", "init", "-q", str(repo)],
                              capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        return str(e)
    return None if done.returncode == 0 else (done.stderr.strip() or "git init failed")


def bundle(repo, to):
    """Write every ref of `repo` into one file at `to`, and prove the file
    carries them. Returns None, or what went wrong.

    A write, so the policy is `start`'s and not the questions': a delete
    removes the space only on a None from here, and a bundle git could not
    write, or wrote and cannot read back whole, must stop it. Proved twice:
    git verifies the file, and the heads it lists are every ref the
    repository has, so a bundle missing a branch is not mistaken for one
    holding it.
    """
    for args in (("bundle", "create", "-q", str(to), "--all"),
                 ("bundle", "verify", "-q", str(to))):
        try:
            done = subprocess.run(["git", "-C", str(repo), *args],
                                  capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as e:
            return str(e)
        if done.returncode != 0:
            return done.stderr.strip() or f"git {' '.join(args[:2])} failed"
    ok, heads = _ask(repo, "bundle", "list-heads", str(to))
    ok_refs, refs = _ask(repo, "for-each-ref", "--format=%(objectname) %(refname)")
    if not (ok and ok_refs):
        return "git could not list what the bundle holds"
    missing = set(refs.split("\n")) - set(heads.split("\n"))
    if missing - {""}:
        return f"the bundle does not carry {', '.join(sorted(missing - {''}))}"
    return None


def clone(bundle, to):
    """Make a repository at `to` from `bundle`, with no remote. Returns None,
    or what git said if it could not.

    A write, so `start`'s policy. A clone names its source as `origin`, and a
    model space with a remote is the thing rule 8 forbids; here the remote is
    a file in the trash, but `doctor` and `spaces` would rightly warn about it,
    so it is removed before the space is handed back.
    """
    for args in (("clone", "-q", str(bundle), str(to)),
                 ("-C", str(to), "remote", "remove", "origin")):
        try:
            done = subprocess.run(["git", *args], capture_output=True, text=True,
                                  timeout=120)
        except (OSError, subprocess.SubprocessError) as e:
            return str(e)
        if done.returncode != 0:
            return done.stderr.strip() or f"git {args[0]} failed"
    return None
