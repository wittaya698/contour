"""The agent's words as a tree the page can draw (issue 128).

The agent writes Markdown, and *the agent's words as they are* (ADR 0025,
decision 8) means with the formatting it gave them, not the symbols that
wrote it. So each `text` event carries, beside its raw words, a tree of blocks
and spans, and the page draws that tree with `createElement` and `textContent`.

Hand-written, and a tree rather than HTML, on purpose. A Markdown library is
not stdlib, which the launcher promises to be, and it hands back an HTML
string, which the page must never take: what the page cannot set as markup it
cannot be tricked into running. A subset, too: what this does not understand
it shows as written, so a word is never lost, only left unformatted.

Stdlib, and Blender-free: the console imports this to draw its transcript.
"""
import re


def blocks(text):
    """The tree of `text`: a list of blocks, each a dict with a `kind`."""
    lines = text.split("\n")
    out, para = [], []
    listed = None   # the list being read, as [block, its indent, its latest item]

    def close():
        if para:
            out.append({"kind": "paragraph", "spans": spans("\n".join(para))})
            para.clear()

    at = 0
    while at < len(lines):
        line = lines[at]
        fence = FENCE.match(line)
        end = fence and closing(lines, at, fence)
        item = ITEM.match(line.lstrip())
        indent = len(line) - len(line.lstrip())
        if end:
            close()
            listed = None
            out.append({"kind": "code", "lang": fence["lang"].strip(),
                        "text": "\n".join(dedent(l, len(fence["indent"]))
                                          for l in lines[at + 1:end])})
            at = end + 1
            continue
        heading = HEADING.match(line)
        if heading:
            close()
            listed = None
            out.append({"kind": "heading", "spans": spans(heading["words"])})
        elif line.lstrip().startswith("|") and TABLE.match(lines[at + 1] if at + 1 < len(lines) else ""):
            # As written, in monospace: its columns line up as the agent
            # spaced them, and a grid drawn from cells it may have miscounted
            # would lose the ones that do not fit.
            close()
            listed = None
            end = at
            while end < len(lines) and lines[end].lstrip().startswith("|"):
                end += 1
            out.append({"kind": "code", "lang": "", "text": "\n".join(lines[at:end])})
            at = end
            continue
        elif item:
            close()
            new = {"marker": item["marker"], "lines": [item["rest"]]}
            if listed is None:
                listed = [{"kind": "list", "items": []}, indent, None]
                out.append(listed[0])
            if indent > listed[1] and listed[0]["items"]:
                # One level of nesting, however deep it was written: a page
                # half a screen wide has no room for a staircase.
                listed[0]["items"][-1].setdefault("items", []).append(new)
            else:
                listed[0]["items"].append(new)
            listed[2] = new
        elif not line.strip():
            close()
            if listed and not continues(lines, at, listed[1]):
                listed = None
        elif listed and indent > listed[1]:
            listed[2]["lines"].append(line.strip())
        else:
            listed = None
            para.append(line)
        at += 1
    close()
    for block in out:
        if block["kind"] == "list":
            block["items"] = [finished(i) for i in block["items"]]
    return out


HEADING = re.compile(r" {0,3}#{1,6}[ \t]+(?P<words>\S.*)$")
"""A heading, drawn as a line on its own in bold. `#3` is a number."""

TABLE = re.compile(r"\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")
"""The line under a table's header, which is what makes the lines around it
a table and not words with pipes in them."""

ITEM = re.compile(r"(?P<marker>[-*+]|\d{1,9}[.)])[ \t]+(?P<rest>\S.*)$")
"""A list item: `-`, `*`, `+` or a number, then a space, then words. So a
line opening `**1. What is it?**` is bold, and `*nexus-probe*` italic."""


def continues(lines, at, indent):
    """Whether the list goes on past the blank line at `at`: an agent puts
    blank lines between the questions of one interview."""
    for line in lines[at + 1:]:
        if line.strip():
            return bool(ITEM.match(line.strip())) or len(line) - len(line.lstrip()) > indent
    return False


