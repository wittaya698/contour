"""What a call means, in Contour's vocabulary (ADR 0019, decision 22).

The console's gate consults a list of intents — a build, a spec write — and
asks this module which one a call belongs to. It does not pattern-match the
call's text: one intent has four spellings (`./contour check`, `contour
check`, a `cd` into the space first, and `contour render`, which also builds)
and a permission list needing one rule per spelling will still have a hole.

Blender-free by construction: the console imports this to decide whether to
ask, and the console must never pull Blender into its own process.
"""
import re
import shlex
from pathlib import Path

# Every category the toolkit knows, in the order ADR 0019 names them: the two
# writes rule 1 is about, then the build, then the two rule 5 is about. The
# order is declared rather than derived so that an audit against the user's
# ask-list compares two lists that do not move.
CATEGORIES = ("spec-write", "ref-write", "build", "commit", "push")


# Signs that a shell call writes rather than reads. Blunt on purpose: a false
# positive costs one click at a gate, a false negative is a rule that has
# silently stopped being enforced, and rule 1 is not a thing to be subtle
# about. `sed` earns its place only with `-i`, since reading with it is common.
WRITING = ("tee", "cp", "mv", "dd", "truncate", "install", "patch",
           "python", "python3", "perl", "ruby", "awk")


# A substitution is a whole command line packed inside one word, so splitting
# the outer line into words never reaches it.
INSIDE = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")


# Shells whose `-c` argument is a whole command line of its own, invisible to
# anything that splits the outer line into words.
SHELLS = ("sh", "bash", "zsh", "dash", "ksh")


# The launcher subcommands that run Blender and write `out/`.
BUILD = ("check", "render", "export")

# git's verbs that carry an intent. A commit is local and a push leaves the
# machine, so they are two categories and not one.
GIT = {"commit": "commit", "push": "push"}


def categories():
    """The categories a call can be classified as, for printing and auditing.

    The ask-list is an allow-list with no presets, so it is meaningful only
    against the current set; a list that cannot be printed cannot be audited.
    """
    return CATEGORIES


def writes(call, words):
    """Whether this shell call looks like it changes a file.

    A redirect is punctuation rather than a word, so the raw line is read for
    those and the words for the programs.
    """
    if any(mark in call for mark in (">", "<<")):
        return True
    if "sed" in [w.rsplit("/", 1)[-1] for w in words] and "-i" in words:
        return True
    return any(w.rsplit("/", 1)[-1] in WRITING for w in words)


def mentioned(call):
    """The category a writing shell call carries, from the text of the call.

    Not from its words: a path inside a script — `open('spec.yaml', 'w')` — is
    part of a word rather than one, and a heredoc is how an agent in auto mode
    edits a file. So the line is read for the names that matter.
    """
    if "spec.yaml" in call:
        return "spec-write"
    if re.search(r"(?<![.\w])refs/", call.replace(".git/refs/", "")):
        return "ref-write"
    return None


def path_intent(path):
    """The category a path being written carries, or None."""
    if path.name == "spec.yaml":
        return "spec-write"
    # A space holds two directories called `refs`: the user's reference images
    # at its root, and git's branch heads under `.git`. Only the first is the
    # one rule 1 is about.
    if "refs" in path.parts and ".git" not in path.parts:
        return "ref-write"
    return None


def after(flag, words):
    """The value `flag` was given, or None. `bash -lc "git push"` bundles its
    flags, so the flag is found inside a cluster as well as alone."""
    for at, word in enumerate(words):
        if word == flag or (word.startswith("-") and not word.startswith("--")
                            and flag[1:] in word[1:]):
            return words[at + 1] if at + 1 < len(words) else None
    return None


def subcommand(words):
    """The verb in `git -C widget commit -m x`, past git's own options.

    `-C` is the spelling that reaches a model space from outside it, so a rule
    wanting the words `git` and `commit` adjacent misses the call the toolkit
    makes into a space. Two of git's global options take a separate value.
    """
    takes_value = ("-C", "-c", "--git-dir", "--work-tree", "--namespace")
    skip = False
    for word in words:
        if skip:
            skip = False
        elif word.startswith("-"):
            skip = word in takes_value
        else:
            return word
    return None


def strictest(found):
    """The highest-stakes category of those a call carries.

    One call gets one answer, so a call that chains a spec write onto a build
    must not be let through because the build was matched first. CATEGORIES is
    declared in the order the stakes run.
    """
    for category in CATEGORIES:
        if category in found:
            return category
    return None


def classify(tool, payload):
    """The category this call belongs to, or None if it carries no intent.

    None means *not gated*, so a call this cannot read raises instead: a
    quoting accident around `git push` must not read as carrying no intent.
    """
    if tool in ("Write", "Edit"):
        return path_intent(Path(payload.get("file_path", "")))
    if tool != "Bash":
        return None
    call = payload.get("command", "")
    try:
        words = shlex.split(call)
    except ValueError as e:
        raise ValueError(f"cannot read the intent of {call!r}: {e}") from e
    found = set()
    for at, word in enumerate(words):
        program = word.rsplit("/", 1)[-1]
        if program == "contour" and at + 1 < len(words):
            if words[at + 1] in BUILD:
                found.add("build")
        if program in SHELLS:
            inner = after("-c", words[at + 1:])
            if inner:
                found.add(classify(tool, {"command": inner}))
        if program == "git":
            found.add(GIT.get(subcommand(words[at + 1:])))
    if writes(call, words):
        found.add(mentioned(call))
    for pair in INSIDE.findall(call):
        found.add(classify(tool, {"command": "".join(pair)}))
    return strictest(found)
