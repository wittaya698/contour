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

from lib import commands

# Every category the toolkit knows, in the order ADR 0019 names them: the two
# writes rule 1 is about, then the build, then the two rule 5 is about. The
# order is declared rather than derived so that an audit against the user's
# ask-list compares two lists that do not move.
CATEGORIES = ("spec-write", "ref-write", "build", "commit", "push")

ROOT = "CLAUDE_PROJECT_DIR"
"""Where a hook is told which space it is guarding, and so where the paths in a
call are judged from: the guard reads it, and a console that makes a set-aside
call later names the space in it, so an inherited one never points elsewhere."""


# Signs that a shell call writes rather than reads. Blunt on purpose: a false
# positive costs one click at a gate, a false negative is a rule that has
# silently stopped being enforced, and rule 1 is not a thing to be subtle
# about. `sed` earns its place only with `-i`, since reading with it is common.
WRITING = ("tee", "cp", "mv", "dd", "truncate", "install", "patch",
           "python", "python3", "perl", "ruby", "awk")


# The `sips` flags that only read an image. Any other flag changes it, and
# `sips` writes a change back over the file it read unless given `--out`.
SIPS_READS = ("-g", "--getProperty", "-1", "--oneLine", "-h", "--help",
              "-H", "--helpProperties", "-v", "--version", "--debug")


# A path under the user's references, wherever in a call it sits. Read out of the
# raw text and not the words: a path inside a heredoc or a quoted script is part
# of a word rather than a word, and a heredoc is how an agent in auto mode edits
# a file. The prefix is whole components only, so `sourcerefs/x` is not one.
REFS = re.compile(r"(?<![.\w])(/?(?:[\w.~@+=,:-]+/)*refs/[\w.~@+=,:/-]*)")


# A substitution is a whole command line packed inside one word, so splitting
# the outer line into words never reaches it.
INSIDE = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")


# Shells whose `-c` argument is a whole command line of its own, invisible to
# anything that splits the outer line into words.
SHELLS = ("sh", "bash", "zsh", "dash", "ksh")


# git's verbs that carry an intent. A commit is local and a push leaves the
# machine, so they are two categories and not one.
GIT = {"commit": "commit", "push": "push"}


# A redirect that writes no file: onto another descriptor, or into nothing.
NOWHERE = re.compile(r"(?<![\w>&])(?:&|\d*)>>?\s*/dev/null(?![\w/.])"
                     r"|(?<![\w>&])\d*>&\s*(?:\d+|-)(?![\w/.])")


# A redirect into a file, and the file: `> x`, `>> x`, `2> x`, `&> "x y"`.
INTO = re.compile(r"(?<![\w>&<])(?:&|\d*)>>?\|?\s*(\"[^\"]*\"|'[^']*'|[^\s;&|<>()]+)")


# A heredoc's opening:`<<EOF`, `<<-EOF`, `<<'EOF'` or `<<"EOF"`.
HEREDOC = re.compile(r"<<(-?)\s*(['\"]?)([A-Za-z_]\w*)\2")


def unmessaged(call):
    """The call with `git commit`'s own message taken out, where a heredoc
    feeds it one (issue 103).

    A message is text about a change, and it names what it is about: a save
    whose message said `spec.yaml` read as a spec write, and said so on the
    page and in the veto. Only `git commit -F -` is let off. An interpreter fed
    a heredoc is how an agent edits a file, and `git apply` fed one changes
    files, so every other heredoc is left to be read as a write.
    """
    at = 0
    while True:
        found = HEREDOC.search(call, at)
        if found is None:
            return call
        start = call.rfind("\n", 0, found.start()) + 1
        command = re.split(r"&&|\|\||;|\|", call[start:found.start()])[-1]
        body = call.find("\n", found.end())
        end = closing(call, body, found.group(3), found.group(1)) if body != -1 else None
        if end is None or not messages(command):
            at = found.end()
            continue
        call = call[:found.start()] + call[found.end():body] + call[end:]
        at = found.start()


def closing(call, body, delimiter, indented):
    """Where the line after a heredoc's closing delimiter starts, or None if it
    is never closed: an unclosed one is left whole, to be read as written."""
    at = body + 1
    while at <= len(call):
        stop = call.find("\n", at)
        line = call[at:] if stop == -1 else call[at:stop]
        if (line.lstrip("\t") if indented else line) == delimiter:
            return len(call) if stop == -1 else stop
        if stop == -1:
            return None
        at = stop + 1
    return None


def messages(command):
    """Whether this command is `git commit` taking its message from stdin."""
    try:
        words = shlex.split(command)
    except ValueError:
        return False
    for at, word in enumerate(words):
        if word.rsplit("/", 1)[-1] == "git":
            rest = words[at + 1:]
            return (subcommand(rest) == "commit"
                    and (after("-F", rest) == "-" or after("--file", rest) == "-"
                         or "--file=-" in rest))
    return False


