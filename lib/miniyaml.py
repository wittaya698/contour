"""A small YAML subset reader, so specs load with neither PyYAML nor a venv.

Blender's bundled Python has no yaml module and README promises no virtualenv.
Supported: block mappings and sequences (a sequence may sit at its key's indent),
one-line flow `{a: 1}` / `[a, b]`, quoted and plain scalars, `>` and `|` block
scalars with `-`/`+` chomping, `#` comments.

Refused loudly, never guessed at: tabs, anchors/aliases, tags, multi-document
streams, `?` complex keys. If a spec needs those, extend this file and its test.
"""
import re

_INT = re.compile(r"[-+]?\d+")
_FLOAT = re.compile(r"[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?")


class YamlError(ValueError):
    pass


def loads(text):
    return _Parser(text).document()


def load(path):
    with open(path, encoding="utf-8") as f:
        return loads(f.read())


def _strip_comment(s):
    q = None
    for i, c in enumerate(s):
        if q:
            if c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i]
    return s


def _scalar(s):
    s = s.strip()
    if s == "" or s in ("~", "null", "Null", "NULL"):
        return None
    if s[0] in "&*!" or s.startswith("---"):
        raise YamlError(f"unsupported YAML construct: {s[:20]!r}")
    if s[0] == '"' and s[-1] == '"' and len(s) >= 2:
        return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)),
                      s[1:-1])
    if s[0] == "'" and s[-1] == "'" and len(s) >= 2:
        return s[1:-1].replace("''", "'")
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if _INT.fullmatch(s):
        return int(s)
    if _FLOAT.fullmatch(s):
        return float(s)
    return s


def _split_key(s):
    """('key', 'rest') if s is `key: rest`, else None. Colon must be outside quotes/brackets."""
    q, depth = None, 0
    for i, c in enumerate(s):
        if q:
            if c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
        elif c == ":" and depth == 0 and (i + 1 == len(s) or s[i + 1] in " \t"):
            return _scalar(s[:i]), s[i + 1:].strip()
    return None


class _Flow:
    def __init__(self, s):
        self.s, self.i = s, 0

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t":
            self.i += 1

    def value(self):
        self.ws()
        c = self.s[self.i] if self.i < len(self.s) else ""
        if c == "{":
            return self.mapping()
        if c == "[":
            return self.sequence()
        if c in "\"'":
            j = self.i + 1
            while j < len(self.s) and self.s[j] != c:
                j += 2 if (c == '"' and self.s[j] == "\\") else 1
            tok, self.i = self.s[self.i:j + 1], j + 1
            return _scalar(tok)
        j = self.i
        while j < len(self.s) and self.s[j] not in ",}]" and not (
                self.s[j] == ":" and (j + 1 == len(self.s) or self.s[j + 1] in " ,}]")):
            j += 1
        tok, self.i = self.s[self.i:j], j
        return _scalar(tok)

    def mapping(self):
        self.i += 1
        out = {}
        while True:
            self.ws()
            if self.s[self.i] == "}":
                self.i += 1
                return out
            k = self.value()
            self.ws()
            if self.s[self.i] != ":":
                raise YamlError(f"flow mapping: expected ':' in {self.s!r}")
            self.i += 1
            out[k] = self.value()
            self.ws()
            if self.s[self.i] == ",":
                self.i += 1

    def sequence(self):
        self.i += 1
        out = []
        while True:
            self.ws()
            if self.s[self.i] == "]":
                self.i += 1
                return out
            out.append(self.value())
            self.ws()
            if self.s[self.i] == ",":
                self.i += 1


def _inline(s):
    s = s.strip()
    if s[:1] in ("{", "["):
        f = _Flow(s)
        v = f.value()
        if s[f.i:].strip():
            raise YamlError(f"trailing text after flow value: {s!r}")
        return v
    return _scalar(s)


