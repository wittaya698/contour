"""A cited decision number resolves to a decision.

The toolkit cites ADR decisions by number in about a hundred places — docstrings
in `lib/`, `console/` and `tools/`, comments in `canvas.html`, the source line of
every slice in `docs/issues/`, and the docstring of most tests. Those citations
are how a reader gets from a line of code to the argument behind it, and they are
the only such path: the code does not otherwise say why.

Nothing checked that they land, and for ADR 0019 they did not. Its decisions were
written unnumbered and never numbered afterwards — the Decision section has not
changed since the day it was committed — so a hundred and seventy-four citations
pointed at numbers the document never defined. Recovered by subject, *decision 20*
and *decision 22* turned out to be each other, and *decision 31* was the
thirty-ninth. A citation that resolves to the wrong decision is worse than none: it
sends a reader to a confident, unrelated paragraph.

So the numbers live in the ADR, and this holds the two halves together: an ADR that
is cited numbers its decisions, and a citation names one that exists.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
ADRS = ROOT / "docs" / "adr"

# A numbered decision, in either spelling the repo uses: `1. **Text.**` where the
# decisions are short enough to be a list (ADR 0009, ADR 0020), and `**12. Text.**`
# where each one is a paragraph of argument and a list would fight the prose
# (ADR 0019). One number per decision paragraph either way — mid-paragraph bold is
# emphasis within a decision, not a decision of its own, so a citation names a
# paragraph and there is nothing to adjudicate.
DECISION = re.compile(r"^(?:\*\*(\d+)\. |(\d+)\. \*\*)", re.M)

# `decision 8`, `decisions 15, 25`, `decisions 8 and 14` — every spelling the
# repo actually uses, because a citation this misses is a citation unguarded.
CITATION = re.compile(r"decisions?\s+((?:\d+)(?:\s*(?:,|and)\s*\d+)*)", re.I)

# Which ADR a citation is about. Named in the phrase — *ADR 0019, decisions 15 and
# 25* — or, inside an ADR citing its own decisions, left unsaid because there it
# cannot be anything else. There is deliberately no third rule that infers the ADR
# from further up the file: two ADRs get mentioned in one docstring all the time,
# and an inference that is usually right is exactly what put *decision 31* on the
# thirty-ninth decision.
ADR_REF = re.compile(r"ADR\s+(\d{4})")
PHRASE = 40                      # how far left of a citation its own ADR can sit

SEARCHED = ("docs", "lib", "console", "tools", "tests", "templates", "schema")
SUFFIXES = (".md", ".py", ".html", ".txt", ".yaml", ".json")


def decision_section(text):
    """The Decision section alone. A number in Context or Rejected is prose."""
    body = text.split("\n## Decision", 1)
    if len(body) < 2:
        return ""
    after = body[1]
    nxt = re.search(r"^## ", after, re.M)
    return after[:nxt.start()] if nxt else after


def decisions(path):
    """The decision numbers this ADR carries, in the order it carries them."""
    return [int(a or b) for a, b in DECISION.findall(decision_section(
        path.read_text(encoding="utf-8")))]


def files():
    """Everything that could hold a citation, except this file, which holds
    examples of one and would otherwise audit its own prose."""
    out = [ROOT / "contour", ROOT / "contour-console", ROOT / "verify.py"]
    for top in SEARCHED:
        for p in (ROOT / top).rglob("*"):
            if (p.is_file() and p.suffix in SUFFIXES
                    and "__pycache__" not in p.parts
                    and p != Path(__file__).resolve()):
                out.append(p)
    return [p for p in out if p.exists()]


def citations(path):
    """Every (adr, decision, line) this file claims, and (None, n, line) for a
    citation that names no ADR — which is unresolvable rather than absent, so it
    is returned and reported rather than skipped."""
    text = path.read_text(encoding="utf-8", errors="replace")
    own = path.name[:4] if path.parent.name == "adr" else None
    out = []
    for m in CITATION.finditer(text):
        before = text[:m.start()]
        phrase = ADR_REF.findall(before[-PHRASE:])
        adr = phrase[-1] if phrase else own
        line = before.count("\n") + 1
        for n in re.findall(r"\d+", m.group(1)):
            out.append((adr, int(n), line))
    return out


class DecisionNumbersTest(unittest.TestCase):
    def test_an_adr_that_is_cited_numbers_its_decisions(self):
        """Numbering is what makes a citation checkable, so it is required of
        exactly the ADRs something cites — not of every ADR, because most record
        one decision and are cited whole."""
        cited = {adr for p in files() for adr, _, _ in citations(p) if adr}
        for adr in sorted(cited):
            hits = sorted(ADRS.glob(f"{adr}-*.md"))
            self.assertEqual(len(hits), 1, f"ADR {adr} is cited by number")
            with self.subTest(adr=adr):
                self.assertTrue(decisions(hits[0]),
                                f"ADR {adr} is cited by decision number and "
                                f"numbers none of its decisions")

    def test_the_numbers_run_from_one_with_no_gaps(self):
        """A gap is invisible to a reader, who then cannot tell a decision that
        was removed from a citation that was mistyped."""
        for path in sorted(ADRS.glob("0*.md")):
            got = decisions(path)
            if not got:
                continue
            with self.subTest(adr=path.name):
                self.assertEqual(got, list(range(1, len(got) + 1)),
                                 f"{path.name} numbers its decisions {got}")

    def test_a_citation_names_the_adr_it_cites(self):
        """*decision 27* alone is a reader looking for the right paragraph in
        the wrong ADR. Inside an ADR it needs no name; anywhere else it does."""
        bare = [f"{p.relative_to(ROOT)}:{line} cites decision {n} and names no ADR"
                for p in sorted(files())
                for adr, n, line in citations(p) if adr is None]
        self.assertEqual(bare, [], "\n" + "\n".join(bare))

    def test_every_cited_decision_exists(self):
        """Catches a number with nothing behind it — a decision deleted, a
        citation mistyped, a section that grew shorter. It cannot catch a
        citation that resolves to the *wrong* decision, because only prose knows
        that; what it does is keep the range honest, which is the half that can
        be mechanised. The other half is why the numbers are in the file now:
        a reader who follows one can see whether it fits."""
        known = {}
        for path in sorted(ADRS.glob("0*.md")):
            known[path.name[:4]] = set(decisions(path))
        bad = []
        for path in sorted(files()):
            for adr, n, line in citations(path):
                if adr in known and known[adr] and n not in known[adr]:
                    bad.append(f"{path.relative_to(ROOT)}:{line} cites ADR "
                               f"{adr} decision {n}, which does not exist")
        self.assertEqual(bad, [], "\n" + "\n".join(bad))


if __name__ == "__main__":
    unittest.main()
