"""Shown terms are taught where they first appear (ADR 0025, decision 1; issue 77).

Each term in the *shown* tier — reference, sheet, mark, span, spec — carries
one line where a page first shows it, in the words `docs/CONTEXT.md` gives it
under *On the page*. Once the viewer closes one it stays closed, on this
computer rather than in one tab: each page is served on a port of its own, so
the browser's storage would forget it the next time any page opened. The
record is a convenience — without it the page shows every line.
"""
import os
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.canvas import Canvas    # noqa: E402
from lib.lobby import Lobby    # noqa: E402
from lib.taught import LINES    # noqa: E402
from client import get, open_url, post    # noqa: E402

SHOWN = ("reference", "sheet", "mark", "span", "spec")


def context_lines():
    """{term: line}, as `docs/CONTEXT.md` teaches each one."""
    page = (ROOT / "docs" / "CONTEXT.md").read_text(encoding="utf-8")
    taught = page.split("## On the page", 1)[1].split("**Taught as**", 1)[1].split("\n\n", 2)[1]
    return dict(re.findall(r"^- \*\*(\w+)\*\* — (.+)$", taught, re.M))


def served(page):
    page.start()
    try:
        with open_url(page, "/", timeout=5) as r:
            return r.read().decode()
    finally:
        page.stop()


def lobby():
    return Lobby(lambda: {"spaces": [], "deleted": [], "roots": []}, can=())


def canvas():
    tmp = Path(tempfile.mkdtemp())
    return Canvas(sheet=tmp / "sheet.png", marks=tmp / "marks.json")


class LinesTest(unittest.TestCase):

    def test_context_teaches_every_shown_term(self):
        self.assertEqual(set(context_lines()), set(SHOWN))

    def test_the_pages_lines_are_contexts_words(self):
        self.assertEqual(LINES, context_lines())

    def test_every_page_carries_the_lines_in_contexts_words(self):
        for page in (lobby(), canvas()):
            html = served(page)
            for term, line in context_lines().items():
                self.assertIn(line, html, f"{type(page).__name__} lacks {term}")

    def test_each_page_teaches_the_terms_it_shows_once(self):
        """The lobby shows references and the spec; the canvas and console show
        all five. The page's source, because there is no browser here."""
        from lib.canvas import PAGE as CANVAS
        from lib.lobby import PAGE as LOBBY
        for page, terms in ((LOBBY, {"reference", "spec"}), (CANVAS, set(SHOWN))):
            source = page.read_text(encoding="utf-8")
            for term in SHOWN:
                self.assertEqual(source.count(f"teach('{term}')"), term in terms,
                                 f"{page.name}: {term}")


class ClosedTest(unittest.TestCase):
    """Which lines the viewer has closed, as every page's host keeps it."""

    def setUp(self):
        home = mock.patch.dict(os.environ, {"CONTOUR_HOME": tempfile.mkdtemp()})
        home.start()
        self.addCleanup(home.stop)

    def started(self, page):
        page.start()
        self.addCleanup(page.stop)
        return page

    def test_a_line_closed_on_one_page_is_closed_on_every_page(self):
        on, later = self.started(canvas()), self.started(lobby())
        self.assertEqual(get(later, "/taught")[1], {"closed": []})
        self.assertEqual(post(on, "/taught", {"closed": "mark"})[0], 200)
        self.assertEqual(get(later, "/taught")[1], {"closed": ["mark"]})

    def test_an_unreadable_record_leaves_every_line_showing(self):
        (Path(os.environ["CONTOUR_HOME"]) / "taught.json").write_text("{not json")
        self.assertEqual(get(self.started(lobby()), "/taught")[1], {"closed": []})

    def test_only_a_taught_term_is_recorded(self):
        page = self.started(canvas())
        self.assertEqual(post(page, "/taught", {"closed": "toolkit"})[1], {"closed": []})
        self.assertEqual(get(page, "/taught")[1], {"closed": []})


HARNESS = r"""
const posted = [];
const element = () => ({ children: [], hidden: false, textContent: '', listeners: {},
  append(...k) { this.children.push(...k); },
  addEventListener(e, f) { this.listeners[e] = f; } });
const text = el => typeof el === 'string' ? el
  : (el.textContent || '') + (el.children || []).map(text).join('');
const document = { createElement: element, createTextNode: t => ({ textContent: t }) };
const HOST = %s;
function ask(path, body) {
  if (body !== undefined) posted.push([path, body]);
  if (HOST === null) return Promise.reject(new Error('no host'));
  return Promise.resolve({ json: () => Promise.resolve(HOST) });
}
%s
const shown = teach(%s);
setTimeout(() => {
  if (%s) shown.children.find(k => k.listeners && k.listeners.click).listeners.click();
  setTimeout(() => console.log(JSON.stringify({ hidden: shown.hidden, text: text(shown), posted })));
});
"""


@unittest.skipUnless(shutil.which("node"), "no node to run the page's script")
class TeachTest(unittest.TestCase):
    """The page's script, as the browser gets it, run under node with a
    stand-in for the page and for its host."""

    def teach(self, term, host, click=False):
        html = served(canvas())
        script = html.split("<script data-teach>", 1)[1].split("</script>", 1)[0]
        js = HARNESS % (json.dumps(host), script, json.dumps(term), json.dumps(click))
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_a_term_nobody_closed_shows_its_line(self):
        said = self.teach("mark", {"closed": []})
        self.assertFalse(said["hidden"])
        self.assertIn("mark", said["text"])
        self.assertIn(context_lines()["mark"], said["text"])

    def test_a_closed_line_stays_closed(self):
        self.assertTrue(self.teach("mark", {"closed": ["mark"]})["hidden"])
        self.assertFalse(self.teach("span", {"closed": ["mark"]})["hidden"])

    def test_closing_a_line_hides_it_and_tells_the_host(self):
        said = self.teach("span", {"closed": []}, click=True)
        self.assertTrue(said["hidden"])
        self.assertEqual(said["posted"], [["/taught", {"closed": "span"}]])

    def test_with_no_record_to_ask_the_page_still_explains(self):
        said = self.teach("spec", None)
        self.assertFalse(said["hidden"])
        self.assertIn(context_lines()["spec"], said["text"])


if __name__ == "__main__":
    unittest.main()