class _Parser:
    def __init__(self, text):
        if "\t" in "".join(l[: len(l) - len(l.lstrip("\t "))] for l in text.splitlines()):
            raise YamlError("tab indentation is not supported")
        self.raw = text.splitlines()
        self.i = 0

    def peek(self):
        """(indent, content) of the next meaningful line, or None. Does not consume."""
        while self.i < len(self.raw):
            line = self.raw[self.i]
            body = _strip_comment(line).rstrip()
            if body.strip() == "":
                self.i += 1
                continue
            return len(body) - len(body.lstrip(" ")), body.strip()
        return None

    def document(self):
        p = self.peek()
        if p is None:
            return None
        if p[1].startswith("---"):
            raise YamlError("multi-document streams are not supported")
        v = self.block(p[0])
        if self.peek() is not None:
            raise YamlError(f"unparsed content at line {self.i + 1}: {self.raw[self.i]!r}")
        return v

    def block(self, indent):
        _, content = self.peek()
        if content == "-" or content.startswith("- "):
            return self.sequence(indent)
        if _split_key(content):
            return self.mapping(indent)
        self.i += 1
        return _inline(content)

    def sequence(self, indent):
        out = []
        while True:
            p = self.peek()
            if p is None or p[0] != indent or not (p[1] == "-" or p[1].startswith("- ")):
                return out
            rest = p[1][1:].strip()
            if rest == "":
                self.i += 1
                q = self.peek()
                out.append(self.block(q[0]) if q and q[0] > indent else None)
                continue
            nested_seq = rest == "-" or rest.startswith("- ")
            if nested_seq or (_split_key(rest) and not rest.startswith(("{", "["))):
                # `- key: v` / `- - v` open a block whose lines align with what follows `- `
                line = self.raw[self.i]
                col = line.index("-") + 1
                col += len(line[col:]) - len(line[col:].lstrip(" "))
                self.raw[self.i] = " " * col + line[col:]
                out.append(self.sequence(col) if nested_seq else self.mapping(col))
            else:
                self.i += 1
                out.append(_inline(rest))

    def mapping(self, indent):
        out = {}
        while True:
            p = self.peek()
            if p is None or p[0] != indent:
                return out
            kv = _split_key(p[1])
            if kv is None:
                return out
            key, rest = kv
            self.i += 1
            if rest == "":
                q = self.peek()
                if q and q[0] > indent:
                    out[key] = self.block(q[0])
                elif q and q[0] == indent and (q[1] == "-" or q[1].startswith("- ")):
                    out[key] = self.sequence(indent)
                else:
                    out[key] = None
            elif rest[0] in ">|":
                out[key] = self.block_scalar(rest, indent)
            else:
                if rest[0] not in "\"'{[" and _split_key(rest):
                    raise YamlError(f"line {self.i}: nested mapping on one line: {rest!r}")
                out[key] = _inline(rest)

    def block_scalar(self, header, parent_indent):
        m = re.fullmatch(r"([>|])([-+]?)(\d?)", header)
        if not m:
            raise YamlError(f"bad block scalar header {header!r}")
        style, chomp = m.group(1), m.group(2)
        body = []
        while self.i < len(self.raw):
            line = self.raw[self.i]
            if line.strip() and len(line) - len(line.lstrip(" ")) <= parent_indent:
                break
            body.append(line)
            self.i += 1
        while body and not body[-1].strip():
            body.pop()
        pad = min((len(l) - len(l.lstrip(" ")) for l in body if l.strip()), default=0)
        body = [l[pad:] for l in body]
        if style == "|":
            text = "\n".join(body)
        else:  # fold: single newlines become spaces, blank lines become newlines
            text, prev_blank = "", True
            for l in body:
                if not l.strip():
                    text += "\n"
                    prev_blank = True
                else:
                    text += ("" if prev_blank else " ") + l.strip()
                    prev_blank = False
        if chomp == "-":
            return text
        return text + "\n" if text else text
