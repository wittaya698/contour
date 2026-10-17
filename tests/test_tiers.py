"""The transcript reads in tiers (issue 129).

Loudest first: a gate waiting, the agent's words, what you asked, what it did,
and the bookkeeping. Read from the page's stylesheet, as every page test is:
there is no browser in this suite. What a tier looks like is for eyes on a
run; what is pinned here is its order and the colours it may use.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PAGE = ROOT / "lib" / "canvas.html"


def rules():
    """The page's stylesheet, as selector -> {property: value}."""
    style = PAGE.read_text().split("<style>", 1)[1].split("</style>", 1)[0]
    style = re.sub(r"/\*.*?\*/", "", style, flags=re.S)
    out = {}
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", style):
        said = dict((k.strip(), v.strip()) for k, v in
                    (d.split(":", 1) for d in body.split(";") if ":" in d))
        for selector in selectors.split(","):
            out.setdefault(" ".join(selector.split()), {}).update(said)
    return out


class TiersTest(unittest.TestCase):

    def test_what_you_asked_has_a_quiet_rule_and_no_bold(self):
        """Bold inside a line then only ever means the agent stressed it."""
        prompt = rules()["#turns > .prompt"]
        self.assertNotIn("font-weight", prompt)
        self.assertIn("var(--line)", prompt.get("border-left", ""))

    def test_the_agents_words_outrank_what_it_did(self):
        """Body size and the agent's colour, against the activity lines
        between them, which are there to skim. And the size holds inside a
        list the agent wrote: a rule on every `li` in the transcript would
        set its options smaller than its sentences."""
        css = rules()
        words = css["#turns > .text"]
        self.assertGreater(px(words["font-size"]), px(css["#turns > li"]["font-size"]))
        self.assertIn("var(--agent)", words.get("border-left", ""))
        self.assertNotIn("font-size", css.get("#turns li", {}))

    def test_bookkeeping_is_quieter_than_what_it_did_and_a_run_visibly_closes(self):
        css = rules()
        line = px(css["#turns > li"]["font-size"])
        for kind in ("ended", "limit", "resolved", "verdict"):
            self.assertLess(px(css[f"#turns > .{kind}"]["font-size"]), line, kind)
        self.assertIn("var(--line)", css["#turns > .ended"].get("border-top", ""))

    def test_a_gate_waiting_is_still_the_only_red_border(self):
        """`--pin` is *stop and look*: no tier outshouts a gate."""
        red = sorted(sel for sel, said in transcript().items()
                     if any(k.startswith("border") and "var(--pin)" in v
                            for k, v in said.items()))
        self.assertEqual(red, ["#run .gate"])

    def test_the_tiers_use_the_pages_colours_and_add_none(self):
        """Two colours already mean something here, and the tiers use those:
        every colour in the transcript is one of the page's tokens."""
        for sel, said in transcript().items():
            for k, v in said.items():
                self.assertFalse(re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", v),
                                 f"{sel} {{ {k}: {v} }}")


def transcript():
    """The rules for the transcript and the run around it."""
    return {sel: said for sel, said in rules().items() if sel.startswith(("#turns", "#run"))}


def px(size):
    return float(size.removesuffix("px"))


if __name__ == "__main__":
    unittest.main()