def finished(item):
    """An item read as lines, as the tree holds it."""
    done = {"marker": item["marker"], "spans": spans("\n".join(item["lines"]))}
    if "items" in item:
        done["items"] = [finished(i) for i in item["items"]]
    return done


FENCE = re.compile(r"(?P<indent>[ \t]*)(?P<run>`{3,}|~{3,})(?P<lang>[^`]*)$")
"""A fence opens a block of code. Any indent, since an agent nests one under
a list item; the code inside loses that indent and no more."""


def closing(lines, at, fence):
    """The line that closes the fence opened at `at`, or None: an unclosed
    fence is shown as written, not taken to swallow everything after it."""
    run = fence["run"]
    for n in range(at + 1, len(lines)):
        if (lines[n].strip().startswith(run[0] * len(run))
                and not lines[n].strip().strip(run[0])):
            return n
    return None


def dedent(line, indent):
    """`line` less up to `indent` leading spaces."""
    keep = len(line) - len(line.lstrip(" "))
    return line[min(keep, indent):]


def spans(text, style=()):
    """Runs of text, each a dict with its `text` and the styles it is in.

    Each marker must close, in this text, around something, or it is a
    character like any other."""
    out = []
    at = plain = 0
    while at < len(text):
        found = emphasis(text, at)
        if not found:
            at += 1
            continue
        inner, end, kind = found
        out.append(run(text[plain:at], style))
        if kind == "link":
            # Its words and where it points, and not a link: the agent chose
            # where it goes, so the page shows that rather than going there.
            out += spans(inner["words"], style) + [run(f" ({inner['to']})", style)]
        elif kind == "code":
            # As written, markers and all: only emphasis nests.
            out.append(run(inner, style + (kind,)))
        else:
            out += spans(inner, style + (kind,))
        at = plain = end
    out.append(run(text[plain:], style))
    return merged(out)


def emphasis(text, at):
    """The emphasis opening at `at`, as (inner text, end, style), or None."""
    if text[at] == "[":
        link = LINK.match(text, at)
        if link:
            return link, link.end(), "link"
        return None
    if text[at] == "`":
        n = len(text) - len(text[at:].lstrip("`")) - at
        end = text.find("`" * n, at + n)
        while end >= 0 and text.startswith("`", end + n):
            end = text.find("`" * n, end + n + 1)
        if end > at + n:
            return text[at + n:end], end + n, "code"
        return None
    for marker, kind in (("**", "bold"), ("__", "bold"), ("*", "italic"), ("_", "italic")):
        if text.startswith(marker, at):
            end = closer(text, at, marker)
            if end is not None:
                return text[at + len(marker):end], end + len(marker), kind
            return None
    return None


LINK = re.compile(r"\[(?P<words>[^\]\n]+)\]\((?P<to>(?:[^()\s]|\([^()\s]*\))+)\)")
"""`[words](where)`, where may hold one level of brackets."""


def closer(text, at, marker):
    """Where `marker`, opening at `at`, closes, or None. It opens before a
    character and closes after one, never on space, so *2 * 3* is a sum; and
    `_` only between words, so a snake_case_name is a name."""
    n = len(marker)
    after = text[at + n:at + n + 1]
    if not after or after.isspace() or after == marker[0]:
        return None
    if marker[0] == "_" and at and text[at - 1].isalnum():
        return None
    end = text.find(marker, at + n + 1)
    while end >= 0:
        doubled = n == 1 and (text[end - 1] == marker or text.startswith(marker, end + 1))
        word = marker[0] == "_" and text[end + n:end + n + 1].isalnum()
        if not text[end - 1].isspace() and not doubled and not word:
            return end
        end = text.find(marker, end + (2 if doubled else 1))
    return None


def run(text, style):
    return {"text": text, **{s: True for s in style}}


def merged(runs):
    """`runs` less the empty ones, and with neighbours in one style joined."""
    out = []
    for r in runs:
        if not r["text"]:
            continue
        if out and out[-1].keys() == r.keys():   # a style is there or absent
            out[-1] = {**out[-1], "text": out[-1]["text"] + r["text"]}
        else:
            out.append(r)
    return out
