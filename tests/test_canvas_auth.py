"""The canvas is not open because it is local (ADR 0019 decision 31).

A server taking state-changing POSTs is reachable from any page the browser
happens to be showing, so *localhost is private* is false for this one. These
talk to the running server the way a page does, and the way an attacker would.
"""
import json
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.canvas import PAGE, Canvas, TOKEN_HEADER


class CanvasAuthTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.sheet = self.tmp / "sheet.png"
        self.sheet.write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")
        self.marks = self.tmp / "marks.json"
        self.canvas = Canvas(sheet=self.sheet, marks=self.marks)
        self.addCleanup(self.canvas.stop)
        self.canvas.start()

    def test_a_request_without_the_token_is_refused(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self.canvas.origin + "/marks", timeout=5)
        self.assertEqual(caught.exception.code, 403)

    def test_a_post_without_the_token_writes_nothing(self):
        """The GET above proves the check is on the path; this proves it is on
        the path that changes something, which is the one that matters."""
        req = urllib.request.Request(
            self.canvas.origin + "/marks",
            data=json.dumps({"view": "front", "pixel": [1, 2], "text": "x"}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(caught.exception.code, 403)
        self.assertFalse(self.marks.exists())

    def test_a_post_that_is_not_json_writes_nothing(self):
        """A form POST is a *simple* request: any page can send one at us
        without a preflight. Requiring a content type only a preflighted
        request can set is what keeps such a POST away from a handler."""
        body = json.dumps({"view": "front", "pixel": [1, 2], "text": "x"})
        req = urllib.request.Request(
            self.canvas.origin + "/marks", data=body.encode(),
            headers={TOKEN_HEADER: self.canvas.token,
                     "Content-Type": "text/plain;charset=UTF-8"},
            method="POST")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(caught.exception.code, 415)
        self.assertFalse(self.marks.exists())

    def test_the_page_routes_every_request_through_one_helper(self):
        """No browser here, so this is structural where the others are
        behavioural: it cannot prove the page authenticates, only that no
        request in it bypasses the one place that does. A second bare `fetch`
        is how the token gets forgotten on the call added six months from now.
        """
        page = PAGE.read_text(encoding="utf-8")
        self.assertEqual(page.count("fetch("), 1,
                         "every request goes through the one helper")
        self.assertIn(TOKEN_HEADER, page)
        self.assertIn("application/json", page)
        for n, line in enumerate(page.splitlines(), 1):
            if ".src =" in line:
                self.assertIn("asset(", line, f"line {n} builds a URL by hand")

    def _post(self, path, payload, **headers):
        req = urllib.request.Request(
            self.canvas.origin + path, data=json.dumps(payload).encode(),
            headers={TOKEN_HEADER: self.canvas.token,
                     "Content-Type": "application/json", **headers},
            method="POST")
        return urllib.request.urlopen(req, timeout=5)

    def test_a_post_from_another_origin_is_refused(self):
        """A stolen token is not the only way in. DNS rebinding gives another
        site our address, so a request can arrive holding everything except a
        claim to have come from this page."""
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self._post("/marks", {"view": "front", "pixel": [1, 2], "text": "x"},
                       Origin="https://example.com")
        self.assertEqual(caught.exception.code, 403)
        self.assertFalse(self.marks.exists())

    def test_a_post_from_this_page_is_served(self):
        """The guard has to let the page through, or it is a guard against the
        only caller there is."""
        with self._post("/marks", {"view": "front", "pixel": [1, 2], "text": "x"},
                        Origin=self.canvas.origin) as r:
            self.assertEqual(r.status, 200)

    def test_a_request_the_browser_calls_cross_site_is_refused(self):
        """`Sec-Fetch-Site` is the browser's own account of where a request
        came from, and a page cannot forge it. It is checked as well as
        `Origin` because the two are attached to different requests."""
        for site in ("cross-site", "same-site"):
            with self.subTest(site=site):
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    self._post("/marks", {"view": "front", "pixel": [1, 2],
                                          "text": "x"},
                               **{"Sec-Fetch-Site": site})
                self.assertEqual(caught.exception.code, 403)
        self.assertFalse(self.marks.exists())

    def test_the_page_and_its_own_navigation_are_served(self):
        """`same-origin` is what the page's own fetches carry; `none` is what
        the address bar carries, so refusing it would refuse the page."""
        with self._post("/marks", {"view": "front", "pixel": [1, 2], "text": "x"},
                        **{"Sec-Fetch-Site": "same-origin"}) as r:
            self.assertEqual(r.status, 200)
        req = urllib.request.Request(
            self.canvas.url, headers={"Sec-Fetch-Site": "none"})
        with urllib.request.urlopen(req, timeout=5) as r:
            self.assertEqual(r.status, 200)

    def test_the_server_is_reachable_only_on_the_loopback_address(self):
        """True before this slice and now guarded: binding every interface
        would put the sheet on the network, where no token was ever the plan."""
        self.assertTrue(self.canvas.origin.startswith("http://127.0.0.1:"),
                        self.canvas.origin)

    def test_two_sessions_do_not_share_a_token(self):
        """A token reused across sessions is a password, and the URL of a
        session that ended would open the next one."""
        other = Canvas(sheet=self.sheet, marks=self.marks)
        self.assertNotEqual(self.canvas.token, other.token)
        self.assertGreater(len(other.token), 20)

    def test_the_report_never_carries_the_token(self):
        """The report is the one output that reaches a transcript and a log.
        The URL is printed for the user who has to click it; the record of what
        happened does not need the secret and should not keep it."""
        report = self.canvas.report("no marks captured")
        for line in report["lines"]:
            self.assertNotIn(self.canvas.token, line)


if __name__ == "__main__":
    unittest.main()