def categories():
    """The categories a call can be classified as, for printing and auditing.

    The ask-list is an allow-list with no presets, so it is meaningful only
    against the current set; a list that cannot be printed cannot be audited.
    """
    return CATEGORIES


def quiet(call):
    """The call with its redirects that write no file taken out: onto another
    descriptor (`2>&1`, `>&2`) or into `/dev/null` (issue 152)."""
    return NOWHERE.sub(" ", call)


def writes(call, words):
    """Whether this shell call looks like it changes a file.

    A redirect is punctuation rather than a word, so the raw line is read for
    those and the words for the programs.
    """
    if any(mark in quiet(call) for mark in (">", "<<")):
        return True
    if "sed" in [w.rsplit("/", 1)[-1] for w in words] and "-i" in words:
        return True
    if any(resized(part) for part in commands_in(call)):
        return True
    return any(w.rsplit("/", 1)[-1] in WRITING for w in words)


def commands_in(call):
    """The call's commands, one per `;`, `&&`, `||`, `|` or line."""
    return re.split(r"&&|\|\||;|\||\n", call)


def resized(command):
    """Whether this command is a `sips` that changes an image, and so writes
    one: into its `--out`, or in place over the file it was given."""
    words = words_of(command)
    if "sips" not in [w.rsplit("/", 1)[-1] for w in words]:
        return False
    return any(w.startswith("-") and w not in SIPS_READS for w in words)


def resized_elsewhere(command):
    """Whether this `sips` writes only into an `--out` that is not a reference."""
    words = words_of(command)
    out = after("--out", words) or after("-o", words)
    return resized(command) and out is not None and not refs_in(out)


def mentioned(call):
    """The category a writing shell call carries, from the text of the call.

    Not from its words: a path inside a script — `open('spec.yaml', 'w')` — is
    part of a word rather than one, and a heredoc is how an agent in auto mode
    edits a file. So the line is read for the names that matter.
    """
    if "spec.yaml" in call:
        return "spec-write"
    aimed = aimed_at_references(call)
    if refs_in(aimed) and writes(aimed, words_of(aimed)):
        return "ref-write"
    return None


def aimed_at_references(call):
    """The call without the writes that plainly land outside `refs/`: a
    redirect to a file that is not a reference, or a `sips` whose `--out` is
    not one (issue 152). What is left still names every reference the call
    could change, and nothing that only reads one becomes a write by sitting
    beside a redirect to the scratchpad."""
    call = INTO.sub(lambda m: m.group(0) if refs_in(m.group(1)) else " ", quiet(call))
    return "\n".join(c for c in commands_in(call) if not resized_elsewhere(c))


def words_of(call):
    """The words of a call, or its whitespace-split ones if it will not split:
    a quoting accident is no reason to read fewer programs."""
    try:
        return shlex.split(call)
    except ValueError:
        return call.split()


def refs_in(text):
    """The paths under `refs/` this text names, in the order it names them.

    One definition, because `mentioned` asking *does this call touch a reference*
    and `references` asking *which ones* must never be able to disagree: the
    first decides whether a gate fires and the second what the guard denies.
    """
    # A space holds two directories called `refs`: the user's reference images,
    # and git's branch heads under `.git`. Only the first is the one rule 1 is
    # about, and the second is named on every commit.
    return tuple(REFS.findall(text.replace(".git/refs/", "")))


def references(tool, payload):
    """The paths under `refs/` this call names, in the order it names them.

    Beside `classify` rather than inside it, because a category answers *is this
    gated* and the guard has a second question: whether git tracks this
    particular reference, since saving a new one is how a space starts
    (ADR 0012). One call can name several, and the guard judges each.
    """
    return refs_in(payload.get("command") or payload.get("file_path") or "")


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


def launched(name):
    """The category a launcher subcommand carries, read from the launcher's own
    table — the one copy there is, so a build command cannot be added to the
    launcher and missed here (issue 24). None for a name the table does not
    hold, which is no intent rather than an unreadable one."""
    return next((c.category for c in commands.TABLE if c.name == name), None)


def classify(tool, payload):
    """The category this call belongs to, or None if it carries no intent.

    None means *not gated*, so a call this cannot read raises instead: a
    quoting accident around `git push` must not read as carrying no intent.
    """
    if tool in ("Write", "Edit"):
        return path_intent(Path(payload.get("file_path", "")))
    if tool != "Bash":
        return None
    call = unmessaged(payload.get("command", ""))
    try:
        words = shlex.split(call)
    except ValueError as e:
        raise ValueError(f"cannot read the intent of {call!r}: {e}") from e
    found = set()
    for at, word in enumerate(words):
        program = word.rsplit("/", 1)[-1]
        if program == "contour" and at + 1 < len(words):
            found.add(launched(words[at + 1]))
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
