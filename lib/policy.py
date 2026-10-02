"""The ask-list: which categories of call run unwatched (ADR 0019, decision 36).

An allow-list with no presets. The file names only what the user has chosen to
let through, and a category it does not mention is gated — so a category the
toolkit gains later arrives as a gate that is noticed and then decided, rather
than as a word like `normal` whose meaning moved underneath the user.

Blender-free by construction: the console consults this to decide whether to
ask, and the console must never pull Blender into its own process.
"""
import os
from pathlib import Path

from lib import intent, miniyaml


def home():
    """`~/.contour`: the user's own, outside the toolkit and every model space.
    `$CONTOUR_HOME` moves the whole directory, which is how a test reads a
    policy, or writes a trash, that is not the user's own."""
    told = os.environ.get("CONTOUR_HOME")
    return Path(told) if told else Path.home() / ".contour"


def ask_list():
    """Where the ask-list lives: `~/.contour/ask-list.yaml`, outside the toolkit
    and outside every model space, so an agent working in a space has no
    in-scope reason to touch it.
    """
    return home() / "ask-list.yaml"


def here(path):
    """A path as the one directory it names, so two spellings of it agree.

    `~` is expanded because that is how a path gets written into a config file
    by hand, and the shell is not there to do it.
    """
    return str(Path(path).expanduser().resolve())


class PolicyError(ValueError):
    """The file exists and cannot be read as policy.

    Raised rather than resolved to the empty list: empty is a list the user
    could have chosen, and a permission reader must not have one value that
    means both *you allowed nothing* and *I could not read this*.
    """


def named(space, file=None):
    """Exactly what the file names for this space, before it is checked against
    the categories the toolkit knows.

    Being named in `spaces:` is the act of recognition. A path the file never
    names lets nothing through, because the key is the path and a space that
    moved would otherwise arrive holding permissions nobody granted it.
    """
    file = Path(file or ask_list())
    if not file.exists():
        return ()                  # nobody has written one yet: ask about all
    try:
        whole = miniyaml.load(file)
    except (miniyaml.YamlError, OSError) as e:
        raise PolicyError(f"cannot read {file} as an ask-list: {e}") from e
    scope = whole
    if space is not None:
        # Keys are compared as directories, not as strings: the launcher
        # resolves the space it walked up to, and the user writes the path
        # their shell shows them. On this machine those differ by a symlink,
        # and a key that governs nothing reads exactly like a typo.
        spaces = {here(k): v for k, v in (whole.get("spaces") or {}).items()}
        if here(space) not in spaces:
            return ()
        # Replace, whole: a space that named a list does not also inherit the
        # global one, because a merge can shadow a rule in either file.
        scope = spaces[here(space)] or {}
        # A space listed and left silent is the user asking for the global
        # list. Naming the path is the recognition; the list beside it is the
        # override, and there is no third thing a bare path could mean.
        if "allow" not in scope:
            scope = whole
    return tuple(scope.get("allow") or ())


def names(space, file=None):
    """Whether the file has an entry for this space's path — the one thing a
    rename leaves behind here, since the key is the path and the renamed space
    then falls back to asking about everything (open question 12)."""
    file = Path(file or ask_list())
    if not file.exists():
        return False
    try:
        whole = miniyaml.load(file)
    except (miniyaml.YamlError, OSError) as e:
        raise PolicyError(f"cannot read {file} as an ask-list: {e}") from e
    return here(space) in {here(k) for k in (whole.get("spaces") or {})}


def split(names):
    """What the file named, as (categories the toolkit knows, the rest).

    The one place the file meets the vocabulary, so a name cannot be honoured by
    one caller and reported by another.
    """
    known = intent.categories()
    return (tuple(c for c in known if c in names),
            tuple(c for c in names if c not in known))


def allowed(space, file=None):
    """The categories this space lets through without asking, in the order the
    toolkit declares them, so an audit compares two lists that do not move."""
    return split(named(space, file))[0]


def unknown(space, file=None):
    """The names in the file that are not categories the toolkit knows."""
    return split(named(space, file))[1]


def gated(category, space, file=None):
    """Whether a call of this category has to be asked about."""
    return category not in allowed(space, file=file)


def report(space, file=None):
    """The resolved policy, in lines a person can audit against `contour
    intents`. A name the toolkit no longer knows is said out loud here, because
    dropping it silently retires a permission the user believes they granted.
    """
    file = Path(file or ask_list())
    lets, strangers = split(named(space, file))   # one read, one verdict
    lines = [f"ask-list {file}",
             f"space {space}" if space else "no space: the global list"]
    # Every category, not only the allowances: what is *watched* is the half the
    # user is auditing, and it is the half a list of allowances cannot show.
    lines += [f"{'allow' if c in lets else 'ask'} {c}"
              for c in intent.categories()]
    return lines + [f"unknown category {c!r} in {file} — not a category the "
                    f"toolkit knows, so it allows nothing" for c in strangers]
